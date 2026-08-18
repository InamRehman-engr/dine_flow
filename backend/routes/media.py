from flask import Blueprint, jsonify, request

from auth_utils import manager_required
from media import upload_image

media_bp = Blueprint("media", __name__)

ALLOWED = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}


@media_bp.route("/api/media/upload", methods=["POST"])
@manager_required
def upload(tenant):
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "Empty file"}), 400
    ctype = (f.content_type or "").lower()
    if ctype not in ALLOWED:
        return jsonify({"error": "Only jpeg/png/webp/gif allowed"}), 400
    try:
        url = upload_image(f, prefix=f"tenant/{tenant.id}/menu")
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500
    return jsonify({"success": True, "url": url}), 201
