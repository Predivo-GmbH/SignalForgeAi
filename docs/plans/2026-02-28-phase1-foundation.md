# SignalForgeAI Phase 1 — Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stand up the full project skeleton — Docker infrastructure, FastAPI with auth, TimescaleDB with candle storage, CCXT data ingestion, core indicator library, Layers 1-2 of the signal engine, a basic backtest engine with CLI, and a frontend scaffold with auth pages and theme tokens.

**Architecture:** Monorepo with `/backend` (Python 3.12, FastAPI, SQLAlchemy 2.0, TimescaleDB) and `/frontend` (React 18, Vite, TypeScript, Tailwind 4, shadcn/ui). Docker Compose orchestrates all backend services (PG16+TimescaleDB, Redis 7, Nginx). Frontend is a static SPA built separately.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, ta-lib, pandas, numpy, ccxt, vectorbt, pytest | React 18, Vite, TypeScript, Tailwind 4, shadcn/ui, TanStack Query, Zustand, Vitest

**Project Root:** `C:\Business\Internal Projects\SignalForgeAI`

---

## Task 1: Git Init + Monorepo Scaffold

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/` (directory)
- Create: `frontend/` (directory)
- Create: `CLAUDE.md`

**Step 1: Initialize git repo**

```bash
cd "C:/Business/Internal Projects/SignalForgeAI"
git init
```

**Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
dist/
build/
.pytest_cache/
.mypy_cache/
*.egg

# Node
node_modules/
frontend/dist/

# Docker
docker-compose.override.yml

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Reference files (large)
kraken-reference/
*.zip
```

**Step 3: Create CLAUDE.md**

```markdown
# SignalForgeAI

## Project Structure
- `/backend` — Python 3.12 + FastAPI + SQLAlchemy 2.0
- `/frontend` — React 18 + Vite + TypeScript + Tailwind 4

## Commands
- Backend: `cd backend && docker compose up -d` (starts all services)
- Backend tests: `cd backend && pytest -v`
- Frontend dev: `cd frontend && npm run dev` (port 5173)
- Frontend tests: `cd frontend && npx vitest run`
- Frontend build: `cd frontend && npm run build`

## Rules
- NO hardcoded hex values in frontend components — use theme tokens from `lib/colors.ts`
- NO magic px values — use Tailwind classes
- All components must support dark/light theme
- Backend: TDD — write failing test first, then implement
- Backend: All API endpoints need integration tests
- Frontend: Vitest with globals: true — do NOT import from 'vitest'
```

**Step 4: Commit**

```bash
git add .gitignore CLAUDE.md
git commit -m "chore: init repo with gitignore and CLAUDE.md"
```

---

