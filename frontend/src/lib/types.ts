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
