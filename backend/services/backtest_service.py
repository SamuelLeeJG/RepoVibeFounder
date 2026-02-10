"""Ticker-specific backtesting service — replaces flat 72% reversal rate."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd

from backend.config import settings
from backend.data_provider import fetch_ohlcv, fetch_vix
from backend.engine.macd_zscore import MACDZScoreAnalyzer
from backend.engine.reversal_analyzer import ReversalAnalyzer


async def get_historical_win_rate(
    ticker: str,
    signal_type: str = "rsi_phase3",
    timeframe: str = "1Hour",
    years: int = settings.backtest_years,
) -> dict:
    """Compute ticker-specific reversal win rate by backtesting the last N years of data.

    Returns:
        {
            "ticker": str,
            "signal_type": str,
            "reversal_pct": float,
            "avg_gain_pct": float,
            "sample_count": int,
            "timeframe": str,
        }
    """
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=years * 365)

    df = await fetch_ohlcv(ticker, start=start, end=end, timeframe=timeframe)
    if df.empty or len(df) < 50:
        return _empty_result(ticker, signal_type, timeframe)

    vix_df = await fetch_vix(start=start, end=end)

    if signal_type == "rsi_phase3":
        return _backtest_rsi_phase3(ticker, df, vix_df, timeframe)
    elif signal_type == "macd_washout":
        return _backtest_macd_washout(ticker, df, timeframe)
    elif signal_type == "combined":
        return _backtest_combined(ticker, df, vix_df, timeframe)
    else:
        return _empty_result(ticker, signal_type, timeframe)


def _backtest_rsi_phase3(
    ticker: str, df: pd.DataFrame, vix_df: Optional[pd.DataFrame], timeframe: str
) -> dict:
    """Backtest RSI Phase-3 signals for this specific ticker."""
    analyzer = ReversalAnalyzer()
    aug = analyzer.compute_indicators(df)
    trigger_indices = aug.index[aug["phase3"]]
    reversal_window = settings.reversal_window_days

    wins = 0
    gains: list[float] = []
    total = 0

    for t_idx in trigger_indices:
        pos = aug.index.get_loc(t_idx)
        bars_per_day = 8 if timeframe == "1Hour" else 1
        forward = aug.iloc[pos + 1: pos + 1 + reversal_window * bars_per_day]
        if forward.empty:
            continue

        entry_price = aug.loc[t_idx, "close"]
        max_price = forward["close"].max()
        pct_gain = (max_price - entry_price) / entry_price * 100

        total += 1
        if pct_gain > 0:
            wins += 1
        gains.append(pct_gain)

    if total == 0:
        return _empty_result(ticker, "rsi_phase3", timeframe)

    return {
        "ticker": ticker,
        "signal_type": "rsi_phase3",
        "reversal_pct": round(wins / total * 100, 1),
        "avg_gain_pct": round(float(np.mean(gains)), 2),
        "sample_count": total,
        "timeframe": timeframe,
    }


def _backtest_macd_washout(ticker: str, df: pd.DataFrame, timeframe: str) -> dict:
    """Backtest MACD Z-Score washout signals for this specific ticker."""
    analyzer = MACDZScoreAnalyzer()
    aug = analyzer.compute_indicators(df)

    # Only buy-side washouts (Z < -2)
    trigger_indices = aug.index[aug["buy_signal"]]
    reversal_window = settings.reversal_window_days

    wins = 0
    gains: list[float] = []
    total = 0

    for t_idx in trigger_indices:
        pos = aug.index.get_loc(t_idx)
        bars_per_day = 8 if timeframe == "1Hour" else 1
        forward = aug.iloc[pos + 1: pos + 1 + reversal_window * bars_per_day]
        if forward.empty:
            continue

        entry_price = aug.loc[t_idx, "close"]
        max_price = forward["close"].max()
        pct_gain = (max_price - entry_price) / entry_price * 100

        total += 1
        if pct_gain > 0:
            wins += 1
        gains.append(pct_gain)

    if total == 0:
        return _empty_result(ticker, "macd_washout", timeframe)

    return {
        "ticker": ticker,
        "signal_type": "macd_washout",
        "reversal_pct": round(wins / total * 100, 1),
        "avg_gain_pct": round(float(np.mean(gains)), 2),
        "sample_count": total,
        "timeframe": timeframe,
    }


def _backtest_combined(
    ticker: str, df: pd.DataFrame, vix_df: Optional[pd.DataFrame], timeframe: str
) -> dict:
    """Backtest combined RSI Phase-3 + MACD washout signals."""
    rsi_result = _backtest_rsi_phase3(ticker, df, vix_df, timeframe)
    macd_result = _backtest_macd_washout(ticker, df, timeframe)

    total = rsi_result["sample_count"] + macd_result["sample_count"]
    if total == 0:
        return _empty_result(ticker, "combined", timeframe)

    # Weighted average
    rsi_w = rsi_result["sample_count"] / total if total > 0 else 0
    macd_w = macd_result["sample_count"] / total if total > 0 else 0

    return {
        "ticker": ticker,
        "signal_type": "combined",
        "reversal_pct": round(
            rsi_result["reversal_pct"] * rsi_w + macd_result["reversal_pct"] * macd_w, 1
        ),
        "avg_gain_pct": round(
            rsi_result["avg_gain_pct"] * rsi_w + macd_result["avg_gain_pct"] * macd_w, 2
        ),
        "sample_count": total,
        "timeframe": timeframe,
    }


def _empty_result(ticker: str, signal_type: str, timeframe: str) -> dict:
    return {
        "ticker": ticker,
        "signal_type": signal_type,
        "reversal_pct": 0.0,
        "avg_gain_pct": 0.0,
        "sample_count": 0,
        "timeframe": timeframe,
    }
