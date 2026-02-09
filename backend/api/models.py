"""Pydantic response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class RSIInfo(BaseModel):
    rsi_5: float
    rsi_9: float
    rsi_14: float
    phase: int
    active: bool


class MACDInfo(BaseModel):
    zscore: float
    regime: str
    macd_hist: float


class VIXInfo(BaseModel):
    current_vix: float
    vix_rsi2: float
    extreme_fear: bool
    lower_high_confirmed: bool
    regime: str
    recommendation: str


class BacktestStats(BaseModel):
    reversal_pct: float
    avg_gain_pct: float
    sample_count: int


class RiskInfo(BaseModel):
    sma_200: float
    price_vs_sma_200_pct: float
    play_type: str  # "mean_reversion", "trend_following", etc.
    max_drawdown_pct: float
    suggested_stop_loss_pct: float


class ThesisResponse(BaseModel):
    ticker: str
    price: float
    signal_direction: str  # "buy", "sell", "neutral"
    probability_score: float  # 0-100
    why_now: str
    macro_tailwind: str
    risk_summary: str
    rsi: RSIInfo
    macd: MACDInfo
    vix: VIXInfo
    backtest: BacktestStats
    risk: RiskInfo


class SignalRow(BaseModel):
    ticker: str
    price: float
    signal_direction: str  # "buy", "sell", "neutral"
    signal_arrow: str  # "green_up", "red_down", "none"
    probability_score: float
    rsi_5: float
    macd_zscore: float
    vix_regime: str
    reversal_pct: float  # historical reversal percentage for this signal


class SignalGridResponse(BaseModel):
    signals: list[SignalRow]
    vix: VIXInfo
    updated_at: str


class PortfolioPointModel(BaseModel):
    volatility: float
    expected_return: float
    sharpe: float
    weights: dict[str, float]


class TangencyResponse(BaseModel):
    current: PortfolioPointModel
    tangency: PortfolioPointModel
    frontier: list[PortfolioPointModel]
    rebalance_suggestion: dict[str, float]


class TradeImpactRequest(BaseModel):
    holdings: dict[str, float]  # ticker -> weight (0-1)
    buy_ticker: str
    buy_amount_pct: float


class TradeImpactResponse(BaseModel):
    sharpe_before: float
    sharpe_after: float
    sharpe_delta: float
    recommendation: str
