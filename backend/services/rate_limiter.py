"""Smart rate limiter with tiered polling intervals for different data types."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Refresh tiers: how often each data type should update
REFRESH_TIERS = {
    "prices": 60,          # Every 60 seconds
    "signals": 300,        # Every 5 minutes
    "thesis": 0,           # On-demand only
    "news": 900,           # Every 15 minutes
    "events": 3600,        # Every hour
    "insider_trades": 3600,
    "politician_trades": 3600,
    "portfolio": 0,        # On-demand only
    "company_profile": 86400,  # Once per day
}

# API provider rate limits (requests per minute)
API_RATE_LIMITS = {
    "alpaca": 200,
    "fmp": 250,
    "quiver": 100,
    "finnhub": 60,
    "benzinga": 100,
}


@dataclass
class CacheEntry:
    data: Any
    fetched_at: float  # timestamp
    ttl: int  # seconds


class TieredRefreshManager:
    """Manages tiered refresh intervals and caching for API data.

    Prevents excessive API calls by caching results according to their
    refresh tier and enforcing per-provider rate limits.
    """

    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._provider_calls: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _cache_key(self, tier: str, identifier: str) -> str:
        return f"{tier}:{identifier}"

    def _is_fresh(self, key: str) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return False
        age = dt.datetime.now(dt.timezone.utc).timestamp() - entry.fetched_at
        return age < entry.ttl

    def get_cached(self, tier: str, identifier: str) -> Any | None:
        """Return cached data if still fresh, else None."""
        key = self._cache_key(tier, identifier)
        if self._is_fresh(key):
            return self._cache[key].data
        return None

    def set_cached(self, tier: str, identifier: str, data: Any, ttl: int | None = None):
        """Store data in cache."""
        if ttl is None:
            ttl = REFRESH_TIERS.get(tier, 300)
        key = self._cache_key(tier, identifier)
        self._cache[key] = CacheEntry(
            data=data,
            fetched_at=dt.datetime.now(dt.timezone.utc).timestamp(),
            ttl=ttl,
        )

    def check_rate_limit(self, provider: str) -> bool:
        """Check if we can make another call to this provider."""
        limit = API_RATE_LIMITS.get(provider, 100)
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        # Clean old entries (older than 60s)
        self._provider_calls[provider] = [
            t for t in self._provider_calls[provider] if now - t < 60
        ]
        return len(self._provider_calls[provider]) < limit

    def record_call(self, provider: str):
        """Record an API call for rate limiting."""
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        self._provider_calls[provider].append(now)

    async def fetch_with_cache(
        self,
        tier: str,
        identifier: str,
        provider: str,
        fetcher: Callable[[], Coroutine[Any, Any, Any]],
        ttl: int | None = None,
    ) -> Any:
        """Fetch data with caching and rate limiting.

        Returns cached data if fresh, otherwise calls fetcher and caches result.
        """
        cached = self.get_cached(tier, identifier)
        if cached is not None:
            return cached

        key = self._cache_key(tier, identifier)
        async with self._locks[key]:
            # Double-check after acquiring lock
            cached = self.get_cached(tier, identifier)
            if cached is not None:
                return cached

            if not self.check_rate_limit(provider):
                logger.warning(f"Rate limit reached for {provider}, returning stale data")
                entry = self._cache.get(key)
                if entry:
                    return entry.data
                return None

            self.record_call(provider)
            data = await fetcher()
            self.set_cached(tier, identifier, data, ttl)
            return data

    def invalidate(self, tier: str, identifier: str):
        """Force-invalidate a cache entry."""
        key = self._cache_key(tier, identifier)
        self._cache.pop(key, None)

    def invalidate_tier(self, tier: str):
        """Invalidate all entries for a tier."""
        to_remove = [k for k in self._cache if k.startswith(f"{tier}:")]
        for k in to_remove:
            del self._cache[k]

    def get_refresh_config(self) -> dict[str, int]:
        """Return the refresh tier configuration for the frontend."""
        return dict(REFRESH_TIERS)

    def get_stats(self) -> dict:
        """Return cache stats for monitoring."""
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        fresh = sum(1 for k in self._cache if self._is_fresh(k))
        return {
            "total_cached": len(self._cache),
            "fresh": fresh,
            "stale": len(self._cache) - fresh,
            "provider_calls_last_min": {
                provider: len([t for t in calls if now - t < 60])
                for provider, calls in self._provider_calls.items()
            },
        }


# Singleton instance
refresh_manager = TieredRefreshManager()
