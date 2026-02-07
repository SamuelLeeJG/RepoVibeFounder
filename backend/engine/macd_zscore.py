"""MACD-Histogram Z-Score Analyzer (The Bottom / Top Finder)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.config import settings


@dataclass
class MACDZSignal:
    ticker: str
    timestamp: pd.Timestamp
    direction: str  # "buy" or "sell"
    zscore: float
    macd_hist: float
    hist_mean: float
    hist_std: float
    price: float


class MACDZScoreAnalyzer:
    """Standardise the MACD-Histogram over a rolling window and flag extreme Z-scores."""

    def __init__(
        self,
        fast: int = settings.macd_fast,
        slow: int = settings.macd_slow,
        signal: int = settings.macd_signal,
        zscore_window: int = settings.macd_zscore_window,
        threshold: float = settings.macd_zscore_threshold,
    ):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.zscore_window = zscore_window
        self.threshold = threshold

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD line, signal line, histogram, rolling stats, and Z-score."""
        close = df["close"]
        out = df.copy()

        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        out["macd_line"] = ema_fast - ema_slow
        out["macd_signal"] = out["macd_line"].ewm(span=self.signal, adjust=False).mean()
        out["macd_hist"] = out["macd_line"] - out["macd_signal"]

        out["hist_mean"] = out["macd_hist"].rolling(self.zscore_window).mean()
        out["hist_std"] = out["macd_hist"].rolling(self.zscore_window).std()
        out["hist_zscore"] = (out["macd_hist"] - out["hist_mean"]) / out["hist_std"].replace(0, np.nan)

        out["buy_signal"] = out["hist_zscore"] < -self.threshold
        out["sell_signal"] = out["hist_zscore"] > self.threshold

        return out

    def scan(self, df: pd.DataFrame, ticker: str = "") -> list[MACDZSignal]:
        """Return buy/sell signals from the most recent data."""
        aug = self.compute_indicators(df)
        signals: list[MACDZSignal] = []

        for idx in aug.index:
            row = aug.loc[idx]
            if pd.isna(row.get("hist_zscore")):
                continue

            direction = None
            if row["buy_signal"]:
                direction = "buy"
            elif row["sell_signal"]:
                direction = "sell"

            if direction:
                signals.append(
                    MACDZSignal(
                        ticker=ticker,
                        timestamp=idx,
                        direction=direction,
                        zscore=round(float(row["hist_zscore"]), 3),
                        macd_hist=round(float(row["macd_hist"]), 4),
                        hist_mean=round(float(row["hist_mean"]), 4),
                        hist_std=round(float(row["hist_std"]), 4),
                        price=round(float(row["close"]), 2),
                    )
                )
        return signals

    def latest_zscore(self, df: pd.DataFrame) -> dict:
        """Return the latest MACD-Hist Z-score with interpretation."""
        aug = self.compute_indicators(df)
        last = aug.dropna(subset=["hist_zscore"]).iloc[-1]
        z = float(last["hist_zscore"])
        if z < -self.threshold:
            regime = "statistical_washout"
        elif z > self.threshold:
            regime = "exhaustion"
        else:
            regime = "neutral"
        return {
            "zscore": round(z, 3),
            "regime": regime,
            "macd_hist": round(float(last["macd_hist"]), 4),
            "price": round(float(last["close"]), 2),
        }
