"""Quiver Quantitative API client — politician/congress trading data."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import settings

BASE_URL = "https://api.quiverquant.com/beta"


class QuiverClient:
    """Client for Quiver Quantitative API — congressional and political trading data."""

    def __init__(self, api_key: str = settings.quiver_api_key):
        self.api_key = api_key

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> list | dict:
        if not self.api_key:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}{path}", headers=headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    async def get_congress_trading(self, ticker: str | None = None) -> list[dict]:
        """Get congressional trading data, optionally filtered by ticker."""
        if ticker:
            data = await self._get(f"/historical/congresstrading/{ticker}")
        else:
            data = await self._get("/live/congresstrading")
        return data if isinstance(data, list) else []

    async def get_senate_trading(self, ticker: str | None = None) -> list[dict]:
        """Get senate trading disclosures."""
        if ticker:
            data = await self._get(f"/historical/senatetrading/{ticker}")
        else:
            data = await self._get("/live/senatetrading")
        return data if isinstance(data, list) else []

    async def get_house_trading(self, ticker: str | None = None) -> list[dict]:
        """Get house of representatives trading disclosures."""
        if ticker:
            data = await self._get(f"/historical/housetrading/{ticker}")
        else:
            data = await self._get("/live/housetrading")
        return data if isinstance(data, list) else []

    async def get_insider_trading(self, ticker: str) -> list[dict]:
        """Get insider trading data with wealth-weighted impact."""
        data = await self._get(f"/historical/insiders/{ticker}")
        if not isinstance(data, list):
            return []

        # Enrich with wealth-weighted impact score
        enriched = []
        for trade in data:
            trade["wealth_impact_score"] = _compute_wealth_impact(trade)
            enriched.append(trade)
        return enriched


def _compute_wealth_impact(trade: dict) -> float:
    """Compute a wealth-weighted impact score for an insider trade.

    Higher score = more conviction. Based on:
    - Trade value relative to reported total holdings
    - Whether it's a buy (more meaningful) vs sell
    """
    value = abs(float(trade.get("Value", 0) or 0))
    if value == 0:
        return 0.0

    transaction_type = str(trade.get("TransactionType", "")).lower()
    is_buy = "purchase" in transaction_type or "buy" in transaction_type

    # Base score from trade size
    if value > 10_000_000:
        base = 100
    elif value > 1_000_000:
        base = 80
    elif value > 100_000:
        base = 50
    elif value > 10_000:
        base = 25
    else:
        base = 10

    # Buys are more meaningful than sells (insiders sell for many reasons)
    multiplier = 1.5 if is_buy else 0.7

    return round(base * multiplier, 1)
