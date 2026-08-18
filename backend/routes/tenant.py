import io

import qrcode
from flask import Blueprint, current_app, jsonify, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from auth_utils import login_required
from extensions import db
from models import DiningTable, OPEN_ORDER_STATUSES, Order, WaiterCall, new_table_access_token

tenant_bp = Blueprint("tenant", __name__)


def _table_occupancy_map(tenant_id):
    rows = (
        db.session.query(Order.table_number, func.count(Order.id))
        .filter(
            Order.tenant_id == tenant_id,
            Order.status.in_(OPEN_ORDER_STATUSES),
        )
        .group_by(Order.table_number)
        .all()
    )
    return {number: count for number, count in rows}


def _open_waiter_tables(tenant_id):
    rows = (
        WaiterCall.query.filter_by(tenant_id=tenant_id, status="open")
        .with_entities(WaiterCall.table_number)
        .all()
    )
    return {r[0] for r in rows}


def _clamp_pct(value, default=20.0):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(100.0, v))


def _normalize_boundary(points):
    if not isinstance(points, list):
        return None, "floor_boundary must be a list of {x, y} points"
    cleaned = []
    for p in points:
        if not isinstance(p, dict):
            return None, "Each boundary point must be an object with x and y"
        cleaned.append({"x": _clamp_pct(p.get("x"), 0), "y": _clamp_pct(p.get("y"), 0)})
    if cleaned and len(cleaned) < 3:
        return None, "Boundary needs at least 3 points"
    return cleaned, None


@tenant_bp.route("/api/tenant/layout", methods=["GET"])
@login_required
def get_layout(tenant):
    tables = (
        DiningTable.query.filter_by(tenant_id=tenant.id)
        .order_by(DiningTable.number)
        .all()
    )
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    return jsonify(
        {
            "floor_boundary": tenant.get_floor_boundary(),
            "tables": [
                t.to_dict(
                    occupancy="occupied" if occ.get(t.number) else "free",
                    waiter_alert=t.number in alerts,
                )
                for t in tables
            ],
        }
    )


@tenant_bp.route("/api/tenant/layout", methods=["PUT"])
@login_required
def save_layout(tenant):
    """Save floor boundary and optionally upsert table positions in one request."""
    data = request.get_json(silent=True) or {}

    if "floor_boundary" in data:
        cleaned, err = _normalize_boundary(data.get("floor_boundary") or [])
        if err:
            return jsonify({"error": err}), 400
        tenant.set_floor_boundary(cleaned)

    tables_payload = data.get("tables")
    if tables_payload is not None:
        if not isinstance(tables_payload, list):
            return jsonify({"error": "tables must be a list"}), 400

        # Replace layout tables from payload (create/update by number; delete missing)
        existing = {
            t.number: t
            for t in DiningTable.query.filter_by(tenant_id=tenant.id).all()
        }
        keep_numbers = set()

        for row in tables_payload:
            try:
                number = int(row.get("number"))
            except (TypeError, ValueError):
                return jsonify({"error": "Each table needs a valid number"}), 400
            if number < 1:
                return jsonify({"error": "Table numbers must be >= 1"}), 400
            if number in keep_numbers:
                return jsonify({"error": f"Duplicate table number {number}"}), 400
            keep_numbers.add(number)

            pos_x = _clamp_pct(row.get("pos_x"), 20)
            pos_y = _clamp_pct(row.get("pos_y"), 20)
            capacity = int(row.get("capacity") or 4)

            if number in existing:
                t = existing[number]
                t.pos_x = pos_x
                t.pos_y = pos_y
                t.capacity = capacity
                t.version += 1
            else:
                db.session.add(
                    DiningTable(
                        tenant_id=tenant.id,
                        number=number,
                        pos_x=pos_x,
                        pos_y=pos_y,
                        capacity=capacity,
                        cell_index=0,
                        access_token=new_table_access_token(),
                    )
                )

        for number, t in existing.items():
            if number not in keep_numbers:
                open_count = (
                    Order.query.filter_by(tenant_id=tenant.id, table_number=number)
                    .filter(Order.status.in_(OPEN_ORDER_STATUSES))
                    .count()
                )
                if open_count:
                    return jsonify(
                        {"error": f"Cannot remove table {number} with open orders"}
                    ), 409
                db.session.delete(t)

    db.session.commit()
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    tables = (
        DiningTable.query.filter_by(tenant_id=tenant.id)
        .order_by(DiningTable.number)
        .all()
    )
    return jsonify(
        {
            "success": True,
            "floor_boundary": tenant.get_floor_boundary(),
            "tables": [
                t.to_dict(
                    occupancy="occupied" if occ.get(t.number) else "free",
                    waiter_alert=t.number in alerts,
                )
                for t in tables
            ],
        }
    )


@tenant_bp.route("/api/tenant/tables", methods=["GET"])
@login_required
def list_tables(tenant):
    tables = (
        DiningTable.query.filter_by(tenant_id=tenant.id)
        .order_by(DiningTable.number)
        .all()
    )
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    return jsonify(
        {
            "tables": [
                t.to_dict(
                    occupancy="occupied" if occ.get(t.number) else "free",
                    waiter_alert=t.number in alerts,
                )
                for t in tables
            ],
            "open_orders_by_table": occ,
            "floor_boundary": tenant.get_floor_boundary(),
        }
    )


