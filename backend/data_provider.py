"""Data provider that fetches OHLCV data from Alpaca or falls back to generated data."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd

from backend.config import settings

_CACHE: dict[str, pd.DataFrame] = {}


def _generate_synthetic(
    ticker: str,
    start: dt.datetime,
    end: dt.datetime,
    timeframe: str = "1Hour",
) -> pd.DataFrame:
    """Generate plausible synthetic OHLCV data for demo / offline mode."""
    rng = np.random.default_rng(abs(hash(ticker)) % (2**31))
    if timeframe == "1Hour":
        periods = int((end - start).total_seconds() / 3600)
    else:
        periods = int((end - start).days)
    if periods <= 0:
        periods = 252

    dates = pd.date_range(start=start, periods=periods, freq="h" if timeframe == "1Hour" else "B")
    base_price = 50 + rng.random() * 200
    returns = rng.normal(0.0001, 0.015, size=len(dates))
    prices = base_price * np.exp(np.cumsum(returns))
    high = prices * (1 + rng.uniform(0.001, 0.02, len(dates)))
    low = prices * (1 - rng.uniform(0.001, 0.02, len(dates)))
    volume = rng.integers(100_000, 5_000_000, size=len(dates)).astype(float)

    df = pd.DataFrame(
        {"open": prices * (1 + rng.normal(0, 0.003, len(dates))),
         "high": high,
         "low": low,
         "close": prices,
         "volume": volume},
        index=dates,
    )
    df.index.name = "timestamp"
    return df


async def fetch_ohlcv(
    ticker: str,
    start: Optional[dt.datetime] = None,
    end: Optional[dt.datetime] = None,
    timeframe: str = "1Hour",
) -> pd.DataFrame:
    """Fetch OHLCV bars.  Uses Alpaca when credentials are configured, otherwise synthetic."""
    now = dt.datetime.now(dt.timezone.utc)
    if end is None:
        end = now
    if start is None:
        start = end - dt.timedelta(days=settings.backtest_years * 365)

    cache_key = f"{ticker}_{timeframe}_{start.date()}_{end.date()}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    df: Optional[pd.DataFrame] = None

    if settings.alpaca_api_key and settings.alpaca_api_secret:
        try:
            df = await _fetch_from_alpaca(ticker, start, end, timeframe)
        except Exception:
            df = None

    if df is None or df.empty:
        df = _generate_synthetic(ticker, start, end, timeframe)

    _CACHE[cache_key] = df
    return df


async def _fetch_from_alpaca(
    ticker: str,
    start: dt.datetime,
    end: dt.datetime,
    timeframe: str,
) -> pd.DataFrame:
    """Fetch from Alpaca Markets data API."""
    import httpx

    tf_map = {"1Hour": "1Hour", "1Day": "1Day"}
    tf = tf_map.get(timeframe, "1Hour")
    url = f"{settings.alpaca_data_url}/v2/stocks/{ticker}/bars"
    params = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeframe": tf,
        "limit": 10000,
    }
    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
    }

    rows = []
    async with httpx.AsyncClient(timeout=30) as client:
        next_token: Optional[str] = None
        while True:
            if next_token:
                params["page_token"] = next_token
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            bars = data.get("bars", [])
            if not bars:
                break
            for b in bars:
                rows.append({
                    "timestamp": pd.Timestamp(b["t"]),
                    "open": b["o"],
                    "high": b["h"],
                    "low": b["l"],
                    "close": b["c"],
                    "volume": b["v"],
                })
            next_token = data.get("next_page_token")
            if not next_token:
                break

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("timestamp").sort_index()
    return df


async def fetch_vix(
    start: Optional[dt.datetime] = None,
    end: Optional[dt.datetime] = None,
) -> pd.DataFrame:
    """Fetch VIX data. Falls back to synthetic VIX-like series."""
    now = dt.datetime.now(dt.timezone.utc)
    if end is None:
        end = now
    if start is None:
        start = end - dt.timedelta(days=90)

    cache_key = f"VIX_{start.date()}_{end.date()}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # Try ^VIX or VIXY as a proxy
    try:
        df = await fetch_ohlcv("VIXY", start, end, "1Hour")
        if not df.empty:
            _CACHE[cache_key] = df
            return df
    except Exception:
        pass

    # Synthetic VIX
    rng = np.random.default_rng(42)
    periods = int((end - start).total_seconds() / 3600)
    if periods <= 0:
        periods = 500
    dates = pd.date_range(start=start, periods=periods, freq="h")
    base = 18.0
    returns = rng.normal(0, 0.04, len(dates))
    vix_vals = base * np.exp(np.cumsum(returns))
    vix_vals = np.clip(vix_vals, 9, 80)
    df = pd.DataFrame(
        {"open": vix_vals, "high": vix_vals * 1.02,
         "low": vix_vals * 0.98, "close": vix_vals,
         "volume": np.zeros(len(dates))},
        index=dates,
    )
    df.index.name = "timestamp"
    _CACHE[cache_key] = df
    return df
