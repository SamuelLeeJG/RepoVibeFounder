"""Plaid brokerage integration scaffold — link accounts and fetch holdings."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import settings

PLAID_ENV_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidClient:
    """Scaffold for Plaid API integration — brokerage account linking."""

    def __init__(
        self,
        client_id: str = settings.plaid_client_id,
        secret: str = settings.plaid_secret,
        env: str = settings.plaid_env,
    ):
        self.client_id = client_id
        self.secret = secret
        self.base_url = PLAID_ENV_URLS.get(env, PLAID_ENV_URLS["sandbox"])

    async def _post(self, path: str, body: dict[str, Any]) -> dict:
        if not self.client_id or not self.secret:
            return {"error": "Plaid credentials not configured"}
        body["client_id"] = self.client_id
        body["secret"] = self.secret
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base_url}{path}", json=body)
            resp.raise_for_status()
            return resp.json()

    async def create_link_token(self, user_id: str) -> dict:
        """Create a Plaid Link token for the frontend to launch Link."""
        return await self._post("/link/token/create", {
            "user": {"client_user_id": user_id},
            "client_name": "Alpha-Beta Terminal",
            "products": ["investments"],
            "country_codes": ["US"],
            "language": "en",
        })

    async def exchange_public_token(self, public_token: str) -> dict:
        """Exchange a public token from Plaid Link for an access token."""
        return await self._post("/item/public_token/exchange", {
            "public_token": public_token,
        })

    async def get_holdings(self, access_token: str) -> dict:
        """Get investment holdings from a linked brokerage account."""
        return await self._post("/investments/holdings/get", {
            "access_token": access_token,
        })

    async def get_transactions(
        self, access_token: str, start_date: str, end_date: str
    ) -> dict:
        """Get investment transactions from a linked brokerage."""
        return await self._post("/investments/transactions/get", {
            "access_token": access_token,
            "start_date": start_date,
            "end_date": end_date,
        })
