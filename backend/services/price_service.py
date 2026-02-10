"""Tiered price refresh service — refreshes ~100 tickers per minute across 5 tiers.

All ~500 S&P 500 tickers are divided into 5 tiers of ~100 each.
A background task rotates through tiers, refreshing one tier every 60 seconds.
Full universe is refreshed every 5 minutes.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import math
from dataclasses import dataclass, field

from backend.data_provider import fetch_ohlcv

logger = logging.getLogger(__name__)

NUM_TIERS = 5
TIER_INTERVAL_SECONDS = 60  # Refresh one tier every 60 seconds


@dataclass
class TickerPrice:
    ticker: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    updated_at: str  # ISO timestamp


@dataclass
class TierStatus:
    tier: int
    tickers: list[str]
    last_refreshed: str | None = None
    refresh_count: int = 0
    avg_refresh_ms: float = 0.0


class TieredPriceService:
    """Manages tiered price refreshing for all S&P 500 tickers."""

    def __init__(self, all_tickers: list[str]):
        self._all_tickers = list(all_tickers)
        self._tiers: list[list[str]] = self._build_tiers()
        self._prices: dict[str, TickerPrice] = {}
        self._tier_status: list[TierStatus] = [
            TierStatus(tier=i, tickers=self._tiers[i]) for i in range(NUM_TIERS)
        ]
        self._current_tier: int = 0
        self._running: bool = False
        self._task: asyncio.Task | None = None

    def _build_tiers(self) -> list[list[str]]:
        """Split tickers into NUM_TIERS roughly equal groups."""
        tickers = self._all_tickers
        tier_size = math.ceil(len(tickers) / NUM_TIERS)
        return [tickers[i : i + tier_size] for i in range(0, len(tickers), tier_size)]

    # ── Public API ──

    def get_price(self, ticker: str) -> TickerPrice | None:
        return self._prices.get(ticker.upper())

    def get_all_prices(self) -> dict[str, TickerPrice]:
        return dict(self._prices)

    def get_tier_prices(self, tier: int) -> list[TickerPrice]:
        if tier < 0 or tier >= NUM_TIERS:
            return []
        return [self._prices[t] for t in self._tiers[tier] if t in self._prices]

    def get_tier_status(self) -> list[dict]:
        return [
            {
                "tier": ts.tier,
                "ticker_count": len(ts.tickers),
                "last_refreshed": ts.last_refreshed,
                "refresh_count": ts.refresh_count,
                "avg_refresh_ms": round(ts.avg_refresh_ms, 1),
                "next_refresh_in_s": self._seconds_until_tier(ts.tier),
            }
            for ts in self._tier_status
        ]

    def get_refresh_meta(self) -> dict:
        return {
            "num_tiers": NUM_TIERS,
            "tier_interval_seconds": TIER_INTERVAL_SECONDS,
            "full_cycle_seconds": NUM_TIERS * TIER_INTERVAL_SECONDS,
            "total_tickers": len(self._all_tickers),
            "cached_prices": len(self._prices),
            "current_tier": self._current_tier,
            "tiers": self.get_tier_status(),
        }

    def _seconds_until_tier(self, tier: int) -> int:
        if tier == self._current_tier:
            return 0
        ahead = (tier - self._current_tier) % NUM_TIERS
        return ahead * TIER_INTERVAL_SECONDS

    # ── Background refresh loop ──

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("TieredPriceService started (%d tickers, %d tiers)", len(self._all_tickers), NUM_TIERS)

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _refresh_loop(self):
        """Main loop: refresh one tier every TIER_INTERVAL_SECONDS."""
        while self._running:
            try:
                await self._refresh_tier(self._current_tier)
                self._current_tier = (self._current_tier + 1) % NUM_TIERS
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Price refresh error (tier %d): %s", self._current_tier, e)
            await asyncio.sleep(TIER_INTERVAL_SECONDS)

    async def _refresh_tier(self, tier: int):
        """Fetch latest prices for all tickers in a tier."""
        tickers = self._tiers[tier]
        start = dt.datetime.now(dt.timezone.utc)
        logger.info("Refreshing tier %d (%d tickers)...", tier, len(tickers))

        tasks = [self._fetch_price(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = 0
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.debug("Failed to fetch %s: %s", ticker, result)
                continue
            if result is not None:
                self._prices[ticker] = result
                success += 1

        elapsed = (dt.datetime.now(dt.timezone.utc) - start).total_seconds() * 1000
        status = self._tier_status[tier]
        status.last_refreshed = dt.datetime.now(dt.timezone.utc).isoformat()
        status.refresh_count += 1
        # Running average
        if status.refresh_count == 1:
            status.avg_refresh_ms = elapsed
        else:
            status.avg_refresh_ms = (status.avg_refresh_ms * 0.8) + (elapsed * 0.2)

        logger.info(
            "Tier %d refreshed: %d/%d success in %.0fms", tier, success, len(tickers), elapsed
        )

    async def _fetch_price(self, ticker: str) -> TickerPrice | None:
        """Fetch the latest close price for a single ticker."""
        try:
            df = await fetch_ohlcv(ticker, timeframe="1Day")
            if df.empty or len(df) < 2:
                return None
            close = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-2])
            change = close - prev
            change_pct = (change / prev * 100) if prev != 0 else 0.0
            return TickerPrice(
                ticker=ticker,
                price=round(close, 2),
                prev_close=round(prev, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            )
        except Exception:
            return None

    async def seed_all(self):
        """Initial seed: fetch all tickers at once on startup."""
        logger.info("Seeding all %d ticker prices...", len(self._all_tickers))
        for tier in range(NUM_TIERS):
            await self._refresh_tier(tier)
        logger.info("Seeding complete. %d prices cached.", len(self._prices))


# Singleton — initialized with SP500 tickers from routes
_service: TieredPriceService | None = None


def get_price_service() -> TieredPriceService:
    global _service
    if _service is None:
        from backend.api.routes import SP500_TICKERS
        _service = TieredPriceService(SP500_TICKERS)
    return _service
