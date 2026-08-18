import io
import math

import qrcode
from flask import Blueprint, jsonify, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from auth_utils import kitchen_or_manager_required, manager_required
from extensions import db
from models import (
    DiningTable,
    Floor,
    OPEN_ORDER_STATUSES,
    Order,
    WaiterCall,
    new_table_access_token,
    utcnow,
)

tenant_bp = Blueprint("tenant", __name__)


def _active_tables_q(tenant_id, floor_id=None):
    q = DiningTable.query.filter_by(tenant_id=tenant_id).filter(DiningTable.deleted_at.is_(None))
    if floor_id:
        q = q.filter_by(floor_id=floor_id)
    return q


def _active_floors_q(tenant_id):
    return (
        Floor.query.filter_by(tenant_id=tenant_id)
        .filter(Floor.deleted_at.is_(None))
        .order_by(Floor.sort_order, Floor.created_at)
    )


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


def _normalize_boundary(points, snap_threshold=2.0):
    """Normalize boundary points; auto-close by snapping last→first when near."""
    if not isinstance(points, list):
        return None, "boundary must be a list of {x, y} points"
    cleaned = []
    for p in points:
        if not isinstance(p, dict):
            return None, "Each boundary point must be an object with x and y"
        cleaned.append({"x": _clamp_pct(p.get("x"), 0), "y": _clamp_pct(p.get("y"), 0)})
    if cleaned and len(cleaned) < 3:
        return None, "Boundary needs at least 3 points"
    if len(cleaned) >= 3:
        first, last = cleaned[0], cleaned[-1]
        dist = math.hypot(first["x"] - last["x"], first["y"] - last["y"])
        if dist <= snap_threshold:
            cleaned[-1] = {"x": first["x"], "y": first["y"]}
        # Always ensure closed polygon representation (SVG closes visually; store unique verts)
        if cleaned[0]["x"] == cleaned[-1]["x"] and cleaned[0]["y"] == cleaned[-1]["y"] and len(cleaned) > 3:
            cleaned = cleaned[:-1]
    return cleaned, None


def _ensure_default_floor(tenant):
    floor = _active_floors_q(tenant.id).first()
    if floor:
        return floor
    floor = Floor(tenant_id=tenant.id, name="Main Floor", sort_order=0)
    legacy = tenant.get_floor_boundary()
    if legacy:
        floor.set_boundary(legacy)
    db.session.add(floor)
    db.session.flush()
    return floor


def _serialize_tables(tenant_id, tables):
    occ = _table_occupancy_map(tenant_id)
    alerts = _open_waiter_tables(tenant_id)
    return [
        t.to_dict(
            occupancy="occupied" if occ.get(t.number) else "free",
            waiter_alert=t.number in alerts,
            open_ticket_count=occ.get(t.number, 0),
        )
        for t in tables
    ]


# ---------- Floors ----------


@tenant_bp.route("/api/tenant/floors", methods=["GET"])
@kitchen_or_manager_required
def list_floors(tenant):
    floors = _active_floors_q(tenant.id).all()
    if not floors:
        floors = [_ensure_default_floor(tenant)]
        db.session.commit()
    return jsonify({"floors": [f.to_dict() for f in floors]})


@tenant_bp.route("/api/tenant/floors", methods=["POST"])
@manager_required
def create_floor(tenant):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or "New Floor"
    floor = Floor(
        tenant_id=tenant.id,
        name=name,
        sort_order=int(data.get("sort_order") or (_active_floors_q(tenant.id).count())),
    )
    if "boundary" in data:
        cleaned, err = _normalize_boundary(data.get("boundary") or [])
        if err:
            return jsonify({"error": err}), 400
        floor.set_boundary(cleaned)
    db.session.add(floor)
    db.session.commit()
    return jsonify({"success": True, "floor": floor.to_dict()}), 201