## Task 2: Backend Python Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "signalforge"
version = "0.1.0"
description = "Multi-layer automated trading platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "redis>=5.2.0",
    "celery>=5.4.0",
    "pandas>=2.2.0",
    "numpy>=2.0.0",
    "ta-lib>=0.5.1",
    "pandas-ta>=0.3.14b1",
    "ccxt>=4.4.0",
    "python-multipart>=0.0.18",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = ["ignore::DeprecationWarning"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
```

**Step 2: Create app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30
    jwt_refresh_expiry_days: int = 7

    # App
    app_name: str = "SignalForgeAI"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "SF_", "env_file": ".env"}


settings = Settings()
```

**Step 3: Create app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

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
```

**Step 4: Create empty __init__.py files**

```python
# backend/app/__init__.py — empty
# backend/tests/__init__.py — empty
```

**Step 5: Create tests/conftest.py**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Step 6: Write failing test for health endpoint**

Create `backend/tests/test_health.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "SignalForgeAI"
```

**Step 7: Install deps and run test**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows git bash
pip install -e ".[dev]"
pytest tests/test_health.py -v
```

Expected: PASS

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat(backend): FastAPI skeleton with health endpoint and config"
```

---

## Task 3: Docker Compose Infrastructure

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`
- Create: `backend/scripts/init-db.sql`

**Step 1: Create docker-compose.yml**

```yaml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: signalforge
      POSTGRES_PASSWORD: signalforge
      POSTGRES_DB: signalforge
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U signalforge"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      SF_DATABASE_URL: postgresql+asyncpg://signalforge:signalforge@db:5432/signalforge
      SF_REDIS_URL: redis://redis:6379/0
      SF_DEBUG: "true"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./app:/code/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  pgdata:
  redisdata:
```

**Step 2: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /code

# Install ta-lib C library
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make wget \
    && wget -q https://github.com/TA-Lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz \
    && tar -xzf ta-lib-0.6.4-src.tar.gz \
    && cd ta-lib-0.6.4 \
    && ./configure --prefix=/usr \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz \
    && apt-get purge -y gcc g++ make wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create scripts/init-db.sql**

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

**Step 4: Create .env.example**

```env
SF_DATABASE_URL=postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge
SF_REDIS_URL=redis://localhost:6379/0
SF_JWT_SECRET=change-me-in-production
SF_DEBUG=true
SF_CORS_ORIGINS=["http://localhost:5173"]
```

**Step 5: Verify Docker Compose starts**

```bash
cd backend
docker compose up -d db redis
docker compose ps
```

Expected: `db` and `redis` healthy.

**Step 6: Commit**

```bash
git add backend/docker-compose.yml backend/Dockerfile backend/.env.example backend/scripts/
git commit -m "infra: Docker Compose with TimescaleDB and Redis"
```

---

## Task 4: Database Models + Alembic Migrations

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/strategy.py`
- Create: `backend/app/models/candle.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (directory)

**Step 1: Create core/database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
```

**Step 2: Create models/base.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
```

**Step 3: Create models/user.py**

```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Step 4: Create models/strategy.py**

```python
import uuid

from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class Strategy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class BrokerConnection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "broker_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    broker: Mapped[str] = mapped_column(String(50), nullable=False)  # 'alpaca', 'binance', 'ib'
    api_key_enc: Mapped[bytes] = mapped_column(nullable=False)
    api_secret_enc: Mapped[bytes] = mapped_column(nullable=False)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Step 5: Create models/candle.py**

```python
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Candle(Base):
    __tablename__ = "candles"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(20), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(5), primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    trades: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_candles_symbol", "symbol", "timeframe", time.desc()),
    )
```

**Step 6: Create models/__init__.py**

```python
from app.models.base import Base
from app.models.user import User
from app.models.strategy import Strategy, BrokerConnection
from app.models.candle import Candle

__all__ = ["Base", "User", "Strategy", "BrokerConnection", "Candle"]
```

**Step 7: Set up Alembic**

```bash
cd backend
alembic init alembic
```

Then edit `alembic/env.py` to use async and our models:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.database_url,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 8: Generate and run initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial: users, strategies, broker_connections, candles"
alembic upgrade head
```

**Step 9: Verify tables exist**

```bash
docker compose exec db psql -U signalforge -c "\dt"
```

Expected: `users`, `strategies`, `broker_connections`, `candles` tables listed.

**Step 10: Create TimescaleDB hypertable for candles**

Create `backend/alembic/versions/002_create_hypertable.py` (manual migration):

```python
"""create hypertable for candles

Revision ID: 002
"""
from alembic import op


def upgrade():
    op.execute("SELECT create_hypertable('candles', 'time', if_not_exists => TRUE)")
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', time) AS time,
            symbol, exchange,
            first(open, time) AS open,
            max(high) AS high,
            min(low) AS low,
            last(close, time) AS close,
            sum(volume) AS volume
        FROM candles
        WHERE timeframe = '1m'
        GROUP BY time_bucket('1 hour', time), symbol, exchange
    """)


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS candles_1h")
```

**Step 11: Commit**

```bash
git add backend/app/core/ backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat(backend): SQLAlchemy models + Alembic migrations for users, strategies, candles"
```

---

## Task 5: JWT Authentication

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/jwt.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_auth.py`

**Step 1: Create core/security.py**

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**Step 2: Create auth/schemas.py**

```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
```

**Step 3: Create auth/jwt.py**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": user_id, "exp": expires, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expiry_days)
    payload = {"sub": user_id, "exp": expires, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
```

**Step 4: Create auth/router.py**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.schemas import LoginRequest, RegisterRequest, RefreshRequest, TokenResponse
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
```

**Step 5: Wire router into main.py**

Add to `backend/app/main.py`:

```python
from app.auth.router import router as auth_router

app.include_router(auth_router, prefix="/api")
```

**Step 6: Write auth tests**

Create `backend/tests/test_auth.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_register_new_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@signalforge.com",
        "password": "testpass123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dupe@signalforge.com",
        "password": "testpass123"
    })
    response = await client.post("/api/auth/register", json={
        "email": "dupe@signalforge.com",
        "password": "testpass123"
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    await client.post("/api/auth/register", json={
        "email": "login@signalforge.com",
        "password": "testpass123"
    })
    response = await client.post("/api/auth/login", json={
        "email": "login@signalforge.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    await client.post("/api/auth/register", json={
        "email": "bad@signalforge.com",
        "password": "testpass123"
    })
    response = await client.post("/api/auth/login", json={
        "email": "bad@signalforge.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client):
    reg = await client.post("/api/auth/register", json={
        "email": "refresh@signalforge.com",
        "password": "testpass123"
    })
    refresh_token = reg.json()["refresh_token"]
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

**Step 7: Run tests**

```bash
cd backend
pytest tests/test_auth.py -v
```

Note: These tests require a running DB or an in-memory SQLite override in conftest. Update `conftest.py` to use a test database:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.core.database import get_db
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with test_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

Add `aiosqlite` to dev dependencies in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "aiosqlite>=0.20.0",
]
```

**Step 8: Run tests — verify pass**

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Expected: All tests PASS.

**Step 9: Commit**

```bash
git add backend/app/auth/ backend/app/core/security.py backend/tests/
git commit -m "feat(backend): JWT auth with register, login, refresh endpoints"
```

---

## Task 6: Indicator Library

**Files:**
- Create: `backend/app/engine/__init__.py`
- Create: `backend/app/engine/indicators.py`
- Test: `backend/tests/test_indicators.py`

**Step 1: Write failing tests for indicators**

Create `backend/tests/test_indicators.py`:

```python
import numpy as np
import pandas as pd
import pytest

# Generate sample OHLCV data for testing
def make_candles(n=200, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.uniform(1000, 10000, n)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume
    })


class TestEMA:
    def test_ema_returns_series(self):
        from app.engine.indicators import compute_ema
        candles = make_candles()
        result = compute_ema(candles["close"], period=20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(candles)

    def test_ema_last_value_near_close(self):
        from app.engine.indicators import compute_ema
        candles = make_candles()
        result = compute_ema(candles["close"], period=1)
        # EMA with period 1 should equal close
        np.testing.assert_allclose(result.iloc[-1], candles["close"].iloc[-1], rtol=1e-5)


class TestRSI:
    def test_rsi_range(self):
        from app.engine.indicators import compute_rsi
        candles = make_candles()
        rsi = compute_rsi(candles["close"], period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


class TestMACD:
    def test_macd_returns_three_series(self):
        from app.engine.indicators import compute_macd
        candles = make_candles()
        macd, signal, hist = compute_macd(candles["close"])
        assert len(macd) == len(candles)
        assert len(signal) == len(candles)
        assert len(hist) == len(candles)


class TestATR:
    def test_atr_positive(self):
        from app.engine.indicators import compute_atr
        candles = make_candles()
        atr = compute_atr(candles, period=14)
        valid = atr.dropna()
        assert (valid > 0).all()


class TestStochastic:
    def test_stochastic_range(self):
        from app.engine.indicators import compute_stochastic
        candles = make_candles()
        slowk, slowd = compute_stochastic(candles)
        valid_k = slowk.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()


class TestVWAP:
    def test_vwap_returns_series(self):
        from app.engine.indicators import compute_vwap
        candles = make_candles()
        vwap = compute_vwap(candles)
        assert isinstance(vwap, pd.Series)
        assert len(vwap) == len(candles)


class TestFibonacci:
    def test_fib_levels_correct(self):
        from app.engine.indicators import calculate_fib_levels
        levels = calculate_fib_levels(swing_low=100.0, swing_high=200.0)
        assert levels[0.0] == 200.0
        assert levels[1.0] == 100.0
        assert abs(levels[0.5] - 150.0) < 0.01
        assert abs(levels[0.382] - (200.0 - 0.382 * 100)) < 0.01
        assert abs(levels[0.618] - (200.0 - 0.618 * 100)) < 0.01
```

**Step 2: Run tests — verify they fail**

```bash
pytest tests/test_indicators.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine.indicators'`

**Step 3: Implement indicators.py**

```python
"""
Indicator library wrapping ta-lib and pandas-ta.
All functions accept pandas Series/DataFrame and return pandas Series.
"""
import numpy as np
import pandas as pd

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    if HAS_TALIB:
        return pd.Series(talib.EMA(close.values, timeperiod=period), index=close.index)
    return close.ewm(span=period, adjust=False).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    if HAS_TALIB:
        return pd.Series(talib.RSI(close.values, timeperiod=period), index=close.index)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    if HAS_TALIB:
        macd, signal, hist = talib.MACD(close.values, fastperiod=fast, slowperiod=slow, signalperiod=signal_period)
        return (
            pd.Series(macd, index=close.index),
            pd.Series(signal, index=close.index),
            pd.Series(hist, index=close.index),
        )
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    if HAS_TALIB:
        return pd.Series(
            talib.ATR(candles["high"].values, candles["low"].values, candles["close"].values, timeperiod=period),
            index=candles.index,
        )
    high = candles["high"]
    low = candles["low"]
    prev_close = candles["close"].shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_stochastic(
    candles: pd.DataFrame, k_period: int = 14, d_period: int = 3, slowing: int = 3
) -> tuple[pd.Series, pd.Series]:
    if HAS_TALIB:
        slowk, slowd = talib.STOCH(
            candles["high"].values, candles["low"].values, candles["close"].values,
            fastk_period=k_period, slowk_period=slowing, slowd_period=d_period,
        )
        return pd.Series(slowk, index=candles.index), pd.Series(slowd, index=candles.index)
    lowest_low = candles["low"].rolling(window=k_period).min()
    highest_high = candles["high"].rolling(window=k_period).max()
    fastk = 100 * (candles["close"] - lowest_low) / (highest_high - lowest_low)
    slowk = fastk.rolling(window=slowing).mean()
    slowd = slowk.rolling(window=d_period).mean()
    return slowk, slowd


def compute_vwap(candles: pd.DataFrame) -> pd.Series:
    typical_price = (candles["high"] + candles["low"] + candles["close"]) / 3
    cum_vol = candles["volume"].cumsum()
    cum_tp_vol = (typical_price * candles["volume"]).cumsum()
    return cum_tp_vol / cum_vol


def calculate_fib_levels(swing_low: float, swing_high: float) -> dict[float, float]:
    diff = swing_high - swing_low
    return {
        0.0: swing_high,
        0.236: swing_high - 0.236 * diff,
        0.382: swing_high - 0.382 * diff,
        0.5: swing_high - 0.5 * diff,
        0.618: swing_high - 0.618 * diff,
        0.786: swing_high - 0.786 * diff,
        1.0: swing_low,
    }


def compute_adx(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    if HAS_TALIB:
        return pd.Series(
            talib.ADX(candles["high"].values, candles["low"].values, candles["close"].values, timeperiod=period),
            index=candles.index,
        )
    # Simplified ADX via directional movement
    high = candles["high"]
    low = candles["low"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    plus_dm = np.where((high - prev_high) > (prev_low - low), np.maximum(high - prev_high, 0), 0)
    minus_dm = np.where((prev_low - low) > (high - prev_high), np.maximum(prev_low - low, 0), 0)
    atr = compute_atr(candles, period)
    plus_di = 100 * pd.Series(plus_dm, index=candles.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=candles.index).rolling(period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return adx
```

**Step 4: Run tests — verify pass**

```bash
pytest tests/test_indicators.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add backend/app/engine/ backend/tests/test_indicators.py
git commit -m "feat(backend): indicator library — EMA, RSI, MACD, ATR, Stochastic, VWAP, Fibonacci, ADX"
```

---

## Task 7: Layer 1 — Trend Filter

**Files:**
- Create: `backend/app/engine/layers/__init__.py`
- Create: `backend/app/engine/layers/trend.py`
- Test: `backend/tests/test_trend_filter.py`

**Step 1: Write failing tests**

Create `backend/tests/test_trend_filter.py`:

```python
import numpy as np
import pandas as pd
import pytest


def make_bullish_candles(n=250):
    """Price trending up with aligned EMAs."""
    close = 100 + np.arange(n) * 0.5 + np.random.default_rng(42).normal(0, 0.3, n)
    high = close + np.random.default_rng(42).uniform(0.5, 1.5, n)
    low = close - np.random.default_rng(42).uniform(0.5, 1.5, n)
    return pd.DataFrame({"open": close + 0.1, "high": high, "low": low, "close": close, "volume": np.ones(n) * 5000})


def make_ranging_candles(n=250):
    """Price oscillating around 100 — no clear trend."""
    rng = np.random.default_rng(42)
    close = 100 + rng.normal(0, 2, n)
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({"open": close + 0.1, "high": high, "low": low, "close": close, "volume": np.ones(n) * 5000})


class TestTrendFilter:
    def test_bullish_trend_detected(self):
        from app.engine.layers.trend import TrendFilter, Trend
        tf = TrendFilter()
        result = tf.evaluate(make_bullish_candles())
        assert result.direction == Trend.BULLISH
        assert result.strength > 0

    def test_ranging_market_undetermined(self):
        from app.engine.layers.trend import TrendFilter, Trend
        tf = TrendFilter()
        result = tf.evaluate(make_ranging_candles())
        assert result.direction == Trend.UNDETERMINED
```

**Step 2: Run tests — verify fail**

```bash
pytest tests/test_trend_filter.py -v
```

**Step 3: Implement trend.py**

```python
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from app.engine.indicators import compute_ema, compute_vwap


class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    UNDETERMINED = "undetermined"


@dataclass
class TrendResult:
    direction: Trend
    strength: float
    vwap_aligned: bool | None = None


class TrendFilter:
    """
    Layer 1: Determines dominant trend direction.
    Uses 200 EMA as primary, 50/100 EMA alignment, and slope for strength.
    """

    def evaluate(self, candles: pd.DataFrame) -> TrendResult:
        close = candles["close"]

        if len(close) < 200:
            return TrendResult(direction=Trend.UNDETERMINED, strength=0)

        ema_200 = compute_ema(close, 200)
        ema_100 = compute_ema(close, 100)
        ema_50 = compute_ema(close, 50)

        ema_aligned_bull = (
            ema_50.iloc[-1] > ema_100.iloc[-1] > ema_200.iloc[-1]
        )
        ema_aligned_bear = (
            ema_50.iloc[-1] < ema_100.iloc[-1] < ema_200.iloc[-1]
        )

        # Trend strength via slope of 200 EMA (last 20 bars)
        if ema_200.iloc[-20] != 0:
            ema_slope = (ema_200.iloc[-1] - ema_200.iloc[-20]) / abs(ema_200.iloc[-20])
        else:
            ema_slope = 0

        # VWAP alignment (optional)
        vwap = compute_vwap(candles)
        above_vwap = close.iloc[-1] > vwap.iloc[-1]

        if ema_aligned_bull and ema_slope > 0.001:
            return TrendResult(
                direction=Trend.BULLISH,
                strength=abs(ema_slope),
                vwap_aligned=above_vwap,
            )
        elif ema_aligned_bear and ema_slope < -0.001:
            return TrendResult(
                direction=Trend.BEARISH,
                strength=abs(ema_slope),
                vwap_aligned=not above_vwap,
            )
        else:
            return TrendResult(
                direction=Trend.UNDETERMINED,
                strength=0,
                vwap_aligned=None,
            )
```

**Step 4: Run tests — verify pass**

```bash
pytest tests/test_trend_filter.py -v
```

**Step 5: Commit**

```bash
git add backend/app/engine/layers/ backend/tests/test_trend_filter.py
git commit -m "feat(backend): Layer 1 — TrendFilter with EMA alignment and slope detection"
```

---

## Task 8: Layer 2 — Zone Identifier

**Files:**
- Create: `backend/app/engine/layers/zones.py`
- Test: `backend/tests/test_zones.py`

**Step 1: Write failing tests**

Create `backend/tests/test_zones.py`:

```python
import numpy as np
import pandas as pd
import pytest


def make_candles_with_swing(n=200):
    """Creates data with a clear swing high/low for Fibonacci."""
    rng = np.random.default_rng(42)
    # Go up to 150, then retrace to ~130
    close = np.concatenate([
        100 + np.arange(100) * 0.5 + rng.normal(0, 0.3, 100),  # up to ~150
        150 - np.arange(100) * 0.2 + rng.normal(0, 0.3, 100),  # retrace to ~130
    ])
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1000, 5000, n)})


class TestZoneIdentifier:
    def test_finds_fibonacci_zones(self):
        from app.engine.layers.zones import ZoneIdentifier, EntryZone
        from app.engine.layers.trend import Trend, TrendResult
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        assert len(zones) > 0
        assert any(z.zone_type == "fibonacci_golden" for z in zones)

    def test_zones_have_upper_lower(self):
        from app.engine.layers.zones import ZoneIdentifier
        from app.engine.layers.trend import Trend, TrendResult
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        for z in zones:
            assert z.upper >= z.lower

    def test_vwap_zones_returned(self):
        from app.engine.layers.zones import ZoneIdentifier
        from app.engine.layers.trend import Trend, TrendResult
        zi = ZoneIdentifier()
        candles = make_candles_with_swing()
        trend = TrendResult(direction=Trend.BULLISH, strength=0.01)
        zones = zi.find_zones(candles, trend)
        assert any(z.zone_type.startswith("vwap") for z in zones)
```

**Step 2: Run tests — verify fail**

**Step 3: Implement zones.py**

```python
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.engine.indicators import calculate_fib_levels, compute_vwap
from app.engine.layers.trend import TrendResult, Trend


@dataclass
class EntryZone:
    zone_type: str
    upper: float
    lower: float
    strength: float
    levels: dict[float, float] | None = None

    def to_dict(self) -> dict:
        return {
            "zone_type": self.zone_type,
            "upper": self.upper,
            "lower": self.lower,
            "strength": self.strength,
        }


class ZoneIdentifier:
    """
    Layer 2: Finds potential entry zones using Fibonacci, VWAP bands,
    and support/resistance levels.
    """

    def find_zones(self, candles: pd.DataFrame, trend: TrendResult) -> list[EntryZone]:
        zones = []
        zones.extend(self._fibonacci_zones(candles, trend))
        zones.extend(self._vwap_deviation_zones(candles))
        return zones

    def _fibonacci_zones(self, candles: pd.DataFrame, trend: TrendResult) -> list[EntryZone]:
        swing_high_idx = candles["high"].idxmax()
        swing_low_idx = candles["low"].idxmin()
        swing_high = candles["high"].loc[swing_high_idx]
        swing_low = candles["low"].loc[swing_low_idx]

        if swing_high == swing_low:
            return []

        if trend.direction == Trend.BULLISH:
            fib_levels = calculate_fib_levels(swing_low, swing_high)
        else:
            fib_levels = calculate_fib_levels(swing_high, swing_low)

        golden_upper = fib_levels[0.382]
        golden_lower = fib_levels[0.618]

        if golden_upper < golden_lower:
            golden_upper, golden_lower = golden_lower, golden_upper

        return [
            EntryZone(
                zone_type="fibonacci_golden",
                upper=golden_upper,
                lower=golden_lower,
                strength=0.7,
                levels=fib_levels,
            )
        ]

    def _vwap_deviation_zones(self, candles: pd.DataFrame) -> list[EntryZone]:
        vwap = compute_vwap(candles)
        std = candles["close"].rolling(20).std()

        if std.iloc[-1] is None or np.isnan(std.iloc[-1]):
            return []

        vwap_val = vwap.iloc[-1]
        std_val = std.iloc[-1]

        return [
            EntryZone(
                zone_type="vwap_1sigma",
                upper=vwap_val + std_val,
                lower=vwap_val - std_val,
                strength=0.5,
            ),
            EntryZone(
                zone_type="vwap_2sigma",
                upper=vwap_val + 2 * std_val,
                lower=vwap_val - 2 * std_val,
                strength=0.8,
            ),
        ]
```

**Step 4: Run tests — verify pass**

```bash
pytest tests/test_zones.py -v
```

**Step 5: Commit**

```bash
git add backend/app/engine/layers/zones.py backend/tests/test_zones.py
git commit -m "feat(backend): Layer 2 — ZoneIdentifier with Fibonacci golden zone and VWAP bands"
```

---

## Task 9: Data Pipeline — CCXT Candle Ingestion + Storage

**Files:**
- Create: `backend/app/data/__init__.py`
- Create: `backend/app/data/storage.py`
- Create: `backend/app/data/ingestion.py`
- Test: `backend/tests/test_storage.py`

**Step 1: Write failing tests for storage**

Create `backend/tests/test_storage.py`:

```python
import pytest
from datetime import datetime, timezone

import pandas as pd


class TestCandleStorage:
    def test_save_and_load_candles(self):
        from app.data.storage import CandleStorage
        storage = CandleStorage()
        candles = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "timeframe": "1h",
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000.0] * 5,
        })
        storage.save_candles(candles)
        loaded = storage.load_candles("BTC/USDT", "1h", limit=5)
        assert len(loaded) == 5
        assert loaded["close"].iloc[-1] == 104.5
```

**Step 2: Implement storage.py (with in-memory fallback for tests)**

```python
"""
Candle storage — writes to TimescaleDB in production, in-memory for tests/CLI.
"""
import pandas as pd
from datetime import datetime, timezone


class CandleStorage:
    """In-memory candle storage. Production version will use TimescaleDB via SQLAlchemy."""

    def __init__(self):
        self._store: dict[str, pd.DataFrame] = {}

    def _key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}:{timeframe}"

    def save_candles(self, candles: pd.DataFrame) -> int:
        if candles.empty:
            return 0

        symbol = candles["symbol"].iloc[0]
        timeframe = candles["timeframe"].iloc[0]
        key = self._key(symbol, timeframe)

        if key in self._store:
            existing = self._store[key]
            combined = pd.concat([existing, candles]).drop_duplicates(subset=["time"], keep="last")
            combined = combined.sort_values("time").reset_index(drop=True)
            self._store[key] = combined
        else:
            self._store[key] = candles.sort_values("time").reset_index(drop=True)

        return len(candles)

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        key = self._key(symbol, timeframe)
        if key not in self._store:
            return pd.DataFrame()

        df = self._store[key]

        if since:
            df = df[df["time"] >= since]

        if limit:
            df = df.tail(limit)

        return df.reset_index(drop=True)
```

**Step 3: Implement ingestion.py**

```python
"""
CCXT-based candle ingestion.
Fetches historical OHLCV data and converts to our DataFrame format.
"""
import pandas as pd
import ccxt


class CCXTIngestion:
    """Fetches candles from exchanges via CCXT."""

    def __init__(self, exchange_id: str = "binance"):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({"enableRateLimit": True})

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: int | None = None,
    ) -> pd.DataFrame:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

        if not ohlcv:
            return pd.DataFrame()

        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
        df["symbol"] = symbol
        df["exchange"] = self.exchange.id
        df["timeframe"] = timeframe

        return df
```

**Step 4: Run tests**

```bash
pytest tests/test_storage.py -v
```

**Step 5: Commit**

```bash
git add backend/app/data/ backend/tests/test_storage.py
git commit -m "feat(backend): candle storage + CCXT ingestion pipeline"
```

---

## Task 10: Basic Backtest Engine + CLI

**Files:**
- Create: `backend/app/backtest/__init__.py`
- Create: `backend/app/backtest/engine.py`
- Create: `backend/app/cli.py`
- Test: `backend/tests/test_backtest.py`

**Step 1: Write failing tests**

Create `backend/tests/test_backtest.py`:

```python
import numpy as np
import pandas as pd
import pytest


def make_trending_candles(n=300):
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 1, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.2, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 10000, n),
    })


class TestBacktestEngine:
    def test_returns_result_with_metrics(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        assert "total_trades" in result.metrics
        assert "win_rate" in result.metrics
        assert "total_return_pct" in result.metrics
        assert "max_drawdown_pct" in result.metrics
        assert isinstance(result.equity_curve, list)
        assert len(result.equity_curve) > 0

    def test_equity_curve_starts_at_initial_capital(self):
        from app.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )
        assert result.equity_curve[0] == 10000.0
```

**Step 2: Implement backtest engine**

Create `backend/app/backtest/engine.py`:

```python
"""
Basic backtest engine. Runs the signal pipeline (Layers 1-2 for Phase 1)
on historical data and simulates trades.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.engine.layers.trend import TrendFilter, Trend
from app.engine.layers.zones import ZoneIdentifier
from app.engine.indicators import compute_atr


@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    direction: str
    stop_loss: float
    take_profit: float
    exit_idx: int | None = None
    exit_price: float | None = None
    pnl: float = 0.0

    @property
    def risk_reward(self) -> float:
        if self.exit_price is None:
            return 0
        reward = abs(self.exit_price - self.entry_price)
        risk = abs(self.entry_price - self.stop_loss)
        return reward / risk if risk > 0 else 0


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[float]
    metrics: dict


class BacktestEngine:
    """Walk-forward backtest using Layers 1-2 (TrendFilter + ZoneIdentifier)."""

    def __init__(self, lookback: int = 200, risk_pct: float = 0.02, atr_sl_mult: float = 2.0):
        self.lookback = lookback
        self.risk_pct = risk_pct
        self.atr_sl_mult = atr_sl_mult
        self.trend_filter = TrendFilter()
        self.zone_identifier = ZoneIdentifier()

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str,
        timeframe: str,
        initial_capital: float = 10000.0,
    ) -> BacktestResult:
        trades: list[Trade] = []
        equity_curve = [initial_capital]
        capital = initial_capital
        open_trade: Trade | None = None

        for i in range(self.lookback, len(candles)):
            window = candles.iloc[: i + 1]
            current = candles.iloc[i]

            # Check if we have an open trade to manage
            if open_trade:
                # Check stop loss
                if open_trade.direction == "BUY" and current["low"] <= open_trade.stop_loss:
                    open_trade.exit_idx = i
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.pnl = (open_trade.exit_price - open_trade.entry_price) * (capital * self.risk_pct / abs(open_trade.entry_price - open_trade.stop_loss))
                    capital += open_trade.pnl
                    trades.append(open_trade)
                    open_trade = None
                # Check take profit
                elif open_trade.direction == "BUY" and current["high"] >= open_trade.take_profit:
                    open_trade.exit_idx = i
                    open_trade.exit_price = open_trade.take_profit
                    open_trade.pnl = (open_trade.exit_price - open_trade.entry_price) * (capital * self.risk_pct / abs(open_trade.entry_price - open_trade.stop_loss))
                    capital += open_trade.pnl
                    trades.append(open_trade)
                    open_trade = None

                equity_curve.append(capital)
                continue

            # Run signal pipeline (Layers 1-2 only for Phase 1)
            trend = self.trend_filter.evaluate(window)
            if trend.direction == Trend.UNDETERMINED:
                equity_curve.append(capital)
                continue

            zones = self.zone_identifier.find_zones(window, trend)
            if not zones:
                equity_curve.append(capital)
                continue

            # Check if price is in any zone
            for zone in zones:
                if zone.lower <= current["close"] <= zone.upper:
                    atr = compute_atr(window, 14)
                    atr_val = atr.iloc[-1]
                    if np.isnan(atr_val) or atr_val <= 0:
                        continue

                    entry_price = current["close"]
                    if trend.direction == Trend.BULLISH:
                        stop_loss = entry_price - atr_val * self.atr_sl_mult
                        take_profit = entry_price + atr_val * self.atr_sl_mult * 1.5
                        direction = "BUY"
                    else:
                        stop_loss = entry_price + atr_val * self.atr_sl_mult
                        take_profit = entry_price - atr_val * self.atr_sl_mult * 1.5
                        direction = "SELL"

                    open_trade = Trade(
                        entry_idx=i,
                        entry_price=entry_price,
                        direction=direction,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )
                    break

            equity_curve.append(capital)

        # Close any remaining open trade at last price
        if open_trade:
            open_trade.exit_idx = len(candles) - 1
            open_trade.exit_price = candles["close"].iloc[-1]
            if open_trade.direction == "BUY":
                risk_dist = abs(open_trade.entry_price - open_trade.stop_loss)
                if risk_dist > 0:
                    open_trade.pnl = (open_trade.exit_price - open_trade.entry_price) * (capital * self.risk_pct / risk_dist)
            capital += open_trade.pnl
            trades.append(open_trade)
            equity_curve[-1] = capital

        metrics = self._calculate_metrics(trades, equity_curve, initial_capital)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)

    def _calculate_metrics(self, trades: list[Trade], equity_curve: list[float], initial_capital: float) -> dict:
        if not trades:
            return {
                "total_trades": 0, "win_rate": 0, "profit_factor": 0,
                "total_return_pct": 0, "max_drawdown_pct": 0,
                "sharpe_ratio": 0, "avg_risk_reward": 0,
            }

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        total_win = sum(t.pnl for t in wins) if wins else 0
        total_loss = abs(sum(t.pnl for t in losses)) if losses else 0

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades) * 100 if trades else 0,
            "profit_factor": total_win / total_loss if total_loss > 0 else float("inf"),
            "total_return_pct": (equity_curve[-1] - initial_capital) / initial_capital * 100,
            "max_drawdown_pct": max_dd,
            "sharpe_ratio": self._sharpe(equity_curve),
            "avg_risk_reward": np.mean([t.risk_reward for t in wins]) if wins else 0,
        }

    def _sharpe(self, equity_curve: list[float]) -> float:
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        if len(returns) == 0 or np.std(returns) == 0:
            return 0
        return float(np.mean(returns) / np.std(returns) * np.sqrt(252))
