import uuid

from flask import Blueprint, jsonify, request

from auth_utils import login_required
from extensions import db
from models import MenuCategory, MenuItem, Tenant

menu_bp = Blueprint("menu", __name__)


def _parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


@menu_bp.route("/api/menu/admin", methods=["GET"])
@login_required
def admin_menu(tenant):
    categories = (
        MenuCategory.query.filter_by(tenant_id=tenant.id)
        .order_by(MenuCategory.sort_order, MenuCategory.name)
        .all()
    )
    items = (
        MenuItem.query.filter_by(tenant_id=tenant.id)
        .order_by(MenuItem.name)
        .all()
    )
    return jsonify(
        {
            "categories": [c.to_dict() for c in categories],
            "items": [i.to_dict() for i in items],
        }
    )


@menu_bp.route("/api/menu/<tenant_id>", methods=["GET"])
def public_menu(tenant_id):
    """Customer-facing menu (QR). Only available items by default."""
    tid = _parse_uuid(tenant_id)
    if not tid:
        return jsonify({"error": "Invalid tenant_id"}), 400

    tenant = db.session.get(Tenant, tid)
    if not tenant:
        return jsonify({"error": "Restaurant not found"}), 404

    available_only = request.args.get("all", "0") != "1"
    categories = (
        MenuCategory.query.filter_by(tenant_id=tid)
        .order_by(MenuCategory.sort_order, MenuCategory.name)
        .all()
    )
    items_q = MenuItem.query.filter_by(tenant_id=tid)
    if available_only:
        items_q = items_q.filter_by(available=True)
    items = items_q.order_by(MenuItem.name).all()

    return jsonify(
        {
            "restaurant": {"id": str(tenant.id), "name": tenant.name},
            "categories": [c.to_dict() for c in categories],
            "items": [i.to_dict() for i in items],
        }
    )


@menu_bp.route("/api/menu/categories", methods=["POST"])
@login_required
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
@login_required
def update_category(tenant, category_id):
    cat = MenuCategory.query.filter_by(id=category_id, tenant_id=tenant.id).first()
    if not cat:
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
@login_required
def delete_category(tenant, category_id):
    cat = MenuCategory.query.filter_by(id=category_id, tenant_id=tenant.id).first()
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    for item in cat.items:
        item.category_id = None
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"success": True})


@menu_bp.route("/api/menu/items", methods=["POST"])
@login_required
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
        if not cat:
            return jsonify({"error": "Category not found"}), 404

    try:
        price = float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price"}), 400

    item = MenuItem(
        tenant_id=tenant.id,
        category_id=cat_uuid,
        name=name,
        description=(data.get("description") or "").strip() or None,
        price=price,
        image_url=(data.get("image_url") or "").strip() or None,
        available=bool(data.get("available", True)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "item": item.to_dict()}), 201


@menu_bp.route("/api/menu/items/<uuid:item_id>", methods=["PUT"])
@login_required
def update_item(tenant, item_id):
    item = MenuItem.query.filter_by(id=item_id, tenant_id=tenant.id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(silent=True) or {}

    # Optimistic concurrency on menu edits
    if "version" in data and int(data["version"]) != item.version:
        return jsonify({"error": "Item was updated elsewhere. Refresh and try again.", "item": item.to_dict()}), 409

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
    if "category_id" in data:
        category_id = data.get("category_id")
        if category_id is None or category_id == "":
            item.category_id = None
        else:
            cat_uuid = _parse_uuid(category_id)
            cat = MenuCategory.query.filter_by(id=cat_uuid, tenant_id=tenant.id).first()
            if not cat:
                return jsonify({"error": "Category not found"}), 404
            item.category_id = cat_uuid

    item.version += 1
    db.session.commit()
    return jsonify({"success": True, "item": item.to_dict()})


@menu_bp.route("/api/menu/items/<uuid:item_id>", methods=["DELETE"])
@login_required
def delete_item(tenant, item_id):
    item = MenuItem.query.filter_by(id=item_id, tenant_id=tenant.id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True})
