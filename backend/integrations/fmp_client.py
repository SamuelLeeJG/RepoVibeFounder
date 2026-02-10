"""Financial Modeling Prep API client — earnings, insider trades, company profiles."""

from __future__ import annotations

import datetime as dt
from typing import Any

import httpx

from backend.config import settings

BASE_URL = "https://financialmodelingprep.com/api/v3"


class FMPClient:
    """Client for Financial Modeling Prep API."""

    def __init__(self, api_key: str = settings.fmp_api_key):
        self.api_key = api_key

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> list | dict:
        if not self.api_key:
            return []
        p = {"apikey": self.api_key}
        if params:
            p.update(params)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}{path}", params=p)
            resp.raise_for_status()
            return resp.json()

    async def get_earnings_calendar(
        self, from_date: str | None = None, to_date: str | None = None
    ) -> list[dict]:
        """Get upcoming earnings dates."""
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        data = await self._get("/earning_calendar", params)
        return data if isinstance(data, list) else []

    async def get_earnings_for_ticker(self, ticker: str) -> list[dict]:
        """Get earnings history for a specific ticker."""
        data = await self._get(f"/historical/earning_calendar/{ticker}", {"limit": 8})
        return data if isinstance(data, list) else []

    async def get_insider_trades(self, ticker: str, limit: int = 20) -> list[dict]:
        """Get insider trading activity for a ticker."""
        data = await self._get("/insider-trading", {"symbol": ticker, "limit": limit})
        return data if isinstance(data, list) else []

    async def get_company_profile(self, ticker: str) -> dict | None:
        """Get full company name and profile."""
        data = await self._get(f"/profile/{ticker}")
        if isinstance(data, list) and data:
            return data[0]
        return None

    async def get_company_name(self, ticker: str) -> str:
        """Get just the company name for a ticker."""
        profile = await self.get_company_profile(ticker)
        if profile:
            return profile.get("companyName", ticker)
        return ticker

    async def get_senate_trades(self, ticker: str | None = None) -> list[dict]:
        """Get congressional/senate trading disclosures."""
        params = {}
        if ticker:
            params["symbol"] = ticker
        data = await self._get("/senate-trading", params)
        return data if isinstance(data, list) else []