```

**Step 3: Create CLI**

Create `backend/app/cli.py`:

```python
"""
CLI for running backtests.
Usage: python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 90
"""
import argparse
import json
from datetime import datetime, timedelta, timezone

from app.backtest.engine import BacktestEngine
from app.data.ingestion import CCXTIngestion
from app.data.storage import CandleStorage


def cmd_backtest(args):
    print(f"Fetching {args.symbol} {args.timeframe} candles ({args.days} days)...")

    ingestion = CCXTIngestion(exchange_id=args.exchange)
    since = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp() * 1000)
    candles = ingestion.fetch_candles(args.symbol, args.timeframe, limit=1000, since=since)

    if candles.empty:
        print("No candles fetched. Check symbol and exchange.")
        return

    print(f"Fetched {len(candles)} candles.")
    print(f"Running backtest with ${args.capital} initial capital...")

    engine = BacktestEngine()
    result = engine.run(
        candles=candles,
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_capital=args.capital,
    )

    print("\n=== BACKTEST RESULTS ===")
    print(f"Symbol:          {args.symbol}")
    print(f"Timeframe:       {args.timeframe}")
    print(f"Period:          {args.days} days ({len(candles)} candles)")
    print(f"Initial Capital: ${args.capital:,.2f}")
    print(f"Final Capital:   ${result.equity_curve[-1]:,.2f}")
    print(f"---")
    for key, val in result.metrics.items():
        if isinstance(val, float):
            print(f"{key:20s}: {val:.2f}")
        else:
            print(f"{key:20s}: {val}")


