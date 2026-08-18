from functools import wraps
import uuid

from flask import jsonify, session

from extensions import db
from models import Tenant


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        tenant_id = session.get("tenant_id")
        if not tenant_id:
            return jsonify({"error": "Authentication required"}), 401
        tenant = db.session.get(Tenant, uuid.UUID(tenant_id))
        if not tenant:
            session.clear()
            return jsonify({"error": "Session invalid"}), 401
        return fn(tenant, *args, **kwargs)

    return wrapper


def get_session_tenant():
    tenant_id = session.get("tenant_id")
    if not tenant_id:
        return None
    try:
        return db.session.get(Tenant, uuid.UUID(tenant_id))
    except (ValueError, TypeError):
        return None
