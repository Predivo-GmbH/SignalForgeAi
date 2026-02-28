import logging
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.alerts import router as alerts_router
from app.api.analytics import router as analytics_router
from app.api.backtests import router as backtests_router
from app.api.broker import router as broker_router
from app.api.journal import router as journal_router
from app.api.market import router as market_router
from app.api.positions import router as positions_router
from app.api.signals import router as signals_router
from app.api.strategies import router as strategies_router
from app.api.trades import router as trades_router
from app.auth.router import router as auth_router
from app.config import settings
from app.core.database import async_session
from app.core.logging_config import configure_logging
from app.core.redis_subscriber import RedisSubscriber
from app.ws.hub import manager, ws_prices, ws_signals, ws_trades

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
configure_logging(debug=settings.debug)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title=settings.app_name, debug=settings.debug)

# ---------------------------------------------------------------------------
# Rate limiting (slowapi)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(trades_router, prefix="/api")
app.include_router(strategies_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(backtests_router, prefix="/api")
app.include_router(positions_router, prefix="/api")
app.include_router(journal_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(broker_router, prefix="/api")

# ---------------------------------------------------------------------------
# WebSocket routes for real-time streaming
# ---------------------------------------------------------------------------
app.websocket("/ws/signals")(ws_signals)
app.websocket("/ws/prices")(ws_prices)
app.websocket("/ws/trades")(ws_trades)

# ---------------------------------------------------------------------------
# Redis subscriber for broadcasting pub/sub messages to WebSocket clients
# ---------------------------------------------------------------------------
_subscriber = RedisSubscriber(redis_url=settings.redis_url)


@app.on_event("startup")
async def _start_redis_subscriber() -> None:
    # JWT safety check for production
    if not settings.debug and settings.jwt_secret == "dev-secret-change-in-production":
        raise RuntimeError("JWT secret must be changed for production!")

    try:
        await _subscriber.start(manager.broadcast)
    except Exception as e:
        logger.warning("Redis subscriber failed to start: %s", e)


@app.on_event("shutdown")
async def _stop_redis_subscriber() -> None:
    await _subscriber.stop()


# ---------------------------------------------------------------------------
# Enhanced health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    status: dict = {
        "status": "ok",
        "service": settings.app_name,
        "db": "ok",
        "redis": "unknown",
        "celery": "unknown",
    }

    # Check database
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception:
        status["db"] = "error"
        status["status"] = "degraded"

    # Check Redis
    try:
        import redis

        r = redis.from_url(settings.redis_url)
        r.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "unavailable"

    return status
