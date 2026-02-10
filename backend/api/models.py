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


# ── v2.0 models ──


class ShockEventModel(BaseModel):
    ticker: str
    timestamp: str
    zscore: float
    velocity: float
    acceleration: float
    direction: str  # crash_shock | melt_up_shock
    severity: str  # moderate | severe | extreme


class BacktestDetailResponse(BaseModel):
    ticker: str
    signal_type: str
    reversal_pct: float
    avg_gain_pct: float
    sample_count: int
    timeframe: str


class ThresholdCheckResponse(BaseModel):
    exceeds_90pct: bool
    reversal_rate: float
    sample_count: int
    current_zscore: float


class NewsArticleModel(BaseModel):
    headline: str
    source: str
    url: str
    published_at: str
    sentiment: str
    summary: str


class EventModel(BaseModel):
    ticker: str
    event_type: str
    event_date: str
    details: dict | None = None
    source: str | None = None


class InsiderTradeModel(BaseModel):
    ticker: str
    name: str
    transaction_type: str
    value: float
    wealth_impact_score: float
    date: str


class PoliticianTradeModel(BaseModel):
    politician: str
    ticker: str
    transaction_type: str
    amount: str
    date: str
    source: str


class MultiTimeframeRequest(BaseModel):
    ticker: str
    timeframe: str = "1Hour"  # 1Hour | 1Day | 1Week | 1Month


# ── v2.1 models ──


class SignalRowV2(BaseModel):
    """Extended signal row with RSI 5/9/14, sector, earnings date, reversal %."""
    ticker: str
    price: float
    signal_direction: str
    signal_arrow: str
    probability_score: float
    rsi_5: float
    rsi_9: float
    rsi_14: float
    macd_zscore: float
    vix_regime: str
    reversal_pct: float
    sector: str = ""
    next_earnings_date: str | None = None
    is_extreme_move: bool = False


class SignalGridResponseV2(BaseModel):
    signals: list[SignalRowV2]
    vix: VIXInfo
    updated_at: str
    refresh_intervals: dict[str, int] = {}


class MACDExtremeResponse(BaseModel):
    ticker: str
    current_hist: float
    current_hist_zscore: float
    one_day: dict
    three_day: dict
    is_extreme_now: bool
    events: list[dict]


class EarningsSignalResponse(BaseModel):
    ticker: str
    has_upcoming_earnings: bool
    earnings_date: str | None = None
    days_until_earnings: int | None = None
    signals: list[dict]
    signal_strength: int
    recommendation: str = ""
    pre_earnings_momentum: dict | None = None


class UpcomingEarningsItem(BaseModel):
    ticker: str
    earnings_date: str
    eps_estimated: float | None = None
    revenue_estimated: float | None = None
    signals: list[dict]
    signal_strength: int
    recommendation: str = ""


class PortfolioHolding(BaseModel):
    ticker: str
    weight: float  # percentage 0-100
    value: float | None = None  # dollar value


class PortfolioSaveRequest(BaseModel):
    holdings: dict[str, float]  # ticker -> weight or dollar value
    total_value: float | None = None
    mode: str = "pct"  # 'pct' or 'dollar'


class PortfolioAddRequest(BaseModel):
    ticker: str
    amount: float  # weight or dollar value
    mode: str = "pct"  # 'pct' or 'dollar'


class PortfolioResponse(BaseModel):
    tickers: list[str]
    weights: dict[str, float]
    tangency_weights: dict[str, float] | None = None
    sharpe: float
    total_value: float | None = None


class BenchmarkComparison(BaseModel):
    portfolio: dict
    spy: dict | None = None
    qqq: dict | None = None


class NotificationModel(BaseModel):
    id: str
    ticker: str
    type: str
    title: str
    message: str
    severity: str
    created_at: str
    read: bool
    data: dict = {}


class RefreshConfigResponse(BaseModel):
    prices: int
    signals: int
    thesis: int
    news: int
    events: int
    insider_trades: int
    politician_trades: int
    portfolio: int
    company_profile: int


class ExportFormat(BaseModel):
    format: str = "csv"  # csv only for now
