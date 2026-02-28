"""WebSocket hub for real-time signal and price streaming."""

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.jwt import decode_token


class ConnectionManager:
    """Manages WebSocket connections across named channels."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {
            "signals": [],
            "prices": [],
            "trades": [],
        }

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept a WebSocket connection and register it to a channel."""
        await websocket.accept()
        self.active_connections.setdefault(channel, []).append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from a channel."""
        if channel in self.active_connections:
            self.active_connections[channel] = [
                ws for ws in self.active_connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel: str, message: dict):
        """Send a message to all connections on a channel, removing dead ones."""
        dead = []
        for ws in self.active_connections.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()


async def ws_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal streaming.

    Accepts an optional ?token= query parameter for JWT authentication.
    Invalid tokens are rejected with close code 1008 (Policy Violation).
    """
    token = websocket.query_params.get("token")
    if token:
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=1008)
            return
    await manager.connect(websocket, "signals")
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
