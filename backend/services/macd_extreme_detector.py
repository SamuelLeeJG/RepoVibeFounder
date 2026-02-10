"""MACD Extreme Move Detector — finds 1-day and 3-day MACD histogram drops/spikes beyond 2SD.

Computes the distribution of daily and 3-day MACD histogram changes, then flags
moves that exceed 2 standard deviations — indicating abnormal momentum shifts
worth investigating for entry/exit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.engine.macd_zscore import MACDZScoreAnalyzer


@dataclass
class ExtremeMoveEvent:
    ticker: str
    timestamp: pd.Timestamp
    period: str  # "1d" or "3d"
    direction: str  # "drop" or "spike"
    change: float  # raw MACD histogram change
    mean: float  # rolling mean of changes
    std: float  # rolling std of changes
    z_score: float  # how many SDs from mean
    close_price: float
    macd_hist: float
    hist_zscore: float


class MACDExtremeDetector:
    """Detect 1-day and 3-day MACD histogram changes that exceed 2 standard deviations.

    This identifies momentum shifts that are statistically unusual — these are
    the "this is not normal" moments where capital deployment may be warranted.
    """

    def __init__(
        self,
        lookback: int = 252,  # ~1 year of daily data for distribution
        threshold_sd: float = 2.0,
    ):
        self.lookback = lookback
        self.threshold_sd = threshold_sd
        self.macd_analyzer = MACDZScoreAnalyzer()

    def detect(self, df: pd.DataFrame, ticker: str = "") -> dict:
        """Analyze 1-day and 3-day MACD histogram changes.

        Returns:
            {
                "ticker": str,
                "current_hist": float,
                "one_day": { stats + events },
                "three_day": { stats + events },
                "is_extreme_now": bool,
                "events": list[dict],
            }
        """
        aug = self.macd_analyzer.compute_indicators(df)
        hist = aug["macd_hist"].dropna()

        if len(hist) < self.lookback + 10:
            return self._empty_result(ticker)

        # Compute 1-day and 3-day changes
        changes_1d = hist.diff(1)
        changes_3d = hist.diff(3)

        # Rolling statistics over lookback window
        mean_1d = changes_1d.rolling(self.lookback).mean()
        std_1d = changes_1d.rolling(self.lookback).std()
        zscore_1d = (changes_1d - mean_1d) / std_1d.replace(0, np.nan)

        mean_3d = changes_3d.rolling(self.lookback).mean()
        std_3d = changes_3d.rolling(self.lookback).std()
        zscore_3d = (changes_3d - mean_3d) / std_3d.replace(0, np.nan)

        # Current values
        current_idx = hist.index[-1]
        current_hist = float(hist.iloc[-1])
        current_zscore = float(aug["hist_zscore"].iloc[-1]) if not pd.isna(aug["hist_zscore"].iloc[-1]) else 0.0

        # 1-day current
        c1d = float(changes_1d.iloc[-1]) if not pd.isna(changes_1d.iloc[-1]) else 0.0
        m1d = float(mean_1d.iloc[-1]) if not pd.isna(mean_1d.iloc[-1]) else 0.0
        s1d = float(std_1d.iloc[-1]) if not pd.isna(std_1d.iloc[-1]) else 1.0
        z1d = float(zscore_1d.iloc[-1]) if not pd.isna(zscore_1d.iloc[-1]) else 0.0

        # 3-day current
        c3d = float(changes_3d.iloc[-1]) if not pd.isna(changes_3d.iloc[-1]) else 0.0
        m3d = float(mean_3d.iloc[-1]) if not pd.isna(mean_3d.iloc[-1]) else 0.0
        s3d = float(std_3d.iloc[-1]) if not pd.isna(std_3d.iloc[-1]) else 1.0
        z3d = float(zscore_3d.iloc[-1]) if not pd.isna(zscore_3d.iloc[-1]) else 0.0

        is_extreme_1d = abs(z1d) >= self.threshold_sd
        is_extreme_3d = abs(z3d) >= self.threshold_sd

        # Collect historical extreme events (last 50 bars)
        events = []
        scan_range = min(50, len(hist) - self.lookback)
        for i in range(max(0, len(hist) - scan_range), len(hist)):
            idx = hist.index[i]
            # 1-day extremes
            if not pd.isna(zscore_1d.iloc[i]) and abs(float(zscore_1d.iloc[i])) >= self.threshold_sd:
                events.append(self._make_event(
                    ticker, idx, "1d", changes_1d, mean_1d, std_1d, zscore_1d, aug, i
                ))
            # 3-day extremes
            if not pd.isna(zscore_3d.iloc[i]) and abs(float(zscore_3d.iloc[i])) >= self.threshold_sd:
                events.append(self._make_event(
                    ticker, idx, "3d", changes_3d, mean_3d, std_3d, zscore_3d, aug, i
                ))

        return {
            "ticker": ticker,
            "current_hist": round(current_hist, 4),
            "current_hist_zscore": round(current_zscore, 3),
            "one_day": {
                "change": round(c1d, 4),
                "mean": round(m1d, 4),
                "std": round(s1d, 4),
                "z_score": round(z1d, 3),
                "is_extreme": is_extreme_1d,
                "direction": "drop" if c1d < 0 else "spike",
                "threshold_lower": round(m1d - self.threshold_sd * s1d, 4),
                "threshold_upper": round(m1d + self.threshold_sd * s1d, 4),
            },
            "three_day": {
                "change": round(c3d, 4),
                "mean": round(m3d, 4),
                "std": round(s3d, 4),
                "z_score": round(z3d, 3),
                "is_extreme": is_extreme_3d,
                "direction": "drop" if c3d < 0 else "spike",
                "threshold_lower": round(m3d - self.threshold_sd * s3d, 4),
                "threshold_upper": round(m3d + self.threshold_sd * s3d, 4),
            },
            "is_extreme_now": is_extreme_1d or is_extreme_3d,
            "events": [self._event_to_dict(e) for e in events[-20:]],
        }

    def _make_event(
        self, ticker, idx, period, changes, mean, std, zscore, aug, i
    ) -> ExtremeMoveEvent:
        z = float(zscore.iloc[i])
        c = float(changes.iloc[i])
        return ExtremeMoveEvent(
            ticker=ticker,
            timestamp=idx,
            period=period,
            direction="drop" if c < 0 else "spike",
            change=round(c, 4),
            mean=round(float(mean.iloc[i]), 4),
            std=round(float(std.iloc[i]), 4),
            z_score=round(z, 3),
            close_price=round(float(aug.loc[idx, "close"]), 2),
            macd_hist=round(float(aug.loc[idx, "macd_hist"]), 4),
            hist_zscore=round(float(aug.loc[idx, "hist_zscore"]), 3) if not pd.isna(aug.loc[idx, "hist_zscore"]) else 0.0,
        )

    def _event_to_dict(self, e: ExtremeMoveEvent) -> dict:
        return {
            "ticker": e.ticker,
            "timestamp": str(e.timestamp),
            "period": e.period,
            "direction": e.direction,
            "change": e.change,
            "z_score": e.z_score,
            "close_price": e.close_price,
            "macd_hist": e.macd_hist,
        }

    def _empty_result(self, ticker: str) -> dict:
        empty_stats = {
            "change": 0.0, "mean": 0.0, "std": 0.0, "z_score": 0.0,
            "is_extreme": False, "direction": "neutral",
            "threshold_lower": 0.0, "threshold_upper": 0.0,
        }
        return {
            "ticker": ticker,
            "current_hist": 0.0,
            "current_hist_zscore": 0.0,
            "one_day": empty_stats,
            "three_day": empty_stats,
            "is_extreme_now": False,
            "events": [],
        }
