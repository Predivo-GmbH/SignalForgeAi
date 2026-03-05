"""WebSocket hub for real-time signal and price streaming."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.jwt import decode_token

logger = logging.getLogger(__name__)


MAX_CONNECTIONS_PER_CHANNEL = 500


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
        conns = self.active_connections.setdefault(channel, [])
        if len(conns) >= MAX_CONNECTIONS_PER_CHANNEL:
            await websocket.close(code=1013, reason="Server too busy")
            return
        await websocket.accept()
        conns.append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from a channel."""
        if channel in self.active_connections:
            self.active_connections[channel] = [
                (ws, uid) for ws, uid in self.active_connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel: str, message: dict, user_id: str | None = None):
        """Send a message to all connections on a channel using parallel sends.

        If the message contains a 'user_id' field, only send to that user's
        connections (or to connections with no user -- e.g. prices channel).
        """
        target_user = user_id or message.get("user_id")
        conns = self.active_connections.get(channel, [])
        if not conns:
            return

        async def _safe_send(ws: WebSocket, uid: str | None) -> tuple[WebSocket, str | None, bool]:
            try:
                await ws.send_json(message)
            except Exception:
                return (ws, uid, True)  # Mark for removal
            return (ws, uid, False)

        targets = [
            (ws, uid) for ws, uid in conns
            if target_user is None or not uid or uid == target_user
        ]
        if not targets:
            return

        results = await asyncio.gather(
            *[_safe_send(ws, uid) for ws, uid in targets],
            return_exceptions=True,
        )

        # Clean up dead connections
        dead = {r[0] for r in results if isinstance(r, tuple) and r[2]}
        if dead:
            self.active_connections[channel] = [(ws, uid) for ws, uid in conns if ws not in dead]


manager = ConnectionManager()


async def _authenticate_ws(websocket: WebSocket) -> str | None:
    """Extract and validate JWT from WebSocket query params.

    Returns user_id on success, None on failure.
    Checks the token blacklist to reject revoked tokens.
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    iat = payload.get("iat")
    if user_id and iat is not None:
        from app.core.token_blacklist import are_user_tokens_invalid
        if await are_user_tokens_invalid(user_id, float(iat)):
            return None
    return user_id


async def ws_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal streaming.

    Requires a valid ?token= query parameter for JWT authentication.
    Unauthenticated connections are rejected with close code 1008.
    """
    user_id = await _authenticate_ws(websocket)
    if not user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, "signals", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "signals")
    except Exception as e:
        logger.exception("WebSocket error on signals: %s", e)
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
    except Exception as e:
        logger.exception("WebSocket error on prices: %s", e)
        manager.disconnect(websocket, "prices")


async def ws_trades(websocket: WebSocket):
    """WebSocket endpoint for real-time trade execution streaming.

    Requires a valid ?token= query parameter for JWT authentication.
    Unauthenticated connections are rejected with close code 1008.
    """
    user_id = await _authenticate_ws(websocket)
    if not user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, "trades", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "trades")
    except Exception as e:
        logger.exception("WebSocket error on trades: %s", e)
        manager.disconnect(websocket, "trades")
