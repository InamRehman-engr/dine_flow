import uuid

from flask import Blueprint, jsonify, request

from auth_utils import manager_required
from extensions import db
from models import MenuCategory, MenuItem, Modifier, ModifierGroup, Tenant, utcnow

menu_bp = Blueprint("menu", __name__)


def _parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _active_categories(tenant_id):
    return (
        MenuCategory.query.filter_by(tenant_id=tenant_id)
        .filter(MenuCategory.deleted_at.is_(None))
        .order_by(MenuCategory.sort_order, MenuCategory.name)
    )


def _active_items(tenant_id):
    return (
        MenuItem.query.filter_by(tenant_id=tenant_id)
        .filter(MenuItem.deleted_at.is_(None))
        .order_by(MenuItem.name)
    )


@menu_bp.route("/api/menu/admin", methods=["GET"])
@manager_required
def admin_menu(tenant):
    categories = _active_categories(tenant.id).all()
    items = _active_items(tenant.id).all()
    return jsonify(
        {
            "categories": [c.to_dict() for c in categories],
            "items": [i.to_dict(include_modifiers=True) for i in items],
        }
    )


@menu_bp.route("/api/menu/<tenant_id>", methods=["GET"])
def public_menu(tenant_id):
    tid = _parse_uuid(tenant_id)
    if not tid:
        return jsonify({"error": "Invalid tenant_id"}), 400

    tenant = db.session.get(Tenant, tid)
    if not tenant:
        return jsonify({"error": "Restaurant not found"}), 404

    available_only = request.args.get("all", "0") != "1"
    categories = _active_categories(tid).all()
    items_q = _active_items(tid)
    if available_only:
        items_q = items_q.filter_by(available=True)
    items = items_q.all()

    return jsonify(
        {
            "restaurant": {"id": str(tenant.id), "name": tenant.name},
            "categories": [c.to_dict() for c in categories],
            "items": [i.to_dict(include_modifiers=True) for i in items],
        }
    )


@menu_bp.route("/api/menu/categories", methods=["POST"])
@manager_required
def create_category(tenant):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Category name is required"}), 400
    sort_order = int(data.get("sort_order") or 0)
    cat = MenuCategory(tenant_id=tenant.id, name=name, sort_order=sort_order)
    db.session.add(cat)
    db.session.commit()
    return jsonify({"success": True, "category": cat.to_dict()}), 201


@menu_bp.route("/api/menu/categories/<uuid:category_id>", methods=["PUT"])
@manager_required
def update_category(tenant, category_id):
    cat = MenuCategory.query.filter_by(id=category_id, tenant_id=tenant.id).first()
    if not cat or cat.deleted_at:
        return jsonify({"error": "Category not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        cat.name = name
    if "sort_order" in data:
        cat.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify({"success": True, "category": cat.to_dict()})


@menu_bp.route("/api/menu/categories/<uuid:category_id>", methods=["DELETE"])
@manager_required
def delete_category(tenant, category_id):
    cat = MenuCategory.query.filter_by(id=category_id, tenant_id=tenant.id).first()
    if not cat or cat.deleted_at:
        return jsonify({"error": "Category not found"}), 404
    for item in cat.items:
        if not item.deleted_at:
            item.category_id = None
    cat.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})


@menu_bp.route("/api/menu/items", methods=["POST"])
@manager_required
def create_item(tenant):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Item name is required"}), 400

    category_id = data.get("category_id")
    cat_uuid = None
    if category_id:
        cat_uuid = _parse_uuid(category_id)
        cat = MenuCategory.query.filter_by(id=cat_uuid, tenant_id=tenant.id).first()
        if not cat or cat.deleted_at:
            return jsonify({"error": "Category not found"}), 404

    station_id = None
    if data.get("station_id"):
        station_id = _parse_uuid(data.get("station_id"))

    try:
        price = float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price"}), 400

    item = MenuItem(
        tenant_id=tenant.id,
        category_id=cat_uuid,
        station_id=station_id,
        name=name,
        description=(data.get("description") or "").strip() or None,
        price=price,
        image_url=(data.get("image_url") or "").strip() or None,
        available=bool(data.get("available", True)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "item": item.to_dict(include_modifiers=True)}), 201