def main():
    parser = argparse.ArgumentParser(description="SignalForgeAI CLI")
    subparsers = parser.add_subparsers()

    bt = subparsers.add_parser("backtest", help="Run a backtest")
    bt.add_argument("--symbol", required=True, help="Trading pair (e.g., BTC/USDT)")
    bt.add_argument("--timeframe", default="1h", help="Candle timeframe")
    bt.add_argument("--days", type=int, default=90, help="Days of history")
    bt.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    bt.add_argument("--exchange", default="binance", help="Exchange via CCXT")
    bt.set_defaults(func=cmd_backtest)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

Add `__main__.py` for `python -m app.cli`:

Create `backend/app/__main__.py`:

```python
from app.cli import main

main()
```

**Step 4: Run backtest tests**

```bash
pytest tests/test_backtest.py -v
```

Expected: PASS.

**Step 5: Test CLI (requires internet for CCXT)**

```bash
cd backend
python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 30
```

Expected: Fetches candles, runs backtest, prints results.

**Step 6: Commit**

```bash
git add backend/app/backtest/ backend/app/cli.py backend/app/__main__.py backend/tests/test_backtest.py
git commit -m "feat(backend): basic backtest engine + CLI tool for running backtests"
```

---

## Task 11: Frontend Scaffold — Vite + Tailwind + shadcn/ui