@tenant_bp.route("/api/tenant/floors/<uuid:floor_id>", methods=["PUT"])
@manager_required
def update_floor(tenant, floor_id):
    floor = Floor.query.filter_by(id=floor_id, tenant_id=tenant.id).first()
    if not floor or floor.deleted_at:
        return jsonify({"error": "Floor not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name required"}), 400
        floor.name = name
    if "sort_order" in data:
        floor.sort_order = int(data["sort_order"])
    if "boundary" in data:
        cleaned, err = _normalize_boundary(data.get("boundary") or [])
        if err:
            return jsonify({"error": err}), 400
        floor.set_boundary(cleaned)
        tenant.set_floor_boundary(cleaned)  # keep legacy in sync for default floor
    db.session.commit()
    return jsonify({"success": True, "floor": floor.to_dict()})


@tenant_bp.route("/api/tenant/floors/<uuid:floor_id>", methods=["DELETE"])
@manager_required
def delete_floor(tenant, floor_id):
    floor = Floor.query.filter_by(id=floor_id, tenant_id=tenant.id).first()
    if not floor or floor.deleted_at:
        return jsonify({"error": "Floor not found"}), 404
    if _active_floors_q(tenant.id).count() <= 1:
        return jsonify({"error": "Cannot delete the last floor"}), 400
    open_on_floor = (
        Order.query.join(DiningTable, Order.dining_table_id == DiningTable.id)
        .filter(
            DiningTable.floor_id == floor.id,
            Order.status.in_(OPEN_ORDER_STATUSES),
        )
        .count()
    )
    if open_on_floor:
        return jsonify({"error": "Floor has open orders"}), 409
    floor.deleted_at = utcnow()
    for t in _active_tables_q(tenant.id, floor.id).all():
        t.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})


# ---------- Layout (per floor) ----------


@tenant_bp.route("/api/tenant/layout", methods=["GET"])
@manager_required
def get_layout(tenant):
    floor_id = request.args.get("floor_id")
    floors = _active_floors_q(tenant.id).all()
    if not floors:
        floors = [_ensure_default_floor(tenant)]
        db.session.commit()
    floor = None
    if floor_id:
        floor = next((f for f in floors if str(f.id) == str(floor_id)), None)
    if not floor:
        floor = floors[0]
    tables = _active_tables_q(tenant.id, floor.id).order_by(DiningTable.number).all()
    return jsonify(
        {
            "floor": floor.to_dict(),
            "floors": [f.to_dict() for f in floors],
            "floor_boundary": floor.get_boundary(),
            "tables": _serialize_tables(tenant.id, tables),
        }
    )


