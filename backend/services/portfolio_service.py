"""Persistent Portfolio CRUD service — database-backed portfolio management.

Supports add/remove holdings with $ value or %, constraints enforcement,
and benchmark comparison (SPY/QQQ).
"""

from __future__ import annotations

import datetime as dt
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PortfolioSnapshot, PortfolioTrade
from backend.engine.portfolio import PortfolioAnalyzer
from backend.data_provider import fetch_ohlcv

# Position constraints
MAX_SINGLE_POSITION_PCT = 25.0  # No more than 25% in one stock
MIN_POSITION_PCT = 1.0  # Minimum 1% position
MAX_POSITIONS = 30  # Maximum 30 holdings

BENCHMARKS = ["SPY", "QQQ"]


class PortfolioService:
    """Manage user portfolios with persistent storage, constraints, and optimization."""

    def __init__(self):
        self.analyzer = PortfolioAnalyzer()

    async def get_portfolio(self, user_id: uuid.UUID, db: AsyncSession) -> dict | None:
        """Get the user's latest portfolio snapshot."""
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.created_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            return None
        return {
            "id": str(snapshot.id),
            "tickers": snapshot.tickers,
            "weights": snapshot.weights,
            "tangency_weights": snapshot.tangency_weights,
            "sharpe": snapshot.sharpe,
            "total_value": snapshot.total_value,
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else "",
        }

    async def save_portfolio(
        self,
        user_id: uuid.UUID,
        holdings: dict[str, float],
        total_value: float | None,
        mode: str,
        db: AsyncSession,
    ) -> dict:
        """Save or update portfolio holdings.

        Args:
            holdings: ticker -> weight (if mode='pct') or ticker -> dollar value (if mode='dollar')
            total_value: total portfolio value in $ (required for dollar mode)
            mode: 'pct' or 'dollar'
        """
        # Convert dollar values to percentages
        if mode == "dollar":
            if total_value is None or total_value <= 0:
                total_value = sum(holdings.values())
            weights = {}
            for ticker, value in holdings.items():
                weights[ticker.upper()] = round(value / total_value * 100, 2)
        else:
            weights = {t.upper(): w for t, w in holdings.items()}
            if total_value is None:
                total_value = 0.0

        # Validate constraints
        errors = self._validate_constraints(weights)
        if errors:
            return {"error": True, "messages": errors}

        # Normalize weights to sum to 100
        total_weight = sum(weights.values())
        if total_weight > 0 and abs(total_weight - 100) > 0.1:
            factor = 100 / total_weight
            weights = {t: round(w * factor, 2) for t, w in weights.items()}

        # Compute tangency portfolio
        tickers = list(weights.keys())
        tangency_weights = None
        sharpe = 0.0

        try:
            returns_dict: dict[str, pd.Series] = {}
            for t in tickers:
                df = await fetch_ohlcv(t, timeframe="1Day")
                returns_dict[t] = df["close"].pct_change().dropna()

            returns_df = pd.DataFrame(returns_dict).dropna()
            if len(returns_df) >= 30:
                current_w = {t: w / 100 for t, w in weights.items()}
                result = self.analyzer.compute_tangency(returns_df, current_w)
                tangency_weights = {t: round(w * 100, 2) for t, w in result.tangency.weights.items()}
                sharpe = result.current.sharpe
        except Exception:
            pass

        # Save snapshot
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            tickers=tickers,
            weights=weights,
            tangency_weights=tangency_weights,
            sharpe=round(sharpe, 4),
            total_value=total_value,
        )
        db.add(snapshot)
        await db.flush()

        return {
            "error": False,
            "id": str(snapshot.id),
            "tickers": tickers,
            "weights": weights,
            "tangency_weights": tangency_weights,
            "sharpe": round(sharpe, 4),
            "total_value": total_value,
        }

    async def add_holding(
        self,
        user_id: uuid.UUID,
        ticker: str,
        weight_or_value: float,
        mode: str,
        db: AsyncSession,
    ) -> dict:
        """Add a single holding to the portfolio."""
        existing = await self.get_portfolio(user_id, db)
        holdings = {}
        total_value = 0.0

        if existing:
            holdings = dict(existing["weights"])
            total_value = existing.get("total_value") or 0.0

        ticker = ticker.upper()

        if mode == "dollar" and total_value > 0:
            weight = weight_or_value / total_value * 100
            total_value += weight_or_value
        else:
            weight = weight_or_value

        holdings[ticker] = holdings.get(ticker, 0) + weight

        return await self.save_portfolio(user_id, holdings, total_value, "pct", db)

    async def remove_holding(
        self, user_id: uuid.UUID, ticker: str, db: AsyncSession
    ) -> dict:
        """Remove a holding from the portfolio."""
        existing = await self.get_portfolio(user_id, db)
        if not existing:
            return {"error": True, "messages": ["No portfolio found"]}

        holdings = dict(existing["weights"])
        ticker = ticker.upper()
        if ticker not in holdings:
            return {"error": True, "messages": [f"{ticker} not in portfolio"]}

        del holdings[ticker]

        if not holdings:
            return {"error": True, "messages": ["Cannot remove last holding"]}

        return await self.save_portfolio(
            user_id, holdings, existing.get("total_value"), "pct", db
        )

    async def get_benchmark_comparison(self, user_id: uuid.UUID, db: AsyncSession) -> dict:
        """Compare portfolio performance to SPY and QQQ benchmarks."""
        portfolio = await self.get_portfolio(user_id, db)
        if not portfolio:
            return {"error": "No portfolio found"}

        weights = portfolio["weights"]
        tickers = list(weights.keys())

        # Fetch returns for portfolio holdings + benchmarks
        all_tickers = tickers + BENCHMARKS
        returns_dict: dict[str, pd.Series] = {}
        for t in all_tickers:
            try:
                df = await fetch_ohlcv(t, timeframe="1Day")
                returns_dict[t] = df["close"].pct_change().dropna()
            except Exception:
                continue

        if not returns_dict:
            return {"error": "Could not fetch price data"}

        returns_df = pd.DataFrame(returns_dict).dropna()
        if len(returns_df) < 30:
            return {"error": "Insufficient data for comparison"}

        # Portfolio returns
        portfolio_weights = np.array([weights.get(t, 0) / 100 for t in tickers if t in returns_df.columns])
        portfolio_cols = [t for t in tickers if t in returns_df.columns]
        portfolio_returns = returns_df[portfolio_cols].values @ portfolio_weights

        result = {
            "portfolio": self._compute_perf_metrics(portfolio_returns, "Your Portfolio"),
        }

        for bm in BENCHMARKS:
            if bm in returns_df.columns:
                bm_returns = returns_df[bm].values
                result[bm.lower()] = self._compute_perf_metrics(bm_returns, bm)

        return result

    def _compute_perf_metrics(self, returns: np.ndarray, name: str) -> dict:
        """Compute performance metrics for a returns series."""
        ann_factor = 252
        total_return = float(np.prod(1 + returns) - 1) * 100
        ann_return = float(np.mean(returns) * ann_factor) * 100
        ann_vol = float(np.std(returns) * np.sqrt(ann_factor)) * 100
        sharpe = float(ann_return / ann_vol) if ann_vol > 0 else 0.0

        # Max drawdown
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_dd = float(np.min(drawdown)) * 100

        return {
            "name": name,
            "total_return_pct": round(total_return, 2),
            "annualized_return_pct": round(ann_return, 2),
            "annualized_vol_pct": round(ann_vol, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown_pct": round(max_dd, 2),
        }

    async def record_trade(
        self,
        user_id: uuid.UUID,
        ticker: str,
        action: str,
        amount_pct: float,
        sharpe_before: float | None,
        sharpe_after: float | None,
        db: AsyncSession,
    ):
        """Record a portfolio trade for audit trail."""
        trade = PortfolioTrade(
            user_id=user_id,
            ticker=ticker.upper(),
            action=action,
            amount_pct=amount_pct,
            sharpe_before=sharpe_before,
            sharpe_after=sharpe_after,
        )
        db.add(trade)
        await db.flush()

    async def get_trade_history(self, user_id: uuid.UUID, db: AsyncSession, limit: int = 50) -> list[dict]:
        """Get user's trade history."""
        result = await db.execute(
            select(PortfolioTrade)
            .where(PortfolioTrade.user_id == user_id)
            .order_by(PortfolioTrade.created_at.desc())
            .limit(limit)
        )
        trades = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "ticker": t.ticker,
                "action": t.action,
                "amount_pct": t.amount_pct,
                "sharpe_before": t.sharpe_before,
                "sharpe_after": t.sharpe_after,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }
            for t in trades
        ]

    def _validate_constraints(self, weights: dict[str, float]) -> list[str]:
        """Validate portfolio constraints."""
        errors = []
        if len(weights) > MAX_POSITIONS:
            errors.append(f"Maximum {MAX_POSITIONS} positions allowed")
        for ticker, weight in weights.items():
            if weight > MAX_SINGLE_POSITION_PCT:
                errors.append(f"{ticker}: {weight:.1f}% exceeds max single position of {MAX_SINGLE_POSITION_PCT}%")
            if weight < 0:
                errors.append(f"{ticker}: short positions not allowed")
        return errors