**Files:**
- Create: `frontend/` (full Vite project)

**Step 1: Scaffold Vite project**

```bash
cd "C:/Business/Internal Projects/SignalForgeAI"
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install Tailwind 4 + shadcn/ui dependencies**

```bash
cd frontend
npm install tailwindcss @tailwindcss/vite
npm install -D @types/node
npm install class-variance-authority clsx tailwind-merge lucide-react
npm install @radix-ui/react-slot
```

**Step 3: Configure Tailwind in vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
});
```

**Step 4: Set up CSS with theme tokens**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

:root {
  /* Background */
  --color-bg-base: #F7F5F2;
  --color-bg-surface: #FFFFFF;
  --color-bg-elevated: #F0EDE8;

  /* Border */
  --color-border: #E5E2DC;

  /* Text */
  --color-text-primary: #1A1A2E;
  --color-text-secondary: #6B6B80;

  /* Accent */
  --color-accent: #7B61FF;
  --color-accent-soft: rgba(123, 97, 255, 0.08);

  /* Semantic */
  --color-positive: #00A870;
  --color-negative: #E03E52;
  --color-warning: #E09A00;
}

.dark {
  --color-bg-base: #0B0B14;
  --color-bg-surface: #141420;
  --color-bg-elevated: #1C1C2E;

  --color-border: #2A2A3C;

  --color-text-primary: #F0F0F5;
  --color-text-secondary: #8B8BA0;

  --color-accent: #7B61FF;
  --color-accent-soft: rgba(123, 97, 255, 0.13);

  --color-positive: #00D68F;
  --color-negative: #FF4D6A;
  --color-warning: #FFB020;
}

