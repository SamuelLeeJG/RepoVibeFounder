"""Portfolio Tangency / Efficient Frontier calculator."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class PortfolioPoint:
    volatility: float
    expected_return: float
    sharpe: float
    weights: dict[str, float]


@dataclass
class TangencyResult:
    current: PortfolioPoint
    tangency: PortfolioPoint
    frontier: list[PortfolioPoint]
    rebalance_suggestion: dict[str, float]  # ticker -> weight delta


class PortfolioAnalyzer:
    """Mean-Variance optimisation and Tangency point calculation."""

    def __init__(self, risk_free_rate: float = 0.05):
        self.rf = risk_free_rate

    def _annualised_stats(self, returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Return annualised mean returns and covariance matrix."""
        mean_ret = returns.mean() * 252
        cov = returns.cov() * 252
        return mean_ret.values, cov.values

    def _portfolio_stats(
        self, weights: np.ndarray, mean_ret: np.ndarray, cov: np.ndarray
    ) -> tuple[float, float, float]:
        port_ret = float(weights @ mean_ret)
        port_vol = float(np.sqrt(weights @ cov @ weights))
        sharpe = (port_ret - self.rf) / port_vol if port_vol > 0 else 0.0
        return port_ret, port_vol, sharpe

    def compute_tangency(
        self,
        returns: pd.DataFrame,
        current_weights: dict[str, float] | None = None,
    ) -> TangencyResult:
        """Compute the tangency portfolio and efficient frontier.

        Parameters
        ----------
        returns : DataFrame with columns = tickers, rows = daily returns
        current_weights : dict mapping ticker -> weight (0-1), or None for equal-weight
        """
        tickers = list(returns.columns)
        n = len(tickers)
        mean_ret, cov = self._annualised_stats(returns)

        # Current portfolio
        if current_weights is None:
            w_cur = np.ones(n) / n
        else:
            w_cur = np.array([current_weights.get(t, 0.0) for t in tickers])
            s = w_cur.sum()
            if s > 0:
                w_cur = w_cur / s
            else:
                w_cur = np.ones(n) / n

        cur_ret, cur_vol, cur_sharpe = self._portfolio_stats(w_cur, mean_ret, cov)

        # Tangency portfolio (max Sharpe)
        def neg_sharpe(w: np.ndarray) -> float:
            r = float(w @ mean_ret)
            v = float(np.sqrt(w @ cov @ w))
            return -(r - self.rf) / v if v > 1e-12 else 0.0

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0)] * n
        x0 = np.ones(n) / n
        result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
        w_tan = result.x if result.success else x0
        tan_ret, tan_vol, tan_sharpe = self._portfolio_stats(w_tan, mean_ret, cov)

        # Efficient frontier (20 points)
        target_returns = np.linspace(mean_ret.min(), mean_ret.max(), 20)
        frontier: list[PortfolioPoint] = []
        for tr in target_returns:
            def min_vol(w: np.ndarray) -> float:
                return float(np.sqrt(w @ cov @ w))

            cons = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                {"type": "eq", "fun": lambda w, _tr=tr: float(w @ mean_ret) - _tr},
            ]
            res = minimize(min_vol, x0, method="SLSQP", bounds=bounds, constraints=cons)
            if res.success:
                fr, fv, fs = self._portfolio_stats(res.x, mean_ret, cov)
                frontier.append(
                    PortfolioPoint(
                        volatility=round(fv, 4),
                        expected_return=round(fr, 4),
                        sharpe=round(fs, 3),
                        weights={tickers[i]: round(float(res.x[i]), 4) for i in range(n)},
                    )
                )

        # Rebalance suggestion: delta from current to tangency
        rebalance = {}
        for i, t in enumerate(tickers):
            delta = float(w_tan[i] - w_cur[i])
            if abs(delta) > 0.005:
                rebalance[t] = round(delta * 100, 2)  # percentage points

        return TangencyResult(
            current=PortfolioPoint(
                volatility=round(cur_vol, 4),
                expected_return=round(cur_ret, 4),
                sharpe=round(cur_sharpe, 3),
                weights={tickers[i]: round(float(w_cur[i]), 4) for i in range(n)},
            ),
            tangency=PortfolioPoint(
                volatility=round(tan_vol, 4),
                expected_return=round(tan_ret, 4),
                sharpe=round(tan_sharpe, 3),
                weights={tickers[i]: round(float(w_tan[i]), 4) for i in range(n)},
            ),
            frontier=frontier,
            rebalance_suggestion=rebalance,
        )

    def impact_of_trade(
        self,
        returns: pd.DataFrame,
        current_weights: dict[str, float],
        buy_ticker: str,
        buy_amount_pct: float,
    ) -> dict:
        """Estimate the Sharpe impact of adding *buy_amount_pct* to *buy_ticker*."""
        tickers = list(returns.columns)
        n = len(tickers)
        mean_ret, cov = self._annualised_stats(returns)

        w_before = np.array([current_weights.get(t, 0.0) for t in tickers])
        s = w_before.sum()
        if s > 0:
            w_before = w_before / s

        w_after = w_before.copy()
        if buy_ticker in tickers:
            idx = tickers.index(buy_ticker)
            w_after[idx] += buy_amount_pct / 100.0
        w_after = w_after / w_after.sum()

        _, _, sharpe_before = self._portfolio_stats(w_before, mean_ret, cov)
        _, _, sharpe_after = self._portfolio_stats(w_after, mean_ret, cov)

        return {
            "sharpe_before": round(sharpe_before, 3),
            "sharpe_after": round(sharpe_after, 3),
            "sharpe_delta": round(sharpe_after - sharpe_before, 3),
        }
