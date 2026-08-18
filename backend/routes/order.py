import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import DBAPIError, OperationalError

from auth_utils import login_required
from extensions import db, socketio
from models import (
    ALLOWED_TRANSITIONS,
    DiningTable,
    MenuItem,
    OPEN_ORDER_STATUSES,
    Order,
    OrderItem,
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
    """Resolve guest QR token → DiningTable. Tokens are unguessable; table numbers are not."""
    token = (raw_token or "").strip()
    if not token or len(token) < 16:
        return None
    return DiningTable.query.filter_by(access_token=token).first()


def emit_kitchen_update(tenant_id, order_dict):
    room = f"tenant:{tenant_id}"
    socketio.emit("new_order", order_dict, room=room)


def emit_status_update(tenant_id, order_dict):
    room = f"tenant:{tenant_id}"
    socketio.emit("status_update", order_dict, room=room)


def emit_floor_refresh(tenant_id):
    room = f"tenant:{tenant_id}"
    socketio.emit("floor_refresh", {"tenant_id": str(tenant_id)}, room=room)


def emit_waiter_call(tenant_id, call_dict):
    room = f"tenant:{tenant_id}"
    socketio.emit("waiter_call", call_dict, room=room)


def emit_waiter_acked(tenant_id, call_dict):
    room = f"tenant:{tenant_id}"
    socketio.emit("waiter_acked", call_dict, room=room)


@order_bp.route("/api/public/session", methods=["GET"])
def public_table_session():
    """Resolve QR token to restaurant + table. Never trusts a client-supplied table number."""
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    if not table:
        return jsonify({"error": "Invalid or expired table link"}), 404
    tenant = table.tenant
    return jsonify(
        {
            "token": table.access_token,
            "tenant_id": str(table.tenant_id),
            "table_number": table.number,
            "restaurant": {"id": str(tenant.id), "name": tenant.name},
        }
    )


@order_bp.route("/api/public/orders", methods=["GET"])
def public_orders_for_token():
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    if not table:
        return jsonify({"error": "Invalid or expired table link"}), 404
    status = request.args.get("status")
    q = Order.query.filter_by(tenant_id=table.tenant_id, table_number=table.number)
    if status == "open":
        q = q.filter(Order.status.in_(OPEN_ORDER_STATUSES))
    elif status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.created_at.desc()).limit(50).all()
    return jsonify({"orders": [o.to_dict() for o in orders], "table_number": table.number})


@order_bp.route("/api/orders/create", methods=["POST"])
def create_order():
    """
    Guest order entry. Requires opaque table `token` from the QR link.
    Client-supplied tenant_id / table_number are ignored for authorization.
    """
    data = request.get_json(silent=True) or {}
    table = _table_from_guest_token(data.get("token") or data.get("t"))
    if not table:
        return jsonify({"error": "Valid table token is required"}), 401

    items = data.get("items") or []
    notes = (data.get("notes") or "").strip() or None
    if not items:
        return jsonify({"error": "No items selected"}), 400

    tenant_id = table.tenant_id
    table_number = table.number

    try:
        locked = (
            db.session.query(DiningTable)
            .filter_by(id=table.id)
            .with_for_update()
            .first()
        )
        if not locked:
            return jsonify({"error": "Table not found"}), 404

        order_items = []
        for raw in items:
            mid = _parse_uuid(raw.get("menu_item_id"))
            qty = int(raw.get("quantity") or 0)
            if not mid or qty < 1:
                db.session.rollback()
                return jsonify({"error": "Each item needs menu_item_id and quantity >= 1"}), 400
            menu_item = MenuItem.query.filter_by(id=mid, tenant_id=tenant_id).first()
            if not menu_item or not menu_item.available:
                db.session.rollback()
                return jsonify({"error": f"Menu item unavailable: {mid}"}), 400
            order_items.append((menu_item, qty))

        new_order = Order(
            tenant_id=tenant_id,
            table_number=table_number,
            status="pending",
            notes=notes,
        )
        db.session.add(new_order)
        db.session.flush()

        for menu_item, qty in order_items:
            db.session.add(
                OrderItem(
                    order_id=new_order.id,
                    menu_item_id=menu_item.id,
                    name=menu_item.name,
                    unit_price=menu_item.price,
                    quantity=qty,
                )
            )

        locked.version += 1
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
    """Legacy path — requires matching QR token so table numbers cannot be scanned freely."""
    table = _table_from_guest_token(request.args.get("token") or request.args.get("t"))
    tid = _parse_uuid(tenant_id)
    if not tid or not table:
        return jsonify({"error": "Valid table token is required"}), 401
    if table.tenant_id != tid or table.number != table_number:
        return jsonify({"error": "Token does not match this table"}), 403
    status = request.args.get("status")
    q = Order.query.filter_by(tenant_id=tid, table_number=table_number)
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
    order = Order.query.filter_by(id=order_id, tenant_id=tid, table_number=table.number).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"order": order.to_dict()})

@order_bp.route("/api/orders/kitchen", methods=["GET"])
@login_required
def kitchen_orders(tenant):
    """Open tickets for KDS: pending, preparing, ready."""
    orders = (
        Order.query.filter_by(tenant_id=tenant.id)
        .filter(Order.status.in_(OPEN_ORDER_STATUSES))
        .order_by(Order.created_at.asc())
        .all()
    )
    return jsonify({"orders": [o.to_dict() for o in orders]})


@order_bp.route("/api/orders/<uuid:order_id>/status", methods=["PATCH"])
@login_required
def update_order_status(tenant, order_id):
    """
    Medium lifecycle:
      pending → preparing | cancelled
      preparing → ready | cancelled
      ready → served | cancelled
    Optimistic concurrency via `version`.
    """
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

        order.status = new_status
        order.version += 1
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

    tenant_id = table.tenant_id
    table_number = table.number

    existing = WaiterCall.query.filter_by(
        tenant_id=tenant_id, table_number=table_number, status="open"
    ).first()
    if existing:
        return jsonify({"success": True, "call": existing.to_dict(), "already_open": True})

    call = WaiterCall(tenant_id=tenant_id, table_number=table_number, status="open")
    db.session.add(call)
    db.session.commit()
    payload = call.to_dict()
    emit_waiter_call(tenant_id, payload)
    emit_floor_refresh(tenant_id)
    return jsonify({"success": True, "call": payload}), 201


@order_bp.route("/api/orders/waiter-call/<uuid:call_id>/ack", methods=["POST"])
@login_required
def ack_waiter_call(tenant, call_id):
    """Admin acks the alert, then physically tells a waiter to visit the table."""
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
@login_required
def list_waiter_calls(tenant):
    status = request.args.get("status", "open")
    q = WaiterCall.query.filter_by(tenant_id=tenant.id)
    if status != "all":
        q = q.filter_by(status=status)
    calls = q.order_by(WaiterCall.created_at.desc()).limit(100).all()
    return jsonify({"calls": [c.to_dict() for c in calls]})