@tenant_bp.route("/api/tenant/tables", methods=["POST"])
@login_required
def upsert_table(tenant):
    data = request.get_json(silent=True) or {}
    number = data.get("number")
    capacity = data.get("capacity", 4)
    pos_x = data.get("pos_x", 20)
    pos_y = data.get("pos_y", 20)
    # Legacy cell_index support
    cell_index = data.get("cell_index", 0)

    if number is None:
        return jsonify({"error": "number is required"}), 400

    try:
        number = int(number)
        capacity = int(capacity)
        cell_index = int(cell_index)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid number or capacity"}), 400

    if number < 1:
        return jsonify({"error": "Table number must be >= 1"}), 400

    pos_x = _clamp_pct(pos_x, 20)
    pos_y = _clamp_pct(pos_y, 20)

    existing_number = DiningTable.query.filter_by(tenant_id=tenant.id, number=number).first()
    table_id = data.get("id")
    existing = None
    if table_id:
        existing = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    elif existing_number:
        existing = existing_number

    if existing_number and existing and existing_number.id != existing.id:
        return jsonify({"error": f"Table {number} already exists"}), 409
    if existing_number and not existing:
        return jsonify({"error": f"Table {number} already exists"}), 409

    if existing:
        existing.number = number
        existing.capacity = capacity
        existing.pos_x = pos_x
        existing.pos_y = pos_y
        existing.cell_index = cell_index
        existing.version += 1
        table = existing
    else:
        table = DiningTable(
            tenant_id=tenant.id,
            number=number,
            cell_index=cell_index,
            pos_x=pos_x,
            pos_y=pos_y,
            capacity=capacity,
            access_token=new_table_access_token(),
        )
        db.session.add(table)

    db.session.commit()
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    return jsonify(
        {
            "success": True,
            "table": table.to_dict(
                occupancy="occupied" if occ.get(table.number) else "free",
                waiter_alert=table.number in alerts,
            ),
        }
    ), 201


@tenant_bp.route("/api/tenant/tables/<uuid:table_id>", methods=["PATCH"])
@login_required
def patch_table(tenant, table_id):
    table = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    if not table:
        return jsonify({"error": "Table not found"}), 404

    data = request.get_json(silent=True) or {}
    if "pos_x" in data:
        table.pos_x = _clamp_pct(data["pos_x"], table.pos_x)
    if "pos_y" in data:
        table.pos_y = _clamp_pct(data["pos_y"], table.pos_y)
    if "number" in data:
        try:
            number = int(data["number"])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid number"}), 400
        clash = DiningTable.query.filter_by(tenant_id=tenant.id, number=number).first()
        if clash and clash.id != table.id:
            return jsonify({"error": f"Table {number} already exists"}), 409
        table.number = number
    if "capacity" in data:
        table.capacity = int(data["capacity"])

    table.version += 1
    db.session.commit()
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    return jsonify(
        {
            "success": True,
            "table": table.to_dict(
                occupancy="occupied" if occ.get(table.number) else "free",
                waiter_alert=table.number in alerts,
            ),
        }
    )


@tenant_bp.route("/api/tenant/tables/<uuid:table_id>", methods=["DELETE"])
@login_required
def delete_table(tenant, table_id):
    table = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    if not table:
        return jsonify({"error": "Table not found"}), 404

    open_count = (
        Order.query.filter_by(tenant_id=tenant.id, table_number=table.number)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .count()
    )
    if open_count:
        return jsonify({"error": "Cannot delete a table with open orders"}), 409

    db.session.delete(table)
    db.session.commit()
    return jsonify({"success": True})


@tenant_bp.route("/api/tenant/floor-status", methods=["GET"])
@login_required
def floor_status(tenant):
    """Admin view: which tables are free/occupied and open waiter alerts."""
    tables = DiningTable.query.filter_by(tenant_id=tenant.id).order_by(DiningTable.number).all()
    occ = _table_occupancy_map(tenant.id)
    alerts = _open_waiter_tables(tenant.id)
    open_calls = (
        WaiterCall.query.filter_by(tenant_id=tenant.id, status="open")
        .order_by(WaiterCall.created_at.desc())
        .all()
    )
    open_orders = (
        Order.query.filter_by(tenant_id=tenant.id)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "tables": [
                t.to_dict(
                    occupancy="occupied" if occ.get(t.number) else "free",
                    waiter_alert=t.number in alerts,
                )
                for t in tables
            ],
            "floor_boundary": tenant.get_floor_boundary(),
            "waiter_calls": [c.to_dict() for c in open_calls],
            "open_orders": [o.to_dict() for o in open_orders],
        }
    )


@tenant_bp.route("/api/tenant/export-qrs", methods=["GET"])
@login_required
def export_tenant_qrs(tenant):
    tables = (
        DiningTable.query.filter_by(tenant_id=tenant.id)
        .order_by(DiningTable.number)
        .all()
    )
    if not tables:
        return jsonify({"error": "No tables configured. Add tables first."}), 400

    base = current_app.config["PUBLIC_BASE_URL"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        textColor="#1E4D4A",
        fontSize=20,
        spaceAfter=15,
        alignment=1,
    )
    story.append(Paragraph(f"{tenant.name} — DineFlow Table QRs", title_style))
    story.append(Spacer(1, 10))

    grid_data = []
    current_row = []

    for table in tables:
        # Opaque per-table token — not forgeable by editing a sequential table number
        qr_url = f"{base}/menu?t={table.access_token}"
        qr = qrcode.QRCode(version=1, box_size=5, border=3)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E4D4A", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        flowable_img = Image(img_buffer, width=120, height=120)
        cell_p = Paragraph(f"<b>Table {table.number}</b><br/>Scan to Order", styles["Normal"])
        current_row.append([flowable_img, Spacer(1, 4), cell_p])

        if len(current_row) == 3:
            grid_data.append(current_row)
            current_row = []

    if current_row:
        while len(current_row) < 3:
            current_row.append("")
        grid_data.append(current_row)

    t = Table(grid_data, colWidths=[180, 180, 180])
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="dineflow-table-qrs.pdf",
    )