@tenant_bp.route("/api/tenant/layout", methods=["PUT"])
@manager_required
def save_layout(tenant):
    data = request.get_json(silent=True) or {}
    floor_id = data.get("floor_id")
    floors = _active_floors_q(tenant.id).all()
    if not floors:
        floors = [_ensure_default_floor(tenant)]
        db.session.flush()

    floor = None
    if floor_id:
        floor = Floor.query.filter_by(id=floor_id, tenant_id=tenant.id).first()
    if not floor or floor.deleted_at:
        floor = floors[0]

    if "floor_boundary" in data or "boundary" in data:
        raw = data.get("boundary") if "boundary" in data else data.get("floor_boundary")
        cleaned, err = _normalize_boundary(raw or [])
        if err:
            return jsonify({"error": err}), 400
        floor.set_boundary(cleaned)
        if floor.sort_order == 0:
            tenant.set_floor_boundary(cleaned)

    tables_payload = data.get("tables")
    if tables_payload is not None:
        if not isinstance(tables_payload, list):
            return jsonify({"error": "tables must be a list"}), 400

        existing = {
            t.number: t
            for t in _active_tables_q(tenant.id, floor.id).all()
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
                t.floor_id = floor.id
                t.version += 1
            else:
                clash = (
                    DiningTable.query.filter_by(tenant_id=tenant.id, number=number)
                    .filter(DiningTable.deleted_at.is_(None))
                    .first()
                )
                if clash:
                    return jsonify({"error": f"Table {number} already exists on another floor"}), 409
                db.session.add(
                    DiningTable(
                        tenant_id=tenant.id,
                        floor_id=floor.id,
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
                    return jsonify({"error": f"Cannot remove table {number} with open orders"}), 409
                t.deleted_at = utcnow()

    db.session.commit()
    tables = _active_tables_q(tenant.id, floor.id).order_by(DiningTable.number).all()
    return jsonify(
        {
            "success": True,
            "floor": floor.to_dict(),
            "floor_boundary": floor.get_boundary(),
            "tables": _serialize_tables(tenant.id, tables),
        }
    )


@tenant_bp.route("/api/tenant/tables", methods=["GET"])
@manager_required
def list_tables(tenant):
    floor_id = request.args.get("floor_id")
    q = _active_tables_q(tenant.id, floor_id)
    tables = q.order_by(DiningTable.number).all()
    occ = _table_occupancy_map(tenant.id)
    floor = _ensure_default_floor(tenant)
    db.session.commit()
    return jsonify(
        {
            "tables": _serialize_tables(tenant.id, tables),
            "open_orders_by_table": occ,
            "floor_boundary": floor.get_boundary(),
        }
    )


@tenant_bp.route("/api/tenant/tables", methods=["POST"])
@manager_required
def upsert_table(tenant):
    data = request.get_json(silent=True) or {}
    number = data.get("number")
    capacity = data.get("capacity", 4)
    pos_x = data.get("pos_x", 20)
    pos_y = data.get("pos_y", 20)
    cell_index = data.get("cell_index", 0)
    floor_id = data.get("floor_id")

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

    floor = None
    if floor_id:
        floor = Floor.query.filter_by(id=floor_id, tenant_id=tenant.id).first()
    if not floor or floor.deleted_at:
        floor = _ensure_default_floor(tenant)

    pos_x = _clamp_pct(pos_x, 20)
    pos_y = _clamp_pct(pos_y, 20)

    existing_number = (
        DiningTable.query.filter_by(tenant_id=tenant.id, number=number)
        .filter(DiningTable.deleted_at.is_(None))
        .first()
    )
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
        existing.floor_id = floor.id
        existing.version += 1
        table = existing
    else:
        table = DiningTable(
            tenant_id=tenant.id,
            floor_id=floor.id,
            number=number,
            cell_index=cell_index,
            pos_x=pos_x,
            pos_y=pos_y,
            capacity=capacity,
            access_token=new_table_access_token(),
        )
        db.session.add(table)

    db.session.commit()
    return jsonify({"success": True, "table": _serialize_tables(tenant.id, [table])[0]}), 201


@tenant_bp.route("/api/tenant/tables/<uuid:table_id>", methods=["PATCH"])
@manager_required
def patch_table(tenant, table_id):
    table = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    if not table or table.deleted_at:
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
        clash = (
            DiningTable.query.filter_by(tenant_id=tenant.id, number=number)
            .filter(DiningTable.deleted_at.is_(None))
            .first()
        )
        if clash and clash.id != table.id:
            return jsonify({"error": f"Table {number} already exists"}), 409
        table.number = number
    if "capacity" in data:
        table.capacity = int(data["capacity"])
    if "floor_id" in data:
        floor = Floor.query.filter_by(id=data["floor_id"], tenant_id=tenant.id).first()
        if not floor or floor.deleted_at:
            return jsonify({"error": "Floor not found"}), 404
        table.floor_id = floor.id

    table.version += 1
    db.session.commit()
    return jsonify({"success": True, "table": _serialize_tables(tenant.id, [table])[0]})


@tenant_bp.route("/api/tenant/tables/<uuid:table_id>", methods=["DELETE"])
@manager_required
def delete_table(tenant, table_id):
    table = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    if not table or table.deleted_at:
        return jsonify({"error": "Table not found"}), 404

    open_count = (
        Order.query.filter_by(tenant_id=tenant.id, table_number=table.number)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .count()
    )
    if open_count:
        return jsonify({"error": "Cannot delete a table with open orders"}), 409

    table.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})


@tenant_bp.route("/api/tenant/floor-status", methods=["GET"])
@manager_required
def floor_status(tenant):
    floor_id = request.args.get("floor_id")
    floors = _active_floors_q(tenant.id).all()
    if not floors:
        floors = [_ensure_default_floor(tenant)]
        db.session.commit()
    floor = None
    if floor_id:
        floor = next((f for f in floors if str(f.id) == str(floor_id)), None)
    if not floor:
        floor = floors[0]

    tables = _active_tables_q(tenant.id, floor.id).order_by(DiningTable.number).all()
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
            "floor": floor.to_dict(),
            "floors": [f.to_dict() for f in floors],
            "tables": _serialize_tables(tenant.id, tables),
            "floor_boundary": floor.get_boundary(),
            "waiter_calls": [c.to_dict() for c in open_calls],
            "open_orders": [o.to_dict() for o in open_orders],
        }
    )


