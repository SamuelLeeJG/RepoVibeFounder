"""MACD Velocity Shock Detector — flags rapid Z-score acceleration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.engine.macd_zscore import MACDZScoreAnalyzer


@dataclass
class ShockEvent:
    ticker: str
    timestamp: pd.Timestamp
    zscore: float
    velocity: float  # d(zscore)/dt
    acceleration: float  # d2(zscore)/dt2
    direction: str  # "crash_shock" or "melt_up_shock"
    severity: str  # "moderate" | "severe" | "extreme"


class MACDVelocityShockDetector:
    """Detect rapid changes in MACD-Histogram Z-Score (velocity shocks).

    A velocity shock is when the rate of change of the Z-score exceeds
    a threshold, indicating a rapid momentum shift.
    """

    def __init__(
        self,
        velocity_threshold: float = 0.5,  # Z-score units per bar
        acceleration_threshold: float = 0.3,
        lookback_bars: int = 5,
    ):
        self.velocity_threshold = velocity_threshold
        self.acceleration_threshold = acceleration_threshold
        self.lookback_bars = lookback_bars
        self.macd_analyzer = MACDZScoreAnalyzer()

    def detect(self, df: pd.DataFrame, ticker: str = "") -> list[ShockEvent]:
        """Scan for velocity shocks in the data."""
        aug = self.macd_analyzer.compute_indicators(df)
        zscores = aug["hist_zscore"].dropna()

        if len(zscores) < self.lookback_bars + 2:
            return []

        # Compute velocity (first derivative) and acceleration (second derivative)
        velocity = zscores.diff()
        acceleration = velocity.diff()

        shocks: list[ShockEvent] = []
        for i in range(self.lookback_bars, len(zscores)):
            idx = zscores.index[i]
            v = float(velocity.iloc[i])
            a = float(acceleration.iloc[i]) if not pd.isna(acceleration.iloc[i]) else 0.0
            z = float(zscores.iloc[i])

            if abs(v) < self.velocity_threshold:
                continue

            # Determine direction
            if v < -self.velocity_threshold:
                direction = "crash_shock"
            elif v > self.velocity_threshold:
                direction = "melt_up_shock"
            else:
                continue

            # Determine severity
            abs_v = abs(v)
            if abs_v > self.velocity_threshold * 3:
                severity = "extreme"
            elif abs_v > self.velocity_threshold * 2:
                severity = "severe"
            else:
                severity = "moderate"

            shocks.append(
                ShockEvent(
                    ticker=ticker,
                    timestamp=idx,
                    zscore=round(z, 3),
                    velocity=round(v, 4),
                    acceleration=round(a, 4),
                    direction=direction,
                    severity=severity,
                )
            )

        return shocks

    def latest_shock(self, df: pd.DataFrame, ticker: str = "") -> dict | None:
        """Return the most recent shock event if one occurred in the last N bars."""
        shocks = self.detect(df, ticker)
        if not shocks:
            return None

        last = shocks[-1]
        return {
            "ticker": last.ticker,
            "timestamp": str(last.timestamp),
            "zscore": last.zscore,
            "velocity": last.velocity,
            "acceleration": last.acceleration,
            "direction": last.direction,
            "severity": last.severity,
        }

    def check_90pct_threshold(self, df: pd.DataFrame) -> dict:
        """Check if the MACD-Z reversal rate exceeds 90% threshold.

        Scans historical data and returns whether signals at current Z-level
        have historically reversed >90% of the time.
        """
        aug = self.macd_analyzer.compute_indicators(df)
        zscores = aug["hist_zscore"].dropna()
        if len(zscores) < 50:
            return {"exceeds_90pct": False, "reversal_rate": 0.0, "sample_count": 0}

        current_z = float(zscores.iloc[-1])
        threshold = abs(current_z)

        # Find all historical instances where |Z| >= current level
        extreme_indices = zscores.index[zscores.abs() >= threshold]
        reversals = 0
        total = 0

        for t_idx in extreme_indices:
            pos = zscores.index.get_loc(t_idx)
            forward = aug.iloc[pos + 1: pos + 41]  # 5-day window (8 bars/day)
            if len(forward) < 5:
                continue

            entry_price = float(aug.loc[t_idx, "close"])
            z_at_entry = float(zscores.loc[t_idx])

            if z_at_entry < 0:  # Washout → expect price up
                max_future = float(forward["close"].max())
                if max_future > entry_price:
                    reversals += 1
            else:  # Exhaustion → expect price down
                min_future = float(forward["close"].min())
                if min_future < entry_price:
                    reversals += 1
            total += 1

        rate = (reversals / total * 100) if total > 0 else 0.0
        return {
            "exceeds_90pct": rate >= 90.0,
            "reversal_rate": round(rate, 1),
            "sample_count": total,
            "current_zscore": current_z,
        }
