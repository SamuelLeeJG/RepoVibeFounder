export interface RSIInfo {
  rsi_5: number;
  rsi_9: number;
  rsi_14: number;
  phase: number;
  active: boolean;
}

export interface MACDInfo {
  zscore: number;
  regime: string;
  macd_hist: number;
}

export interface VIXInfo {
  current_vix: number;
  vix_rsi2: number;
  extreme_fear: boolean;
  lower_high_confirmed: boolean;
  regime: string;
  recommendation: string;
}

export interface BacktestStats {
  reversal_pct: number;
  avg_gain_pct: number;
  sample_count: number;
}

export interface RiskInfo {
  sma_200: number;
  price_vs_sma_200_pct: number;
  play_type: string;
  max_drawdown_pct: number;
  suggested_stop_loss_pct: number;
}

export interface ThesisResponse {
  ticker: string;
  price: number;
  signal_direction: string;
  probability_score: number;
  why_now: string;
  macro_tailwind: string;
  risk_summary: string;
  rsi: RSIInfo;
  macd: MACDInfo;
  vix: VIXInfo;
  backtest: BacktestStats;
  risk: RiskInfo;
}

export interface SignalRow {
  ticker: string;
  price: number;
  signal_direction: string;
  probability_score: number;
  rsi_5: number;
  macd_zscore: number;
  vix_regime: string;
}

export interface SignalGridResponse {
  signals: SignalRow[];
  vix: VIXInfo;
  updated_at: string;
}

export interface PortfolioPoint {
  volatility: number;
  expected_return: number;
  sharpe: number;
  weights: Record<string, number>;
}

export interface TangencyResponse {
  current: PortfolioPoint;
  tangency: PortfolioPoint;
  frontier: PortfolioPoint[];
  rebalance_suggestion: Record<string, number>;
}

export interface TradeImpactResponse {
  sharpe_before: number;
  sharpe_after: number;
  sharpe_delta: number;
  recommendation: string;
}

export interface ChartBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  rsi_5: number;
  rsi_9: number;
  rsi_14: number;
  bb_lower: number;
  macd_line: number;
  macd_signal: number;
  macd_hist: number;
  hist_zscore: number;
  phase1: boolean;
  phase2: boolean;
  phase3: boolean;
}

// ── v2.0 types ──

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
  pinned_tickers: string[];
  created_at: string;
}

export interface ShockEvent {
  ticker: string;
  timestamp: string;
  zscore: number;
  velocity: number;
  acceleration: number;
  direction: string;
  severity: string;
}

export interface ThresholdCheck {
  exceeds_90pct: boolean;
  reversal_rate: number;
  sample_count: number;
  current_zscore: number;
}

export interface NewsArticle {
  headline: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: string;
  summary: string;
}

export interface TickerEvent {
  ticker: string;
  event_type: string;
  event_date: string;
  details: Record<string, unknown> | null;
  source: string | null;
}

export interface InsiderTrade {
  ticker: string;
  name: string;
  transaction_type: string;
  value: number;
  wealth_impact_score: number;
  date: string;
}

export interface PoliticianTrade {
  politician: string;
  ticker: string;
  transaction_type: string;
  amount: string;
  date: string;
  source: string;
}

export interface RSIHistoryDay {
  date: string;
  rsi_5: number;
  rsi_9: number;
  rsi_14: number;
  phase: number;
  close: number;
}

export interface MultiTimeframeChart {
  ticker: string;
  timeframe: string;
  bars: ChartBar[];
  reversal_points: { timestamp: string; zscore: number }[];
}
