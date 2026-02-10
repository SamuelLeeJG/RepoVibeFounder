"""News aggregation client — Finnhub + Benzinga for ticker-specific news."""

from __future__ import annotations

import datetime as dt
from typing import Any

import httpx

from backend.config import settings


class NewsClient:
    """Aggregate news from Finnhub and Benzinga APIs."""

    def __init__(
        self,
        finnhub_key: str = settings.finnhub_api_key,
        benzinga_key: str = settings.benzinga_api_key,
    ):
        self.finnhub_key = finnhub_key
        self.benzinga_key = benzinga_key

    async def get_news(self, ticker: str, days_back: int = 7) -> list[dict]:
        """Get recent news for a ticker from all configured sources."""
        articles = []

        if self.finnhub_key:
            articles.extend(await self._finnhub_news(ticker, days_back))
        if self.benzinga_key:
            articles.extend(await self._benzinga_news(ticker, days_back))

        # Sort by date descending and deduplicate by headline
        seen_headlines = set()
        unique = []
        for a in sorted(articles, key=lambda x: x.get("published_at", ""), reverse=True):
            headline_key = a.get("headline", "").lower().strip()
            if headline_key not in seen_headlines:
                seen_headlines.add(headline_key)
                unique.append(a)

        return unique[:20]  # Cap at 20 articles

    async def _finnhub_news(self, ticker: str, days_back: int) -> list[dict]:
        """Fetch from Finnhub company news endpoint."""
        end = dt.date.today()
        start = end - dt.timedelta(days=days_back)
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": ticker,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "token": self.finnhub_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "headline": item.get("headline", ""),
                    "source": item.get("source", "Finnhub"),
                    "url": item.get("url", ""),
                    "published_at": dt.datetime.fromtimestamp(
                        item.get("datetime", 0), tz=dt.timezone.utc
                    ).isoformat(),
                    "sentiment": _simple_sentiment(item.get("headline", "")),
                    "summary": item.get("summary", ""),
                }
                for item in (data if isinstance(data, list) else [])
            ]
        except Exception:
            return []

    async def _benzinga_news(self, ticker: str, days_back: int) -> list[dict]:
        """Fetch from Benzinga news endpoint."""
        end = dt.date.today()
        start = end - dt.timedelta(days=days_back)
        url = "https://api.benzinga.com/api/v2/news"
        params = {
            "tickers": ticker,
            "dateFrom": start.isoformat(),
            "dateTo": end.isoformat(),
            "token": self.benzinga_key,
            "pageSize": 15,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            articles = data if isinstance(data, list) else data.get("results", [])
            return [
                {
                    "headline": item.get("title", ""),
                    "source": "Benzinga",
                    "url": item.get("url", ""),
                    "published_at": item.get("created", ""),
                    "sentiment": _simple_sentiment(item.get("title", "")),
                    "summary": item.get("teaser", ""),
                }
                for item in articles
            ]
        except Exception:
            return []


def _simple_sentiment(headline: str) -> str:
    """Basic keyword-based sentiment classification."""
    h = headline.lower()
    positive_words = ["surge", "jump", "rally", "beat", "upgrade", "rise", "gain", "bull", "record", "soar"]
    negative_words = ["crash", "drop", "plunge", "miss", "downgrade", "fall", "loss", "bear", "cut", "sink"]

    pos_count = sum(1 for w in positive_words if w in h)
    neg_count = sum(1 for w in negative_words if w in h)

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"
