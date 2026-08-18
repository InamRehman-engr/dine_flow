from flask import request
from flask_socketio import emit, join_room, leave_room

from extensions import socketio


@socketio.on("connect")
def on_connect():
    emit("connected", {"ok": True})


@socketio.on("join_session")
def on_join_session(data):
    """
    Client / KDS / Admin joins a tenant room for realtime updates.
    data: { tenant_id: UUID string }
    """
    data = data or {}
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        emit("error", {"error": "tenant_id required"})
        return
    room = f"tenant:{tenant_id}"
    join_room(room)
    emit("joined", {"room": room, "sid": request.sid})


@socketio.on("leave_session")
def on_leave_session(data):
    data = data or {}
    tenant_id = data.get("tenant_id")
    if tenant_id:
        leave_room(f"tenant:{tenant_id}")
        emit("left", {"tenant_id": tenant_id})
