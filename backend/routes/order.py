import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import DBAPIError, OperationalError

from auth_utils import get_current_staff, kitchen_or_manager_required, manager_required
from extensions import db, socketio
from jwt_utils import create_guest_socket_ticket
from models import (
    ALLOWED_TRANSITIONS,
    DiningTable,
    MenuItem,
    Modifier,
    OPEN_ORDER_STATUSES,
    Order,
    OrderItem,
    OrderStatusAudit,
    WAITER_REASONS,
    WaiterCall,
    utcnow,
)

order_bp = Blueprint("order", __name__)


def _parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _table_from_guest_token(raw_token):
    token = (raw_token or "").strip()
    if not token or len(token) < 16:
        return None
    return (
        DiningTable.query.filter_by(access_token=token)
        .filter(DiningTable.deleted_at.is_(None))
        .first()
    )


def emit_kitchen_update(tenant_id, order_dict):
    socketio.emit("new_order", order_dict, room=f"tenant:{tenant_id}")


def emit_status_update(tenant_id, order_dict):
    socketio.emit("status_update", order_dict, room=f"tenant:{tenant_id}")


def emit_floor_refresh(tenant_id):
    socketio.emit("floor_refresh", {"tenant_id": str(tenant_id)}, room=f"tenant:{tenant_id}")


def emit_waiter_call(tenant_id, call_dict):
    socketio.emit("waiter_call", call_dict, room=f"tenant:{tenant_id}")


def emit_waiter_acked(tenant_id, call_dict):
    socketio.emit("waiter_acked", call_dict, room=f"tenant:{tenant_id}")


def _audit(order, from_status, to_status, staff=None, label=None):
    db.session.add(
        OrderStatusAudit(
            order_id=order.id,
            tenant_id=order.tenant_id,
            from_status=from_status,
            to_status=to_status,
            actor_staff_id=staff.id if staff else None,
            actor_label=label or (staff.role if staff else "guest"),
            version=order.version,
        )
    )


@order_bp.route("/api/public/session", methods=["GET"])
def public_table_session():
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    if not table:
        return jsonify({"error": "Invalid or expired table link"}), 404
    tenant = table.tenant
    ticket = create_guest_socket_ticket(table)
    return jsonify(
        {
            "token": table.access_token,
            "tenant_id": str(table.tenant_id),
            "table_id": str(table.id),
            "table_number": table.number,
            "guest_ticket": ticket,
            "restaurant": {"id": str(tenant.id), "name": tenant.name},
        }
    )


@order_bp.route("/api/public/orders", methods=["GET"])
def public_orders_for_token():
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    if not table:
        return jsonify({"error": "Invalid or expired table link"}), 404
    status = request.args.get("status")
    q = Order.query.filter_by(tenant_id=table.tenant_id, dining_table_id=table.id)
    if status == "open":
        q = q.filter(Order.status.in_(OPEN_ORDER_STATUSES))
    elif status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.created_at.desc()).limit(50).all()
    return jsonify({"orders": [o.to_dict() for o in orders], "table_number": table.number})


