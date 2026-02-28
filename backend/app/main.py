from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.ws.hub import ws_prices, ws_signals

app = FastAPI(title=settings.app_name, debug=settings.debug)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket routes for real-time streaming
app.websocket("/ws/signals")(ws_signals)
app.websocket("/ws/prices")(ws_prices)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}
