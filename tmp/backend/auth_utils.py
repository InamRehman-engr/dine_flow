"""Auth decorators — JWT bearer preferred; legacy session still accepted during migration."""
from functools import wraps
import uuid

from flask import g, jsonify, session

from extensions import db
from jwt_utils import bearer_token_from_request, decode_access_token
from models import StaffUser, Tenant


def _load_staff_from_jwt():
    token = bearer_token_from_request()
    if not token:
        return None, None
    payload = decode_access_token(token)
    if not payload:
        return None, None
    try:
        staff = db.session.get(StaffUser, uuid.UUID(payload["sub"]))
        tenant = db.session.get(Tenant, uuid.UUID(payload["tid"]))
    except (ValueError, TypeError, KeyError):
        return None, None
    if not staff or not tenant or not staff.is_active or staff.deleted_at:
        return None, None
    if staff.tenant_id != tenant.id:
        return None, None
    return staff, tenant


def _load_from_legacy_session():
    tenant_id = session.get("tenant_id")
    staff_id = session.get("staff_id")
    if not tenant_id:
        return None, None
    try:
        tenant = db.session.get(Tenant, uuid.UUID(tenant_id))
    except (ValueError, TypeError):
        return None, None
    if not tenant:
        return None, None
    staff = None
    if staff_id:
        try:
            staff = db.session.get(StaffUser, uuid.UUID(staff_id))
        except (ValueError, TypeError):
            staff = None
    if not staff:
        # Fall back to first active manager for this tenant (legacy cookie-only sessions)
        staff = (
            StaffUser.query.filter_by(tenant_id=tenant.id, is_active=True)
            .filter(StaffUser.deleted_at.is_(None))
            .order_by(StaffUser.created_at.asc())
            .first()
        )
    return staff, tenant


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        staff, tenant = _load_staff_from_jwt()
        if not staff:
            staff, tenant = _load_from_legacy_session()
        if not staff or not tenant:
            return jsonify({"error": "Authentication required"}), 401
        g.staff = staff
        g.tenant = tenant
        return fn(tenant, *args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(tenant, *args, **kwargs):
            staff = g.staff
            if staff.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(tenant, *args, **kwargs)

        return wrapper

    return decorator


def manager_required(fn):
    return role_required("manager")(fn)


def kitchen_or_manager_required(fn):
    return role_required("manager", "kitchen")(fn)


def get_session_tenant():
    _, tenant = _load_staff_from_jwt()
    if tenant:
        return tenant
    _, tenant = _load_from_legacy_session()
    return tenant


def get_current_staff():
    return getattr(g, "staff", None)