@order_bp.route("/api/orders/create", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    table = _table_from_guest_token(data.get("token") or data.get("t"))
    if not table:
        return jsonify({"error": "Valid table token is required"}), 401

    items = data.get("items") or []
    notes = (data.get("notes") or "").strip() or None
    if not items:
        return jsonify({"error": "No items selected"}), 400

    tenant_id = table.tenant_id

    try:
        locked = (
            db.session.query(DiningTable)
            .filter_by(id=table.id)
            .with_for_update()
            .first()
        )
        if not locked or locked.deleted_at:
            return jsonify({"error": "Table not found"}), 404

        order_items = []
        for raw in items:
            mid = _parse_uuid(raw.get("menu_item_id"))
            qty = int(raw.get("quantity") or 0)
            if not mid or qty < 1:
                db.session.rollback()
                return jsonify({"error": "Each item needs menu_item_id and quantity >= 1"}), 400
            menu_item = (
                MenuItem.query.filter_by(id=mid, tenant_id=tenant_id)
                .filter(MenuItem.deleted_at.is_(None))
                .first()
            )
            if not menu_item or not menu_item.available:
                db.session.rollback()
                return jsonify({"error": f"Menu item unavailable: {mid}"}), 400

            selected_mods = []
            unit = float(menu_item.price)
            for mod_raw in raw.get("modifiers") or []:
                mod_id = _parse_uuid(mod_raw.get("id") or mod_raw.get("modifier_id"))
                if not mod_id:
                    continue
                mod = db.session.get(Modifier, mod_id)
                if not mod or mod.deleted_at:
                    continue
                # Ensure modifier belongs to this item
                if not mod.group or mod.group.menu_item_id != menu_item.id:
                    continue
                selected_mods.append({"id": str(mod.id), "name": mod.name, "price_delta": float(mod.price_delta)})
                unit += float(mod.price_delta)

            order_items.append((menu_item, qty, selected_mods, unit))

        new_order = Order(
            tenant_id=tenant_id,
            dining_table_id=locked.id,
            table_number=locked.number,
            status="pending",
            notes=notes,
        )
        db.session.add(new_order)
        db.session.flush()

        for menu_item, qty, selected_mods, unit in order_items:
            db.session.add(
                OrderItem(
                    order_id=new_order.id,
                    menu_item_id=menu_item.id,
                    station_id=menu_item.station_id,
                    name=menu_item.name,
                    unit_price=unit,
                    quantity=qty,
                    modifiers_json=selected_mods or None,
                )
            )

        locked.version += 1
        _audit(new_order, None, "pending", label="guest")
        db.session.commit()

        payload = new_order.to_dict()
        emit_kitchen_update(tenant_id, payload)
        emit_floor_refresh(tenant_id)
        return jsonify({"success": True, "order": payload}), 201

    except (DBAPIError, OperationalError):
        db.session.rollback()
        return jsonify({"error": "Database lock timeout or conflict. Please try again."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Unexpected server error: " + str(e)}), 500


@order_bp.route("/api/orders/<tenant_id>/table/<int:table_number>", methods=["GET"])
def orders_for_table(tenant_id, table_number):
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    tid = _parse_uuid(tenant_id)
    if not tid or not table:
        return jsonify({"error": "Valid table token is required"}), 401
    if table.tenant_id != tid or table.number != table_number:
        return jsonify({"error": "Token does not match this table"}), 403
    status = request.args.get("status")
    q = Order.query.filter_by(tenant_id=tid, dining_table_id=table.id)
    if status == "open":
        q = q.filter(Order.status.in_(OPEN_ORDER_STATUSES))
    elif status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.created_at.desc()).limit(50).all()
    return jsonify({"orders": [o.to_dict() for o in orders]})


@order_bp.route("/api/orders/<tenant_id>/<uuid:order_id>", methods=["GET"])
def get_order(tenant_id, order_id):
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    tid = _parse_uuid(tenant_id)
    if not tid or not table:
        return jsonify({"error": "Valid table token is required"}), 401
    if table.tenant_id != tid:
        return jsonify({"error": "Token does not match this restaurant"}), 403
    order = Order.query.filter_by(id=order_id, tenant_id=tid, dining_table_id=table.id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"order": order.to_dict()})


@order_bp.route("/api/orders/kitchen", methods=["GET"])
@kitchen_or_manager_required
def kitchen_orders(tenant):
    station_id = request.args.get("station_id")
    orders = (
        Order.query.filter_by(tenant_id=tenant.id)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .order_by(Order.created_at.asc())
        .all()
    )
    result = []
    for o in orders:
        d = o.to_dict()
        if station_id:
            # Include ticket if any item matches station (or unassigned)
            if d["station_ids"] and station_id not in d["station_ids"]:
                continue
            # Filter visible items to station
            d["items"] = [
                i
                for i in d["items"]
                if not i.get("station_id") or i.get("station_id") == station_id
            ]
            if not d["items"]:
                continue
        result.append(d)
    return jsonify({"orders": result})


@order_bp.route("/api/orders/<uuid:order_id>", methods=["GET"])
@kitchen_or_manager_required
def admin_get_order(tenant, order_id):
    order = Order.query.filter_by(id=order_id, tenant_id=tenant.id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"order": order.to_dict(include_audits=True)})


