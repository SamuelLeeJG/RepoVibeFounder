"""Sam Reversal Multi-Timeframe RSI Analyzer (Alpha Signal Engine)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from backend.config import settings


@dataclass
class ReversalSignal:
    ticker: str
    timestamp: pd.Timestamp
    phase: int  # 1, 2, or 3
    active: bool
    rsi_5: float
    rsi_9: float
    rsi_14: float
    price: float
    bb_lower: float
    reversal_probability: Optional[float] = None
    avg_gain_pct: Optional[float] = None
    sample_count: int = 0


class ReversalAnalyzer:
    """Detects 'Spring-Loading' momentum via Triple RSI Alignment + Bollinger Band confirmation."""

    def __init__(
        self,
        rsi_short: int = settings.rsi_short,
        rsi_mid: int = settings.rsi_mid,
        rsi_long: int = settings.rsi_long,
        bb_period: int = settings.bollinger_period,
        bb_std: float = settings.bollinger_std,
        reversal_window: int = settings.reversal_window_days,
    ):
        self.rsi_short = rsi_short
        self.rsi_mid = rsi_mid
        self.rsi_long = rsi_long
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.reversal_window = reversal_window

    # ---- RSI calculation ----
    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    # ---- Bollinger Band ----
    def _bollinger_lower(self, close: pd.Series) -> pd.Series:
        sma = close.rolling(self.bb_period).mean()
        std = close.rolling(self.bb_period).std()
        return sma - self.bb_std * std

    # ---- Phase detection ----
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Augment a DataFrame with RSI columns, Bollinger Band, and phase flags."""
        close = df["close"]
        out = df.copy()
        out["rsi_5"] = self._rsi(close, self.rsi_short)
        out["rsi_9"] = self._rsi(close, self.rsi_mid)
        out["rsi_14"] = self._rsi(close, self.rsi_long)
        out["bb_lower"] = self._bollinger_lower(close)

        # Phase 1: The Squeeze
        out["phase1"] = (
            (out["rsi_5"] < 30)
            & (out["rsi_9"] < 35)
            & (out["rsi_14"] < 40)
        )

        # Phase 2: The Turn — RSI(5) crosses above RSI(9), both below RSI(14)
        cross_above = (out["rsi_5"] > out["rsi_9"]) & (out["rsi_5"].shift(1) <= out["rsi_9"].shift(1))
        both_below_14 = (out["rsi_5"] < out["rsi_14"]) & (out["rsi_9"] < out["rsi_14"])
        out["phase2"] = cross_above & both_below_14

        # Phase 3: Trigger — Phase 2 + price below lower BB
        out["phase3"] = out["phase2"] & (close < out["bb_lower"])

        return out

    def scan(self, df: pd.DataFrame, ticker: str = "") -> list[ReversalSignal]:
        """Return active signals from the DataFrame."""
        aug = self.compute_indicators(df)
        signals: list[ReversalSignal] = []

        for idx in aug.index[aug["phase3"]]:
            row = aug.loc[idx]
            signals.append(
                ReversalSignal(
                    ticker=ticker,
                    timestamp=idx,
                    phase=3,
                    active=True,
                    rsi_5=round(float(row["rsi_5"]), 2),
                    rsi_9=round(float(row["rsi_9"]), 2),
                    rsi_14=round(float(row["rsi_14"]), 2),
                    price=round(float(row["close"]), 2),
                    bb_lower=round(float(row["bb_lower"]), 2),
                )
            )
        return signals

    # ---- Backtest-on-the-fly ----
    def backtest_reversal(
        self,
        df: pd.DataFrame,
        vix_df: Optional[pd.DataFrame] = None,
        vix_threshold: float = 20.0,
    ) -> dict:
        """For every Phase-3 signal in *df*, check if price reversed within *reversal_window* days.

        Returns aggregate stats: reversal_pct, avg_gain_pct, sample_count.
        """
        aug = self.compute_indicators(df)
        trigger_indices = aug.index[aug["phase3"]]

        wins = 0
        gains: list[float] = []
        total = 0

        for t_idx in trigger_indices:
            pos = aug.index.get_loc(t_idx)
            # Use the next `reversal_window` bars (approximate)
            forward = aug.iloc[pos + 1: pos + 1 + self.reversal_window * 8]  # 8 bars ~ 1 day for hourly
            if forward.empty:
                continue

            entry_price = aug.loc[t_idx, "close"]
            max_price = forward["close"].max()
            pct_gain = (max_price - entry_price) / entry_price * 100

            # Optional VIX condition filter
            if vix_df is not None:
                nearest_vix = vix_df.index.asof(t_idx)
                if nearest_vix is not pd.NaT:
                    vix_val = float(vix_df.loc[nearest_vix, "close"])
                    if vix_val < vix_threshold:
                        continue  # skip low-VIX signals when filtering

            total += 1
            if pct_gain > 0:
                wins += 1
            gains.append(pct_gain)

        if total == 0:
            return {"reversal_pct": 0.0, "avg_gain_pct": 0.0, "sample_count": 0}

        return {
            "reversal_pct": round(wins / total * 100, 1),
            "avg_gain_pct": round(float(np.mean(gains)), 2),
            "sample_count": total,
        }