from public_url import resolve_public_base_url


def _build_qr_pdf(tenant, tables, per_page=2):
    """Build PDF with 1, 2, or 4 QR codes per A4 page."""
    per_page = int(per_page) if int(per_page) in (1, 2, 4) else 2
    base = resolve_public_base_url()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
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
        textColor="#1a2e24",
        fontSize=18,
        spaceAfter=12,
        alignment=1,
    )
    story.append(Paragraph(f"{tenant.name} — DineFlow Table QRs", title_style))
    story.append(
        Paragraph(f"<font size='9' color='#666666'>Links use: {base}</font>", styles["Normal"])
    )
    story.append(Spacer(1, 8))

    # Size QR by density
    size_map = {1: 280, 2: 220, 4: 160}
    qr_size = size_map[per_page]
    cols = 1 if per_page == 1 else (2 if per_page == 2 else 2)
    col_w = (A4[0] - 72) / cols

    grid_data = []
    current_row = []

    for table in tables:
        qr_url = f"{base}/menu?t={table.access_token}"
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1a2e24", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        flowable_img = Image(img_buffer, width=qr_size, height=qr_size)
        cell_p = Paragraph(f"<b>Table {table.number}</b><br/>Scan to Order", styles["Normal"])
        current_row.append([flowable_img, Spacer(1, 6), cell_p])

        if len(current_row) == cols:
            grid_data.append(current_row)
            current_row = []

    if current_row:
        while len(current_row) < cols:
            current_row.append("")
        grid_data.append(current_row)

    t = Table(grid_data, colWidths=[col_w] * cols)
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

@tenant_bp.route("/api/tenant/export-qrs", methods=["GET"])
@manager_required
def export_tenant_qrs(tenant):
    per_page = request.args.get("per_page", 2)
    floor_id = request.args.get("floor_id")
    q = _active_tables_q(tenant.id, floor_id)
    tables = q.order_by(DiningTable.number).all()
    if not tables:
        return jsonify({"error": "No tables configured. Add tables first."}), 400
    buffer = _build_qr_pdf(tenant, tables, per_page=per_page)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="dineflow-table-qrs.pdf",
    )


@tenant_bp.route("/api/tenant/tables/<uuid:table_id>/qr", methods=["GET"])
@manager_required
def export_single_table_qr(tenant, table_id):
    table = DiningTable.query.filter_by(id=table_id, tenant_id=tenant.id).first()
    if not table or table.deleted_at:
        return jsonify({"error": "Table not found"}), 404
    rotate = request.args.get("rotate", "0") in ("1", "true", "True")
    if rotate:
        table.access_token = new_table_access_token()
        table.version += 1
        db.session.commit()
    buffer = _build_qr_pdf(tenant, [table], per_page=1)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"dineflow-table-{table.number}-qr.pdf",
    )