body {
  background-color: var(--color-bg-base);
  color: var(--color-text-primary);
  font-family: "Inter", system-ui, -apple-system, sans-serif;
}

/* Monospace for prices/numbers */
.font-mono {
  font-family: "JetBrains Mono", "Fira Code", monospace;
}

/* Custom scrollbar (dark mode) */
.dark ::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.dark ::-webkit-scrollbar-track {
  background: var(--color-bg-base);
}
.dark ::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
}
```

**Step 5: Install Vitest**

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Add to `vite.config.ts`:

```typescript
/// <reference types="vitest" />
// (add to existing config)
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
```

Create `frontend/src/test-setup.ts`:

```typescript
import "@testing-library/jest-dom";
```

**Step 6: Add scripts to package.json**

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

**Step 7: Commit**

```bash
cd "C:/Business/Internal Projects/SignalForgeAI"
git add frontend/
git commit -m "feat(frontend): Vite + React + TypeScript + Tailwind 4 scaffold with theme tokens"
```

---

## Task 12: Frontend Theme System + Auth Pages

**Files:**
- Create: `frontend/src/lib/colors.ts`
- Create: `frontend/src/lib/theme.ts`
- Create: `frontend/src/lib/cn.ts`
- Create: `frontend/src/components/PasswordGate.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/App.tsx` (replace)

**Step 1: Create lib/colors.ts**

```typescript
/** Runtime color values — use for icon props, inline styles, JS logic. */
export const colors = {
  accent: "#7B61FF",
  accentSoft: "rgba(123, 97, 255, 0.1)",
  positive: { light: "#00A870", dark: "#00D68F" },
  negative: { light: "#E03E52", dark: "#FF4D6A" },
  warning: { light: "#E09A00", dark: "#FFB020" },
} as const;
```

**Step 2: Create lib/theme.ts**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "dark" | "light";

interface ThemeStore {
  theme: Theme;
  toggle: () => void;
  set: (theme: Theme) => void;
}

export const useTheme = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: "dark",
      toggle: () =>
        set((s) => {
          const next = s.theme === "dark" ? "light" : "dark";
          document.documentElement.classList.toggle("dark", next === "dark");
          return { theme: next };
        }),
      set: (theme) => {
        document.documentElement.classList.toggle("dark", theme === "dark");
        set({ theme });
      },
    }),
    { name: "sf-theme" }
  )
);
```