@order_bp.route("/api/orders/live", methods=["GET"])
@manager_required
def live_orders(tenant):
    orders = (
        Order.query.filter_by(tenant_id=tenant.id)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify({"orders": [o.to_dict() for o in orders]})


@order_bp.route("/api/orders/<uuid:order_id>/status", methods=["PATCH"])
@kitchen_or_manager_required
def update_order_status(tenant, order_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip().lower()
    client_version = data.get("version")

    if new_status not in ALLOWED_TRANSITIONS:
        return jsonify({"error": "Invalid status"}), 400

    try:
        order = (
            db.session.query(Order)
            .filter_by(id=order_id, tenant_id=tenant.id)
            .with_for_update()
            .first()
        )
        if not order:
            return jsonify({"error": "Order not found"}), 404

        if client_version is not None and int(client_version) != order.version:
            return jsonify(
                {
                    "error": "Order changed elsewhere. Refresh and try again.",
                    "order": order.to_dict(),
                }
            ), 409

        allowed = ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            return jsonify(
                {"error": f"Cannot transition from {order.status} to {new_status}"}
            ), 400

        old = order.status
        order.status = new_status
        order.version += 1
        staff = get_current_staff()
        _audit(order, old, new_status, staff=staff)
        db.session.commit()

        payload = order.to_dict()
        emit_status_update(tenant.id, payload)
        emit_floor_refresh(tenant.id)
        return jsonify({"success": True, "order": payload})

    except (DBAPIError, OperationalError):
        db.session.rollback()
        return jsonify({"error": "Database conflict. Please try again."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@order_bp.route("/api/orders/waiter-call", methods=["POST"])
def create_waiter_call():
    data = request.get_json(silent=True) or {}
    table = _table_from_guest_token(data.get("token") or data.get("t"))
    if not table:
        return jsonify({"error": "Valid table token is required"}), 401

    reason = (data.get("reason") or "help").strip().lower()
    if reason not in WAITER_REASONS:
        reason = "help"
    note = (data.get("note") or "").strip() or None

    existing = WaiterCall.query.filter_by(
        tenant_id=table.tenant_id, dining_table_id=table.id, status="open"
    ).first()
    if existing:
        existing.reason = reason
        if note:
            existing.note = note
        db.session.commit()
        return jsonify({"success": True, "call": existing.to_dict(), "already_open": True})

    call = WaiterCall(
        tenant_id=table.tenant_id,
        dining_table_id=table.id,
        table_number=table.number,
        reason=reason,
        note=note,
        status="open",
    )
    db.session.add(call)
    db.session.commit()
    payload = call.to_dict()
    emit_waiter_call(table.tenant_id, payload)
    emit_floor_refresh(table.tenant_id)
    return jsonify({"success": True, "call": payload}), 201


@order_bp.route("/api/orders/waiter-call/<uuid:call_id>/ack", methods=["POST"])
@manager_required
def ack_waiter_call(tenant, call_id):
    call = WaiterCall.query.filter_by(id=call_id, tenant_id=tenant.id).first()
    if not call:
        return jsonify({"error": "Waiter call not found"}), 404
    if call.status == "acked":
        return jsonify({"success": True, "call": call.to_dict()})

    call.status = "acked"
    call.acked_at = utcnow()
    db.session.commit()
    payload = call.to_dict()
    emit_waiter_acked(tenant.id, payload)
    emit_floor_refresh(tenant.id)
    return jsonify({"success": True, "call": payload})


@order_bp.route("/api/orders/waiter-calls", methods=["GET"])
@manager_required
def list_waiter_calls(tenant):
    status = request.args.get("status", "open")
    q = WaiterCall.query.filter_by(tenant_id=tenant.id)
    if status != "all":
        q = q.filter_by(status=status)
    calls = q.order_by(WaiterCall.created_at.desc()).limit(100).all()
    return jsonify({"calls": [c.to_dict() for c in calls]})
