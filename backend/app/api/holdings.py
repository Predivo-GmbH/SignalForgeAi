"""Holdings API — aggregated portfolio view, exchange balances, manual CRUD."""

import asyncio
import json
import logging
import uuid

import ccxt.async_support as ccxt_async
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_value
from app.execution.adapters.ccxt_adapter import CCXTAdapter
from app.models.holding import CostBasisOverride, ManualHolding
from app.models.position import Position
from app.models.strategy import BrokerConnection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/holdings", tags=["holdings"])

# Stablecoins pegged to ~$1 — no ticker lookup needed
_STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"}


# ---------- Schemas ----------


class HoldingItem(BaseModel):
    id: str | None = None
    symbol: str
    quantity: float
    avg_price: float | None = None
    current_price: float | None = None
    value_usd: float | None = None
    change_24h_pct: float | None = None
    allocation_pct: float | None = None
    source: str
    notes: str | None = None
    market_cap: int | None = None
    market_cap_rank: int | None = None
    volume_24h: float | None = None
    image_url: str | None = None


class HoldingsResponse(BaseModel):
    holdings: list[HoldingItem]
    total_value_usd: float | None = None


class ManualHoldingRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    purchase_price: float | None = None
    notes: str | None = Field(default=None, max_length=255)


class BulkImportRequest(BaseModel):
    holdings: list[ManualHoldingRequest] = Field(min_length=1, max_length=100)
    clear_existing: bool = False


class ManualHoldingResponse(BaseModel):
    id: str
    symbol: str
    quantity: float
    purchase_price: float | None = None
    notes: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class CostBasisRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    purchase_price: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=255)


class BulkCostBasisRequest(BaseModel):
    overrides: list[CostBasisRequest] = Field(min_length=1, max_length=100)
    clear_existing: bool = False


class CostBasisResponse(BaseModel):
    id: str
    symbol: str
    purchase_price: float
    notes: str | None = None

    model_config = {"from_attributes": True}


# ---------- Price helpers ----------


async def _fetch_prices_from_exchange(
    exchange_id: str,
    symbols: list[str],
) -> dict[str, dict[str, float | None]]:
    """Fetch prices from a single exchange for the given symbols.

    Returns only symbols that were successfully resolved.
    """
    result: dict[str, dict[str, float | None]] = {}
    exchange = getattr(ccxt_async, exchange_id)({"enableRateLimit": True})
    try:
        await exchange.load_markets()
        valid_pairs = [f"{s}/USDT" for s in symbols if f"{s}/USDT" in exchange.markets]
        if valid_pairs:
            tickers = await exchange.fetch_tickers(valid_pairs)
            for pair, ticker in tickers.items():
                sym = pair.split("/")[0]
                if ticker and ticker.get("last"):
                    result[sym] = {
                        "price": float(ticker["last"]),
                        "change_24h_pct": float(ticker.get("percentage") or 0),
                        "volume_24h": float(ticker.get("quoteVolume") or 0) or None,
                    }
    except Exception:
        logger.debug("Price fetch from %s failed", exchange_id)
    finally:
        await exchange.close()
    return result


# Fallback exchanges for symbols not found on Binance
_FALLBACK_EXCHANGES = ["kucoin", "kraken", "mexc", "gateio"]

# Symbols with known exchange ticker collisions — skip exchange lookups,
# go straight to CoinGecko which has explicit ID overrides for these.
_COINGECKO_ONLY = {"APAD", "ABX", "EX", "AYIN", "QUBIC"}