Install zustand:

```bash
cd frontend
npm install zustand
```

**Step 3: Create lib/cn.ts**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Step 4: Create PasswordGate.tsx**

```typescript
import { useState } from "react";

const GATE_PASSWORD = "signalforge2026";
const STORAGE_KEY = "sf-unlocked";

export function PasswordGate({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState(
    () => sessionStorage.getItem(STORAGE_KEY) === "true"
  );
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  if (unlocked) return <>{children}</>;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input === GATE_PASSWORD) {
      sessionStorage.setItem(STORAGE_KEY, "true");
      setUnlocked(true);
    } else {
      setError(true);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--color-bg-base)">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl bg-(--color-bg-surface) p-8 shadow-lg border border-(--color-border)"
      >
        <h1 className="mb-2 text-xl font-bold text-(--color-text-primary)">
          SignalForgeAI
        </h1>
        <p className="mb-6 text-sm text-(--color-text-secondary)">
          Enter password to continue
        </p>
        <input
          type="password"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setError(false);
          }}
          placeholder="Password"
          className="mb-4 w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-4 py-3 text-(--color-text-primary) outline-none focus:border-(--color-accent)"
        />
        {error && (
          <p className="mb-4 text-sm text-(--color-negative)">Wrong password</p>
        )}
        <button
          type="submit"
          className="w-full rounded-lg bg-(--color-accent) py-3 font-medium text-white hover:opacity-90 transition-opacity"
        >
          Enter
        </button>
      </form>
    </div>
  );
}
```

