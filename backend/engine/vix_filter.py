"""VIX Beta Filter — Macro Context Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from backend.config import settings


@dataclass
class VIXStatus:
    current_vix: float
    vix_rsi2: float
    extreme_fear: bool
    lower_high_confirmed: bool
    regime: str  # "extreme_fear_peaking", "extreme_fear", "elevated", "normal", "complacent"
    recommendation: str


class VIXBetaFilter:
    """Monitor the VIX for 'Extreme Fear' and peak confirmation."""

    def __init__(
        self,
        rsi_period: int = settings.vix_rsi_period,
        fear_threshold: float = settings.vix_fear_threshold,
    ):
        self.rsi_period = rsi_period
        self.fear_threshold = fear_threshold

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _detect_lower_high(self, vix_close: pd.Series, lookback_hours: int = 48) -> bool:
        """Check if VIX made a lower high in the last *lookback_hours* bars.

        A 'lower high' means the most recent local peak is below the prior local peak,
        suggesting the volatility spike has peaked.
        """
        tail = vix_close.iloc[-lookback_hours:] if len(vix_close) >= lookback_hours else vix_close
        if len(tail) < 10:
            return False

        # Find local peaks (simple: value higher than both neighbours)
        peaks = []
        values = tail.values
        for i in range(1, len(values) - 1):
            if values[i] > values[i - 1] and values[i] > values[i + 1]:
                peaks.append(values[i])

        if len(peaks) >= 2:
            return peaks[-1] < peaks[-2]
        return False

    def analyze(self, vix_df: pd.DataFrame) -> VIXStatus:
        """Compute the current VIX regime."""
        close = vix_df["close"]
        rsi2 = self._rsi(close, self.rsi_period)
        current_vix = float(close.iloc[-1])
        current_rsi2 = float(rsi2.iloc[-1]) if not pd.isna(rsi2.iloc[-1]) else 50.0

        extreme_fear = current_rsi2 > self.fear_threshold
        lower_high = self._detect_lower_high(close)

        # Determine regime
        if extreme_fear and lower_high:
            regime = "extreme_fear_peaking"
            recommendation = "VIX spike peaking — Index buys (SPY/IWM) favoured."
        elif extreme_fear:
            regime = "extreme_fear"
            recommendation = "VIX Extreme Fear active — wait for lower-high confirmation before Index buys."
        elif current_vix > 25:
            regime = "elevated"
            recommendation = "VIX elevated — selective stock-specific entries only."
        elif current_vix > 15:
            regime = "normal"
            recommendation = "VIX normal — standard signal processing."
        else:
            regime = "complacent"
            recommendation = "VIX low — be cautious of complacency; tighten stops."

        return VIXStatus(
            current_vix=round(current_vix, 2),
            vix_rsi2=round(current_rsi2, 2),
            extreme_fear=extreme_fear,
            lower_high_confirmed=lower_high,
            regime=regime,
            recommendation=recommendation,
        )