async def _fetch_prices(
    symbols: list[str],
) -> dict[str, dict[str, float | None]]:
    """Fetch current prices and 24h change for a list of crypto symbols.

    Uses Binance as primary, then falls back to other exchanges for
    symbols not found on Binance.
    Returns {symbol: {"price": float, "change_24h_pct": float}}.
    """
    result: dict[str, dict[str, float | None]] = {}
    # Assign stablecoins immediately
    non_stable = []
    for s in symbols:
        upper = s.upper()
        if upper in _STABLECOINS:
            result[upper] = {"price": 1.0, "change_24h_pct": 0.0}
        else:
            non_stable.append(upper)

    if not non_stable:
        return result

    # --- Check Redis cache first ---
    from app.core.redis_client import redis_client

    cache_key = "signalforge:prices:v1"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            # Return cached prices for all requested symbols
            for s in non_stable:
                if s in cached_data:
                    result[s] = cached_data[s]
            uncached = [s for s in non_stable if s not in result]
            if not uncached:
                return result
    except Exception:
        logger.debug("Redis price cache read failed, fetching fresh")

    # Separate CoinGecko-only symbols from exchange-eligible ones
    cg_only = [s for s in non_stable if s in _COINGECKO_ONLY]
    exchange_eligible = [s for s in non_stable if s not in _COINGECKO_ONLY]

    # Fire ALL exchange price lookups + CoinGecko in parallel
    from app.data.coingecko import fetch_coin_metadata, fetch_prices as cg_fetch_prices

    exchange_ids = ["binance"] + _FALLBACK_EXCHANGES
    tasks = []
    if exchange_eligible:
        tasks.extend(
            _fetch_prices_from_exchange(eid, exchange_eligible)
            for eid in exchange_ids
        )
    cg_all = cg_only + exchange_eligible  # CoinGecko covers everything as fallback
    if cg_all:
        tasks.append(cg_fetch_prices(cg_all))
    tasks.append(fetch_coin_metadata(non_stable))

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge exchange results: prefer Binance, then fallbacks in order
    exchange_count = len(exchange_ids) if exchange_eligible else 0
    for i in range(exchange_count):
        r = all_results[i]
        if isinstance(r, Exception):
            continue
        for sym, data in r.items():
            if sym not in result:  # first exchange to provide wins
                result[sym] = data

    # Merge CoinGecko prices for anything still missing
    cg_idx = exchange_count
    if cg_all:
        cg_result = all_results[cg_idx]
        if not isinstance(cg_result, Exception):
            for sym, data in cg_result.items():
                if sym not in result:
                    result[sym] = data
        cg_idx += 1

    # Merge CoinGecko metadata
    metadata_result = all_results[cg_idx] if cg_idx < len(all_results) else {}
    if not isinstance(metadata_result, Exception) and metadata_result:
        for sym, meta in metadata_result.items():
            if sym in result:
                result[sym]["market_cap"] = meta.get("market_cap")
                result[sym]["market_cap_rank"] = meta.get("market_cap_rank")
                result[sym]["image_url"] = meta.get("image_url")
                if not result[sym].get("volume_24h"):
                    result[sym]["volume_24h"] = meta.get("volume_24h")

    # Mark any still-missing symbols as None
    for s in non_stable:
        if s not in result:
            result[s] = {"price": None, "change_24h_pct": None}

    # --- Store in Redis cache ---
    try:
        await redis_client.set(cache_key, json.dumps(result), ex=60)
    except Exception:
        logger.debug("Redis price cache write failed")

    return result


def _enrich_holdings(
    holdings: list[HoldingItem],
    prices: dict[str, dict[str, float | None]],
) -> tuple[list[HoldingItem], float]:
    """Attach current_price, value_usd, change_24h_pct, allocation_pct."""
    enriched: list[HoldingItem] = []
    total = 0.0

    for h in holdings:
        info = prices.get(h.symbol.upper(), {})
        price = info.get("price")
        value = price * h.quantity if price is not None else None
        enriched.append(h.model_copy(update={
            "current_price": price,
            "value_usd": round(value, 2) if value is not None else None,
            "change_24h_pct": info.get("change_24h_pct"),
            "market_cap": info.get("market_cap"),
            "market_cap_rank": info.get("market_cap_rank"),
            "volume_24h": info.get("volume_24h"),
            "image_url": info.get("image_url"),
        }))
        if value is not None:
            total += value

    # Compute allocation percentages
    if total > 0:
        for h in enriched:
            if h.value_usd is not None:
                h.allocation_pct = round((h.value_usd / total) * 100, 2)

    return enriched, total


