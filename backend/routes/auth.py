import secrets
from datetime import timedelta

from flask import Blueprint, jsonify, request, session

from auth_utils import login_required
from config import Config
from extensions import db
from models import Tenant, utcnow

auth_bp = Blueprint("auth", __name__)


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

    tenant = Tenant(name=name, email=email)
    tenant.set_password(password)
    db.session.add(tenant)
    db.session.commit()

    session.clear()
    session["tenant_id"] = str(tenant.id)
    session.permanent = True

    return jsonify({"success": True, "tenant": tenant.to_dict()}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    tenant = Tenant.query.filter_by(email=email).first()
    if not tenant or not tenant.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session["tenant_id"] = str(tenant.id)
    session.permanent = True

    return jsonify({"success": True, "tenant": tenant.to_dict()})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/api/auth/me", methods=["GET"])
@login_required
def me(tenant):
    return jsonify({"tenant": tenant.to_dict()})


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    tenant = Tenant.query.filter_by(email=email).first()

    # Always return success to avoid email enumeration
    response = {
        "success": True,
        "message": "If that email exists, a reset token was created.",
    }

    if tenant:
        token = secrets.token_urlsafe(24)
        tenant.reset_token = token
        tenant.reset_token_expires = utcnow() + timedelta(hours=Config.RESET_TOKEN_HOURS)
        db.session.commit()
        # Local-first: return token in response for MVP (no email SMTP)
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
    db.session.commit()

    return jsonify({"success": True, "message": "Password updated. You can log in now."})


@auth_bp.route("/api/auth/profile", methods=["PUT"])
@login_required
def update_profile(tenant):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if name:
        tenant.name = name

    new_password = data.get("password")
    if new_password:
        if len(new_password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        tenant.set_password(new_password)

    db.session.commit()
    return jsonify({"success": True, "tenant": tenant.to_dict()})
