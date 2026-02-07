"""ThesisGenerator — aggregates technical signals, VIX status, backtest stats, and risk into a Thesis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.config import settings
from backend.data_provider import fetch_ohlcv, fetch_vix
from backend.engine.macd_zscore import MACDZScoreAnalyzer
from backend.engine.reversal_analyzer import ReversalAnalyzer
from backend.engine.vix_filter import VIXBetaFilter
from backend.api.models import (
    BacktestStats,
    MACDInfo,
    RiskInfo,
    RSIInfo,
    ThesisResponse,
    VIXInfo,
)


class ThesisGenerator:
    """Produce a full structured thesis for a given ticker."""

    def __init__(self) -> None:
        self.reversal = ReversalAnalyzer()
        self.macd = MACDZScoreAnalyzer()
        self.vix_filter = VIXBetaFilter()

    async def generate(self, ticker: str) -> ThesisResponse:
        # Fetch data
        df = await fetch_ohlcv(ticker)
        vix_df = await fetch_vix()

        # 1) RSI signals
        rsi_aug = self.reversal.compute_indicators(df)
        last = rsi_aug.iloc[-1]
        phase = 3 if last.get("phase3") else (2 if last.get("phase2") else (1 if last.get("phase1") else 0))
        active = bool(last.get("phase3", False))
        rsi_info = RSIInfo(
            rsi_5=round(float(last["rsi_5"]), 2) if not pd.isna(last["rsi_5"]) else 50.0,
            rsi_9=round(float(last["rsi_9"]), 2) if not pd.isna(last["rsi_9"]) else 50.0,
            rsi_14=round(float(last["rsi_14"]), 2) if not pd.isna(last["rsi_14"]) else 50.0,
            phase=phase,
            active=active,
        )

        # 2) MACD Z-Score
        macd_data = self.macd.latest_zscore(df)
        macd_info = MACDInfo(
            zscore=macd_data["zscore"],
            regime=macd_data["regime"],
            macd_hist=macd_data["macd_hist"],
        )

        # 3) VIX status
        vix_status = self.vix_filter.analyze(vix_df)
        vix_info = VIXInfo(
            current_vix=vix_status.current_vix,
            vix_rsi2=vix_status.vix_rsi2,
            extreme_fear=vix_status.extreme_fear,
            lower_high_confirmed=vix_status.lower_high_confirmed,
            regime=vix_status.regime,
            recommendation=vix_status.recommendation,
        )

        # 4) Backtest stats
        bt = self.reversal.backtest_reversal(df, vix_df)
        backtest = BacktestStats(**bt)

        # 5) Risk
        close = df["close"]
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else float(close.mean())
        current_price = float(close.iloc[-1])
        price_vs_sma = (current_price - sma_200) / sma_200 * 100

        # Max drawdown from phase-3 entries in backtest
        max_dd = self._compute_max_drawdown(df)

        if price_vs_sma < -2:
            play_type = "mean_reversion"
        elif price_vs_sma > 2:
            play_type = "trend_following"
        else:
            play_type = "range_bound"

        risk_info = RiskInfo(
            sma_200=round(sma_200, 2),
            price_vs_sma_200_pct=round(price_vs_sma, 2),
            play_type=play_type,
            max_drawdown_pct=round(max_dd, 2),
            suggested_stop_loss_pct=round(max_dd * 1.2, 2),  # 20% buffer beyond historical max DD
        )

        # Composite probability score
        prob_score = self._compute_probability_score(rsi_info, macd_info, vix_info, backtest)

        # Signal direction
        if macd_data["regime"] == "statistical_washout" or active:
            direction = "buy"
        elif macd_data["regime"] == "exhaustion":
            direction = "sell"
        else:
            direction = "neutral"

        # Natural-language thesis
        why_now = self._build_why_now(ticker, rsi_info, macd_info, backtest)
        macro_tailwind = self._build_macro(vix_info)
        risk_summary = self._build_risk(risk_info)

        return ThesisResponse(
            ticker=ticker,
            price=current_price,
            signal_direction=direction,
            probability_score=prob_score,
            why_now=why_now,
            macro_tailwind=macro_tailwind,
            risk_summary=risk_summary,
            rsi=rsi_info,
            macd=macd_info,
            vix=vix_info,
            backtest=backtest,
            risk=risk_info,
        )

    def _compute_max_drawdown(self, df: pd.DataFrame) -> float:
        close = df["close"]
        roll_max = close.cummax()
        drawdown = (close - roll_max) / roll_max * 100
        return abs(float(drawdown.min()))

    def _compute_probability_score(
        self,
        rsi: RSIInfo,
        macd: MACDInfo,
        vix: VIXInfo,
        bt: BacktestStats,
    ) -> float:
        """Weighted composite score 0-100."""
        score = 0.0

        # RSI alignment (0-30)
        if rsi.active:
            score += 30
        elif rsi.phase >= 2:
            score += 20
        elif rsi.phase >= 1:
            score += 10

        # MACD Z-score (0-30)
        z = abs(macd.zscore)
        if z > 2.5:
            score += 30
        elif z > 2.0:
            score += 25
        elif z > 1.5:
            score += 15
        elif z > 1.0:
            score += 5

        # VIX context (0-20)
        if vix.regime == "extreme_fear_peaking":
            score += 20
        elif vix.regime == "extreme_fear":
            score += 10
        elif vix.regime == "normal":
            score += 15

        # Backtest confidence (0-20)
        if bt.sample_count >= 10:
            score += min(bt.reversal_pct / 5, 20)

        return round(min(score, 100), 1)

    def _build_why_now(self, ticker: str, rsi: RSIInfo, macd: MACDInfo, bt: BacktestStats) -> str:
        parts = []
        if rsi.active:
            parts.append(f"RSI Alignment detected (Phase 3 active).")
        elif rsi.phase >= 2:
            parts.append(f"RSI Turn detected (Phase 2) — RSI(5) crossed RSI(9).")
        if macd.regime == "statistical_washout":
            parts.append(f"MACD-Hist Z-Score at {macd.zscore:.1f} — statistical washout territory.")

        if bt.sample_count > 0:
            parts.append(
                f"Historically, this setup has a {bt.reversal_pct:.0f}% reversal rate "
                f"for {ticker} over the last {settings.backtest_years} years "
                f"({bt.sample_count} occurrences, avg gain {bt.avg_gain_pct:.1f}%)."
            )
        if not parts:
            parts.append("No strong directional signal detected at current levels.")
        return " ".join(parts)

    def _build_macro(self, vix: VIXInfo) -> str:
        status = f"VIX is currently {vix.current_vix}"
        if vix.lower_high_confirmed:
            status += " (dropping — lower high confirmed)"
        status += f". Regime: {vix.regime}. {vix.recommendation}"
        return status

    def _build_risk(self, risk: RiskInfo) -> str:
        return (
            f"Current price is {abs(risk.price_vs_sma_200_pct):.1f}% "
            f"{'below' if risk.price_vs_sma_200_pct < 0 else 'above'} SMA(200). "
            f"This is a '{risk.play_type.replace('_', ' ').title()}' play. "
            f"Historical max drawdown: {risk.max_drawdown_pct:.1f}%. "
            f"Suggested stop-loss: {risk.suggested_stop_loss_pct:.1f}%."
        )