# ---------- Helpers ----------


async def _fetch_exchange_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Fetch balances from read-only live broker connections.

    Uses a 30-second Redis cache so page refreshes are instant.
    """
    from app.core.redis_client import redis_client

    cache_key = f"signalforge:exchange_balances:{user_id}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return [HoldingItem(**h) for h in json.loads(cached)]
    except Exception:
        pass

    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == uuid.UUID(user_id),
            BrokerConnection.is_paper.is_(False),
            BrokerConnection.purpose == "read",
        )
    )
    connections = result.scalars().all()

    async def _fetch_one(conn) -> list[HoldingItem]:
        try:
            api_key = decrypt_value(conn.api_key_enc)
            api_secret = decrypt_value(conn.api_secret_enc)
            passphrase = decrypt_value(conn.api_passphrase_enc) if conn.api_passphrase_enc else ""
            adapter = CCXTAdapter(
                exchange_id=conn.broker,
                api_key=api_key,
                api_secret=api_secret,
                password=passphrase,
                testnet=False,
            )
            try:
                balances = await adapter.get_full_balance()
                return [
                    HoldingItem(symbol=symbol, quantity=qty, source=conn.broker)
                    for symbol, qty in balances.items()
                ]
            finally:
                await adapter.close()
        except Exception:
            logger.exception("Failed to fetch balance from %s connection %s", conn.broker, conn.id)
            return []

    results = await asyncio.gather(*[_fetch_one(c) for c in connections])
    holdings = [h for batch in results for h in batch]

    # Cache for 30s so page refreshes are instant
    try:
        await redis_client.set(
            cache_key, json.dumps([h.model_dump() for h in holdings]), ex=30,
        )
    except Exception:
        pass

    return holdings


async def _fetch_trading_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Get open trading positions grouped by base symbol."""
    result = await db.execute(
        select(Position).where(
            Position.user_id == uuid.UUID(user_id),
            Position.is_open.is_(True),
        )
    )
    positions = result.scalars().all()
    grouped: dict[str, float] = {}
    for p in positions:
        # Extract base symbol (e.g. "BTC" from "BTC/USDT")
        base = p.symbol.split("/")[0] if "/" in p.symbol else p.symbol
        sign = 1.0 if p.direction.upper() in ("LONG", "BUY") else -1.0
        grouped[base] = grouped.get(base, 0) + (p.quantity * sign)

    return [
        HoldingItem(symbol=sym, quantity=qty, source="trading")
        for sym, qty in grouped.items()
        if abs(qty) > 1e-12
    ]


async def _fetch_manual_holdings(
    db: AsyncSession, user_id: str,
) -> list[HoldingItem]:
    """Get all manual holdings for the user."""
    result = await db.execute(
        select(ManualHolding).where(ManualHolding.user_id == uuid.UUID(user_id))
        .order_by(ManualHolding.symbol)
    )
    rows = result.scalars().all()
    return [
        HoldingItem(
            id=str(h.id),
            symbol=h.symbol,
            quantity=h.quantity,
            avg_price=h.purchase_price,
            source="manual",
            notes=h.notes,
        )
        for h in rows
    ]


# ---------- Routes ----------