**Step 5: Create Login.tsx placeholder**

```typescript
export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-(--color-bg-base)">
      <div className="w-full max-w-sm rounded-xl bg-(--color-bg-surface) p-8 border border-(--color-border)">
        <h1 className="mb-6 text-2xl font-bold text-(--color-text-primary)">
          Sign In
        </h1>
        <p className="text-sm text-(--color-text-secondary)">
          Auth UI coming in Phase 4. Backend auth is ready.
        </p>
      </div>
    </div>
  );
}
```

**Step 6: Replace App.tsx**

```typescript
import { useEffect } from "react";
import { PasswordGate } from "./components/PasswordGate";
import { LoginPage } from "./pages/Login";
import { useTheme } from "./lib/theme";

function App() {
  const { theme } = useTheme();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, []);

  return (
    <PasswordGate>
      <LoginPage />
    </PasswordGate>
  );
}

export default App;
```

**Step 7: Verify it runs**

```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` — should see password gate, enter `signalforge2026`, then see login placeholder.

**Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): theme system, password gate, login page placeholder"
```

---

## Task 13: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check app/
      - run: pytest -v --tb=short

  frontend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npm run build
```

**Step 2: Commit**

```bash
git add .github/
git commit -m "ci: GitHub Actions for backend lint+test and frontend build"
```

---

## Summary — Phase 1 Deliverables

After completing all 13 tasks:

| Component | Status |
|-----------|--------|
| Git repo + monorepo structure | Done |
| Docker Compose (TimescaleDB + Redis) | Done |
| FastAPI skeleton + health check | Done |
| JWT auth (register, login, refresh) | Done |
| SQLAlchemy models + Alembic migrations | Done |
| Indicator library (EMA, RSI, MACD, ATR, Stoch, VWAP, Fib, ADX) | Done |
| Layer 1 — TrendFilter | Done |
| Layer 2 — ZoneIdentifier (Fibonacci + VWAP) | Done |
| Candle storage + CCXT ingestion | Done |
| Backtest engine + CLI | Done |
| Frontend scaffold (Vite + Tailwind + theme tokens) | Done |
| Password gate + auth page placeholder | Done |
| GitHub Actions CI | Done |

**Next:** Phase 2 plan (Layers 0, 3, 4, 5, 6 + walk-forward optimization) will be written after Phase 1 is complete.
