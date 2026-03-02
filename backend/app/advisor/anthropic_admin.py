"""Client for Anthropic Admin API (Usage & Cost reports)."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.anthropic.com/v1/organizations"


def _headers() -> dict[str, str]:
    return {
        "x-api-key": settings.anthropic_admin_api_key,
        "anthropic-version": "2023-06-01",
    }


def available() -> bool:
    """True if an admin API key is configured."""
    return bool(settings.anthropic_admin_api_key)


async def fetch_cost_report(
    days: int = 30,
) -> list[dict[str, Any]] | None:
    """Fetch daily cost report from Anthropic Admin API.

    Returns list of daily cost buckets, or None on failure.
    """
    if not available():
        return None

    ending = datetime.now(UTC)
    starting = ending - timedelta(days=days)

    params = {
        "starting_at": starting.strftime("%Y-%m-%dT00:00:00Z"),
        "ending_at": ending.strftime("%Y-%m-%dT23:59:59Z"),
        "bucket_width": "1d",
        "group_by[]": "description",
    }

    try:
        all_data: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            page = None
            while True:
                p = {**params}
                if page:
                    p["page"] = page
                resp = await client.get(
                    f"{BASE_URL}/cost_report",
                    headers=_headers(),
                    params=p,
                )
                resp.raise_for_status()
                body = resp.json()
                all_data.extend(body.get("data", []))
                if not body.get("has_more"):
                    break
                page = body.get("next_page")
        return all_data
    except Exception:
        logger.exception("Failed to fetch Anthropic cost report")
        return None


async def fetch_usage_report(
    days: int = 30,
) -> list[dict[str, Any]] | None:
    """Fetch daily usage report from Anthropic Admin API.

    Returns list of daily usage buckets grouped by model,
    or None on failure.
    """
    if not available():
        return None

    ending = datetime.now(UTC)
    starting = ending - timedelta(days=days)

    params = {
        "starting_at": starting.strftime("%Y-%m-%dT00:00:00Z"),
        "ending_at": ending.strftime("%Y-%m-%dT23:59:59Z"),
        "bucket_width": "1d",
        "group_by[]": "model",
    }

    try:
        all_data: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            page = None
            while True:
                p = {**params}
                if page:
                    p["page"] = page
                resp = await client.get(
                    f"{BASE_URL}/usage_report/messages",
                    headers=_headers(),
                    params=p,
                )
                resp.raise_for_status()
                body = resp.json()
                all_data.extend(body.get("data", []))
                if not body.get("has_more"):
                    break
                page = body.get("next_page")
        return all_data
    except Exception:
        logger.exception("Failed to fetch Anthropic usage report")
        return None