@router.get("", response_model=HoldingsResponse)
async def get_aggregated_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated view: exchange balances + manual holdings + trading positions."""
    # DB queries are fast (ms) — keep sequential to avoid session conflicts.
    # Exchange API calls (the bottleneck) are parallelized inside _fetch_exchange_holdings.
    exchange = await _fetch_exchange_holdings(db, user_id)
    manual = await _fetch_manual_holdings(db, user_id)
    trading = await _fetch_trading_holdings(db, user_id)
    all_holdings = exchange + manual + trading

    # Fetch cost basis overrides (apply to holdings without avg_price)
    uid = uuid.UUID(user_id)
    cb_result = await db.execute(
        select(CostBasisOverride).where(CostBasisOverride.user_id == uid)
    )
    cost_overrides: dict[str, float] = {
        row.symbol.upper(): row.purchase_price
        for row in cb_result.scalars().all()
    }

    # Apply cost basis overrides to holdings that lack avg_price
    for h in all_holdings:
        if h.avg_price is None and h.symbol.upper() in cost_overrides:
            h.avg_price = cost_overrides[h.symbol.upper()]

    # Enrich with live prices
    if all_holdings:
        unique_symbols = list({h.symbol.upper() for h in all_holdings})
        prices = await _fetch_prices(unique_symbols)
        all_holdings, total = _enrich_holdings(all_holdings, prices)
    else:
        total = 0.0

    # Sort by value descending (holdings with value first, then the rest)
    all_holdings.sort(
        key=lambda h: (h.value_usd is not None, h.value_usd or 0),
        reverse=True,
    )

    return HoldingsResponse(
        holdings=all_holdings,
        total_value_usd=round(total, 2) if total > 0 else None,
    )


@router.get("/exchange", response_model=list[HoldingItem])
async def get_exchange_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch live balances from connected exchanges."""
    return await _fetch_exchange_holdings(db, user_id)