@menu_bp.route("/api/menu/items/<uuid:item_id>", methods=["PUT"])
@manager_required
def update_item(tenant, item_id):
    item = MenuItem.query.filter_by(id=item_id, tenant_id=tenant.id).first()
    if not item or item.deleted_at:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(silent=True) or {}

    if "version" in data and int(data["version"]) != item.version:
        return jsonify(
            {"error": "Item was updated elsewhere. Refresh and try again.", "item": item.to_dict()}
        ), 409

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        item.name = name
    if "description" in data:
        item.description = (data.get("description") or "").strip() or None
    if "price" in data:
        try:
            item.price = float(data["price"])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid price"}), 400
    if "available" in data:
        item.available = bool(data["available"])
    if "image_url" in data:
        item.image_url = (data.get("image_url") or "").strip() or None
    if "station_id" in data:
        sid = data.get("station_id")
        item.station_id = _parse_uuid(sid) if sid else None
    if "category_id" in data:
        category_id = data.get("category_id")
        if category_id is None or category_id == "":
            item.category_id = None
        else:
            cat_uuid = _parse_uuid(category_id)
            cat = MenuCategory.query.filter_by(id=cat_uuid, tenant_id=tenant.id).first()
            if not cat or cat.deleted_at:
                return jsonify({"error": "Category not found"}), 404
            item.category_id = cat_uuid

    item.version += 1
    db.session.commit()
    return jsonify({"success": True, "item": item.to_dict(include_modifiers=True)})


@menu_bp.route("/api/menu/items/<uuid:item_id>", methods=["DELETE"])
@manager_required
def delete_item(tenant, item_id):
    item = MenuItem.query.filter_by(id=item_id, tenant_id=tenant.id).first()
    if not item or item.deleted_at:
        return jsonify({"error": "Item not found"}), 404
    item.deleted_at = utcnow()
    item.available = False
    db.session.commit()
    return jsonify({"success": True})


# ---------- Modifiers ----------


@menu_bp.route("/api/menu/items/<uuid:item_id>/modifier-groups", methods=["POST"])
@manager_required
def create_modifier_group(tenant, item_id):
    item = MenuItem.query.filter_by(id=item_id, tenant_id=tenant.id).first()
    if not item or item.deleted_at:
        return jsonify({"error": "Item not found"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Group name required"}), 400
    group = ModifierGroup(
        tenant_id=tenant.id,
        menu_item_id=item.id,
        name=name,
        required=bool(data.get("required", False)),
        max_select=int(data.get("max_select") or 1),
        sort_order=int(data.get("sort_order") or 0),
    )
    db.session.add(group)
    db.session.commit()
    return jsonify({"success": True, "group": group.to_dict()}), 201


@menu_bp.route("/api/menu/modifier-groups/<uuid:group_id>", methods=["PUT"])
@manager_required
def update_modifier_group(tenant, group_id):
    group = ModifierGroup.query.filter_by(id=group_id, tenant_id=tenant.id).first()
    if not group or group.deleted_at:
        return jsonify({"error": "Group not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name required"}), 400
        group.name = name
    if "required" in data:
        group.required = bool(data["required"])
    if "max_select" in data:
        group.max_select = int(data["max_select"])
    if "sort_order" in data:
        group.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify({"success": True, "group": group.to_dict()})


@menu_bp.route("/api/menu/modifier-groups/<uuid:group_id>", methods=["DELETE"])
@manager_required
def delete_modifier_group(tenant, group_id):
    group = ModifierGroup.query.filter_by(id=group_id, tenant_id=tenant.id).first()
    if not group or group.deleted_at:
        return jsonify({"error": "Group not found"}), 404
    group.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})


@menu_bp.route("/api/menu/modifier-groups/<uuid:group_id>/modifiers", methods=["POST"])
@manager_required
def create_modifier(tenant, group_id):
    group = ModifierGroup.query.filter_by(id=group_id, tenant_id=tenant.id).first()
    if not group or group.deleted_at:
        return jsonify({"error": "Group not found"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Modifier name required"}), 400
    try:
        price_delta = float(data.get("price_delta") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price_delta"}), 400
    mod = Modifier(
        group_id=group.id,
        name=name,
        price_delta=price_delta,
        sort_order=int(data.get("sort_order") or 0),
    )
    db.session.add(mod)
    db.session.commit()
    return jsonify({"success": True, "modifier": mod.to_dict()}), 201


@menu_bp.route("/api/menu/modifiers/<uuid:modifier_id>", methods=["PUT"])
@manager_required
def update_modifier(tenant, modifier_id):
    mod = db.session.get(Modifier, modifier_id)
    if not mod or mod.deleted_at or not mod.group or mod.group.tenant_id != tenant.id:
        return jsonify({"error": "Modifier not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name required"}), 400
        mod.name = name
    if "price_delta" in data:
        try:
            mod.price_delta = float(data["price_delta"])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid price_delta"}), 400
    if "sort_order" in data:
        mod.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify({"success": True, "modifier": mod.to_dict()})


@menu_bp.route("/api/menu/modifiers/<uuid:modifier_id>", methods=["DELETE"])
@manager_required
def delete_modifier(tenant, modifier_id):
    mod = db.session.get(Modifier, modifier_id)
    if not mod or mod.deleted_at or not mod.group or mod.group.tenant_id != tenant.id:
        return jsonify({"error": "Modifier not found"}), 404
    mod.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})
