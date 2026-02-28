from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.signals import router as signals_router
from app.api.strategies import router as strategies_router
from app.api.trades import router as trades_router
from app.auth.router import router as auth_router
from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(auth_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(trades_router, prefix="/api")
app.include_router(strategies_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}
