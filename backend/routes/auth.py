import secrets
from datetime import timedelta

from flask import Blueprint, current_app, jsonify, make_response, request, session

from auth_utils import get_current_staff, login_required, manager_required
from config import Config
from extensions import db
from jwt_utils import (
    create_access_token,
    hash_token,
    new_refresh_raw,
)
from models import Floor, RefreshToken, StaffUser, Tenant, utcnow

auth_bp = Blueprint("auth", __name__)


def _set_refresh_cookie(response, raw_token: str):
    days = float(current_app.config.get("JWT_REFRESH_DAYS", 14))
    response.set_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        raw_token,
        httponly=True,
        samesite="Lax",
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
        max_age=int(days * 24 * 3600),
        path="/api/auth",
    )
    return response


def _clear_refresh_cookie(response):
    response.set_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        "",
        httponly=True,
        samesite="Lax",
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
        max_age=0,
        path="/api/auth",
    )
    return response


def _issue_tokens(staff: StaffUser, tenant: Tenant):
    access = create_access_token(staff, tenant)
    raw = new_refresh_raw()
    days = float(current_app.config.get("JWT_REFRESH_DAYS", 14))
    db.session.add(
        RefreshToken(
            staff_user_id=staff.id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + timedelta(days=days),
        )
    )
    db.session.commit()

    # Keep legacy session for backwards compatibility during rollout
    session.clear()
    session["tenant_id"] = str(tenant.id)
    session["staff_id"] = str(staff.id)
    session.permanent = True

    body = {
        "success": True,
        "access_token": access,
        "token_type": "Bearer",
        "tenant": tenant.to_dict(),
        "staff": staff.to_dict(),
    }
    resp = make_response(jsonify(body))
    return _set_refresh_cookie(resp, raw)


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or len(password) < 8:
        return jsonify({"error": "Name, email, and password (8+ chars) are required"}), 400

    if Tenant.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
    if StaffUser.query.filter_by(email=email).filter(StaffUser.deleted_at.is_(None)).first():
        return jsonify({"error": "Email already registered"}), 409

    tenant = Tenant(name=name, email=email)
    tenant.set_password(password)
    db.session.add(tenant)
    db.session.flush()

    manager = StaffUser(
        tenant_id=tenant.id,
        email=email,
        role="manager",
        display_name=name,
    )
    manager.set_password(password)
    db.session.add(manager)

    floor = Floor(tenant_id=tenant.id, name="Main Floor", sort_order=0)
    db.session.add(floor)
    db.session.commit()

    return _issue_tokens(manager, tenant)


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    staff = (
        StaffUser.query.filter_by(email=email, is_active=True)
        .filter(StaffUser.deleted_at.is_(None))
        .first()
    )
    if staff and staff.check_password(password):
        tenant = db.session.get(Tenant, staff.tenant_id)
        if not tenant:
            return jsonify({"error": "Invalid email or password"}), 401
        return _issue_tokens(staff, tenant)

    # Legacy: tenant-level password (pre-staff migration)
    tenant = Tenant.query.filter_by(email=email).first()
    if not tenant or not tenant.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    staff = (
        StaffUser.query.filter_by(tenant_id=tenant.id, email=email)
        .filter(StaffUser.deleted_at.is_(None))
        .first()
    )
    if not staff:
        staff = StaffUser(
            tenant_id=tenant.id,
            email=email,
            role="manager",
            display_name=tenant.name,
            password_hash=tenant.password_hash,
        )
        db.session.add(staff)
        db.session.commit()

    return _issue_tokens(staff, tenant)


