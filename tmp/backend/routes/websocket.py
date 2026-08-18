from flask import request
from flask_socketio import emit, join_room, leave_room

from extensions import socketio
from jwt_utils import decode_access_token, decode_guest_socket_ticket


@socketio.on("connect")
def on_connect():
    emit("connected", {"ok": True})


@socketio.on("join_session")
def on_join_session(data):
    """
    Staff joins tenant room with access JWT.
    data: { access_token: str }  (tenant_id alone is no longer accepted)
    """
    data = data or {}
    token = data.get("access_token") or data.get("token")
    if not token:
        emit("error", {"error": "access_token required"})
        return
    payload = decode_access_token(token)
    if not payload:
        emit("error", {"error": "Invalid staff token"})
        return
    tenant_id = payload.get("tid")
    room = f"tenant:{tenant_id}"
    join_room(room)
    emit("joined", {"room": room, "sid": request.sid, "role": payload.get("role")})


@socketio.on("join_guest")
def on_join_guest(data):
    """Guest joins tenant room with signed guest socket ticket."""
    data = data or {}
    ticket = data.get("guest_ticket") or data.get("ticket")
    if not ticket:
        emit("error", {"error": "guest_ticket required"})
        return
    payload = decode_guest_socket_ticket(ticket)
    if not payload:
        emit("error", {"error": "Invalid guest ticket"})
        return
    tenant_id = payload.get("tid")
    room = f"tenant:{tenant_id}"
    join_room(room)
    emit(
        "joined",
        {
            "room": room,
            "sid": request.sid,
            "table_number": payload.get("table_number"),
            "guest": True,
        },
    )


@socketio.on("leave_session")
def on_leave_session(data):
    data = data or {}
    tenant_id = data.get("tenant_id")
    if tenant_id:
        leave_room(f"tenant:{tenant_id}")
        emit("left", {"tenant_id": tenant_id})
