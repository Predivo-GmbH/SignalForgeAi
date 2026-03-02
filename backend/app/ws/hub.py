"""WebSocket hub for real-time signal and price streaming."""

import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.jwt import decode_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections across named channels with user scoping."""

    def __init__(self):
        # channel -> list of (websocket, user_id | None)
        self.active_connections: dict[str, list[tuple[WebSocket, str | None]]] = {
            "signals": [],
            "prices": [],
            "trades": [],
        }

    async def connect(self, websocket: WebSocket, channel: str, user_id: str | None = None):
        """Accept a WebSocket connection and register it to a channel."""
        await websocket.accept()
        self.active_connections.setdefault(channel, []).append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from a channel."""
        if channel in self.active_connections:
            self.active_connections[channel] = [
                (ws, uid) for ws, uid in self.active_connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel: str, message: dict):
        """Send a message to all connections on a channel, removing dead ones.

        If the message contains a 'user_id' field, only send to that user's
        connections (or to connections with no user — e.g. prices channel).
        """
        target_user = message.get("user_id")
        dead = []
        for ws, uid in self.active_connections.get(channel, []):
            # If the message is user-scoped, only send to matching connections
            if target_user and uid and uid != target_user:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()


def _authenticate_ws(websocket: WebSocket) -> str | None:
    """Extract and validate JWT from WebSocket query params.

    Returns user_id on success, None on failure.
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


async def ws_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal streaming.

    Requires a valid ?token= query parameter for JWT authentication.
    Unauthenticated connections are rejected with close code 1008.
    """
    user_id = _authenticate_ws(websocket)
    if not user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, "signals", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "signals")


async def ws_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price streaming.

    No authentication required — price data is public.
    """
    await manager.connect(websocket, "prices")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "prices")


async def ws_trades(websocket: WebSocket):
    """WebSocket endpoint for real-time trade execution streaming.

    Requires a valid ?token= query parameter for JWT authentication.
    Unauthenticated connections are rejected with close code 1008.
    """
    user_id = _authenticate_ws(websocket)
    if not user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, "trades", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "trades")
