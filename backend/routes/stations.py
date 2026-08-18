from flask import Blueprint, jsonify, request

from auth_utils import kitchen_or_manager_required, manager_required
from extensions import db
from models import KitchenStation, MenuItem, utcnow

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations", methods=["GET"])
@kitchen_or_manager_required
def list_stations(tenant):
    rows = (
        KitchenStation.query.filter_by(tenant_id=tenant.id)
        .filter(KitchenStation.deleted_at.is_(None))
        .order_by(KitchenStation.sort_order, KitchenStation.name)
        .all()
    )
    return jsonify({"stations": [s.to_dict() for s in rows]})


@stations_bp.route("/api/stations", methods=["POST"])
@manager_required
def create_station(tenant):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400
    station = KitchenStation(
        tenant_id=tenant.id,
        name=name,
        sort_order=int(data.get("sort_order") or 0),
    )
    db.session.add(station)
    db.session.commit()
    return jsonify({"success": True, "station": station.to_dict()}), 201


@stations_bp.route("/api/stations/<uuid:station_id>", methods=["PUT"])
@manager_required
def update_station(tenant, station_id):
    station = KitchenStation.query.filter_by(id=station_id, tenant_id=tenant.id).first()
    if not station or station.deleted_at:
        return jsonify({"error": "Station not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        station.name = name
    if "sort_order" in data:
        station.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify({"success": True, "station": station.to_dict()})


@stations_bp.route("/api/stations/<uuid:station_id>", methods=["DELETE"])
@manager_required
def delete_station(tenant, station_id):
    station = KitchenStation.query.filter_by(id=station_id, tenant_id=tenant.id).first()
    if not station or station.deleted_at:
        return jsonify({"error": "Station not found"}), 404
    MenuItem.query.filter_by(station_id=station.id).update({"station_id": None})
    station.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})