@auth_bp.route("/api/auth/refresh", methods=["POST"])
def refresh():
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if not raw:
        return jsonify({"error": "Refresh token missing"}), 401
    row = RefreshToken.query.filter_by(token_hash=hash_token(raw)).first()
    if not row or row.revoked_at or row.expires_at < utcnow():
        return jsonify({"error": "Refresh token invalid"}), 401

    staff = db.session.get(StaffUser, row.staff_user_id)
    if not staff or not staff.is_active or staff.deleted_at:
        return jsonify({"error": "Staff inactive"}), 401
    tenant = db.session.get(Tenant, staff.tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant missing"}), 401

    # Rotate refresh token
    row.revoked_at = utcnow()
    return _issue_tokens(staff, tenant)


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if raw:
        row = RefreshToken.query.filter_by(token_hash=hash_token(raw)).first()
        if row and not row.revoked_at:
            row.revoked_at = utcnow()
            db.session.commit()
    session.clear()
    resp = make_response(jsonify({"success": True}))
    return _clear_refresh_cookie(resp)


@auth_bp.route("/api/auth/me", methods=["GET"])
@login_required
def me(tenant):
    staff = get_current_staff()
    return jsonify({"tenant": tenant.to_dict(), "staff": staff.to_dict() if staff else None})


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    tenant = Tenant.query.filter_by(email=email).first()
    staff = (
        StaffUser.query.filter_by(email=email)
        .filter(StaffUser.deleted_at.is_(None))
        .first()
    )

    response = {
        "success": True,
        "message": "If that email exists, a reset token was created.",
    }

    target = tenant
    if not target and staff:
        target = db.session.get(Tenant, staff.tenant_id)

    if target:
        token = secrets.token_urlsafe(24)
        target.reset_token = token
        target.reset_token_expires = utcnow() + timedelta(hours=Config.RESET_TOKEN_HOURS)
        db.session.commit()
        response["reset_token"] = token
        response["hint"] = "Use this token with /api/auth/reset-password (local MVP, no email)."

    return jsonify(response)


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    password = data.get("password") or ""

    if not token or len(password) < 8:
        return jsonify({"error": "Token and password (8+ chars) are required"}), 400

    tenant = Tenant.query.filter_by(reset_token=token).first()
    if not tenant or not tenant.reset_token_expires or tenant.reset_token_expires < utcnow():
        return jsonify({"error": "Invalid or expired reset token"}), 400

    tenant.set_password(password)
    tenant.reset_token = None
    tenant.reset_token_expires = None

    # Sync staff password for matching email
    staff = (
        StaffUser.query.filter_by(tenant_id=tenant.id, email=tenant.email)
        .filter(StaffUser.deleted_at.is_(None))
        .first()
    )
    if staff:
        staff.set_password(password)

    db.session.commit()
    return jsonify({"success": True, "message": "Password updated. You can log in now."})


@auth_bp.route("/api/auth/profile", methods=["PUT"])
@login_required
def update_profile(tenant):
    staff = get_current_staff()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if name:
        tenant.name = name
        if staff and staff.role == "manager":
            staff.display_name = name

    new_password = data.get("password")
    if new_password:
        if len(new_password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        if staff:
            staff.set_password(new_password)
        tenant.set_password(new_password)

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "tenant": tenant.to_dict(),
            "staff": staff.to_dict() if staff else None,
        }
    )


@auth_bp.route("/api/auth/staff", methods=["GET"])
@manager_required
def list_staff(tenant):
    rows = (
        StaffUser.query.filter_by(tenant_id=tenant.id)
        .filter(StaffUser.deleted_at.is_(None))
        .order_by(StaffUser.created_at.asc())
        .all()
    )
    return jsonify({"staff": [s.to_dict() for s in rows]})


@auth_bp.route("/api/auth/staff", methods=["POST"])
@manager_required
def create_staff(tenant):
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "kitchen").strip().lower()
    display_name = (data.get("display_name") or "").strip() or None

    if not email or len(password) < 8:
        return jsonify({"error": "Email and password (8+ chars) required"}), 400
    if role not in ("manager", "kitchen"):
        return jsonify({"error": "Role must be manager or kitchen"}), 400
    if StaffUser.query.filter_by(tenant_id=tenant.id, email=email).filter(StaffUser.deleted_at.is_(None)).first():
        return jsonify({"error": "Staff email already exists"}), 409

    staff = StaffUser(
        tenant_id=tenant.id,
        email=email,
        role=role,
        display_name=display_name,
    )
    staff.set_password(password)
    db.session.add(staff)
    db.session.commit()
    return jsonify({"success": True, "staff": staff.to_dict()}), 201


@auth_bp.route("/api/auth/staff/<uuid:staff_id>", methods=["DELETE"])
@manager_required
def soft_delete_staff(tenant, staff_id):
    staff = StaffUser.query.filter_by(id=staff_id, tenant_id=tenant.id).first()
    if not staff or staff.deleted_at:
        return jsonify({"error": "Staff not found"}), 404
    current = get_current_staff()
    if current and current.id == staff.id:
        return jsonify({"error": "Cannot delete yourself"}), 400
    staff.deleted_at = utcnow()
    staff.is_active = False
    db.session.commit()
    return jsonify({"success": True})