@router.get("/manual", response_model=list[ManualHoldingResponse])
async def list_manual_holdings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all manual holdings."""
    result = await db.execute(
        select(ManualHolding).where(ManualHolding.user_id == uuid.UUID(user_id))
        .order_by(ManualHolding.symbol)
    )
    rows = result.scalars().all()
    return [
        ManualHoldingResponse(
            id=str(h.id),
            symbol=h.symbol,
            quantity=h.quantity,
            purchase_price=h.purchase_price,
            notes=h.notes,
            created_at=h.created_at.isoformat() if h.created_at else "",
        )
        for h in rows
    ]


@router.post("/manual", response_model=ManualHoldingResponse, status_code=201)
async def add_manual_holding(
    body: ManualHoldingRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a manual crypto holding."""
    holding = ManualHolding(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        symbol=body.symbol.upper(),
        quantity=body.quantity,
        purchase_price=body.purchase_price,
        notes=body.notes,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return ManualHoldingResponse(
        id=str(holding.id),
        symbol=holding.symbol,
        quantity=holding.quantity,
        purchase_price=holding.purchase_price,
        notes=holding.notes,
        created_at=holding.created_at.isoformat() if holding.created_at else "",
    )


@router.put("/manual/{holding_id}", response_model=ManualHoldingResponse)
async def update_manual_holding(
    holding_id: str,
    body: ManualHoldingRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a manual holding."""
    result = await db.execute(
        select(ManualHolding).where(
            ManualHolding.id == uuid.UUID(holding_id),
            ManualHolding.user_id == uuid.UUID(user_id),
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    holding.symbol = body.symbol.upper()
    holding.quantity = body.quantity
    holding.purchase_price = body.purchase_price
    holding.notes = body.notes
    await db.commit()
    await db.refresh(holding)
    return ManualHoldingResponse(
        id=str(holding.id),
        symbol=holding.symbol,
        quantity=holding.quantity,
        purchase_price=holding.purchase_price,
        notes=holding.notes,
        created_at=holding.created_at.isoformat() if holding.created_at else "",
    )


@router.delete("/manual/{holding_id}", status_code=204)
async def delete_manual_holding(
    holding_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manual holding."""
    result = await db.execute(
        select(ManualHolding).where(
            ManualHolding.id == uuid.UUID(holding_id),
            ManualHolding.user_id == uuid.UUID(user_id),
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    await db.delete(holding)
    await db.commit()


@router.post("/manual/bulk", response_model=list[ManualHoldingResponse], status_code=201)
async def bulk_import_holdings(
    body: BulkImportRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import manual holdings. Optionally clears existing manual holdings first."""
    uid = uuid.UUID(user_id)

    if body.clear_existing:
        result = await db.execute(
            select(ManualHolding).where(ManualHolding.user_id == uid)
        )
        for h in result.scalars().all():
            await db.delete(h)

    created: list[ManualHolding] = []
    for item in body.holdings:
        holding = ManualHolding(
            id=uuid.uuid4(),
            user_id=uid,
            symbol=item.symbol.upper(),
            quantity=item.quantity,
            purchase_price=item.purchase_price,
            notes=item.notes,
        )
        db.add(holding)
        created.append(holding)

    await db.commit()
    for h in created:
        await db.refresh(h)

    return [
        ManualHoldingResponse(
            id=str(h.id),
            symbol=h.symbol,
            quantity=h.quantity,
            purchase_price=h.purchase_price,
            notes=h.notes,
            created_at=h.created_at.isoformat() if h.created_at else "",
        )
        for h in created
    ]


# ---------- Cost Basis Override routes ----------


@router.get("/cost-basis", response_model=list[CostBasisResponse])
async def list_cost_basis_overrides(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cost basis overrides for the user."""
    result = await db.execute(
        select(CostBasisOverride)
        .where(CostBasisOverride.user_id == uuid.UUID(user_id))
        .order_by(CostBasisOverride.symbol)
    )
    return [
        CostBasisResponse(
            id=str(r.id), symbol=r.symbol,
            purchase_price=r.purchase_price, notes=r.notes,
        )
        for r in result.scalars().all()
    ]


@router.put("/cost-basis/{symbol}", response_model=CostBasisResponse)
async def upsert_cost_basis(
    symbol: str,
    body: CostBasisRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update cost basis for a symbol."""
    uid = uuid.UUID(user_id)
    sym = symbol.upper()
    result = await db.execute(
        select(CostBasisOverride).where(
            CostBasisOverride.user_id == uid,
            CostBasisOverride.symbol == sym,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.purchase_price = body.purchase_price
        row.notes = body.notes
    else:
        row = CostBasisOverride(
            id=uuid.uuid4(), user_id=uid, symbol=sym,
            purchase_price=body.purchase_price, notes=body.notes,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return CostBasisResponse(
        id=str(row.id), symbol=row.symbol,
        purchase_price=row.purchase_price, notes=row.notes,
    )


@router.delete("/cost-basis/{symbol}", status_code=204)
async def delete_cost_basis(
    symbol: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a cost basis override."""
    result = await db.execute(
        select(CostBasisOverride).where(
            CostBasisOverride.user_id == uuid.UUID(user_id),
            CostBasisOverride.symbol == symbol.upper(),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost basis not found")
    await db.delete(row)
    await db.commit()


@router.post("/cost-basis/bulk", response_model=list[CostBasisResponse], status_code=201)
async def bulk_import_cost_basis(
    body: BulkCostBasisRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk upsert cost basis overrides. Optionally clears existing first."""
    uid = uuid.UUID(user_id)

    if body.clear_existing:
        result = await db.execute(
            select(CostBasisOverride).where(CostBasisOverride.user_id == uid)
        )
        for r in result.scalars().all():
            await db.delete(r)

    created: list[CostBasisOverride] = []
    for item in body.overrides:
        sym = item.symbol.upper()
        # Upsert: check for existing
        result = await db.execute(
            select(CostBasisOverride).where(
                CostBasisOverride.user_id == uid,
                CostBasisOverride.symbol == sym,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.purchase_price = item.purchase_price
            existing.notes = item.notes
            created.append(existing)
        else:
            row = CostBasisOverride(
                id=uuid.uuid4(), user_id=uid, symbol=sym,
                purchase_price=item.purchase_price, notes=item.notes,
            )
            db.add(row)
            created.append(row)

    await db.commit()
    for r in created:
        await db.refresh(r)

    return [
        CostBasisResponse(
            id=str(r.id), symbol=r.symbol,
            purchase_price=r.purchase_price, notes=r.notes,
        )
        for r in created
    ]
