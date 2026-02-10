"""Earnings Signal Detector — flags pre-earnings momentum + insider/politician cross-reference.

Concrete signals:
1. Pre-earnings momentum: >3% price move in 5 days before earnings
2. Insider buying within 30 days of earnings
3. Politician buying within 60 days of earnings
4. Combined signal when multiple factors align
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from backend.integrations.fmp_client import FMPClient
from backend.integrations.quiver_client import QuiverClient


class EarningsSignalDetector:
    """Detect pre-earnings signals by cross-referencing price momentum,
    insider activity, and politician trades near earnings dates."""

    def __init__(self):
        self.fmp = FMPClient()
        self.quiver = QuiverClient()

    async def scan_upcoming_earnings(
        self, tickers: list[str], days_ahead: int = 7
    ) -> list[dict]:
        """Scan for tickers with earnings in the next N days and flag signals.

        Returns list of tickers with upcoming earnings + signal strength.
        """
        today = dt.date.today()
        end = today + dt.timedelta(days=days_ahead)

        # Get earnings calendar
        earnings = await self.fmp.get_earnings_calendar(
            from_date=today.isoformat(),
            to_date=end.isoformat(),
        )

        results = []
        for entry in earnings:
            ticker = entry.get("symbol", "")
            if ticker not in tickers:
                continue

            earnings_date = entry.get("date", "")
            result = {
                "ticker": ticker,
                "earnings_date": earnings_date,
                "eps_estimated": entry.get("epsEstimated"),
                "revenue_estimated": entry.get("revenueEstimated"),
                "signals": [],
                "signal_strength": 0,
            }

            # Check insider trades near earnings
            insider_trades = await self.fmp.get_insider_trades(ticker, limit=20)
            recent_insider_buys = self._filter_recent_trades(
                insider_trades, days_back=30, trade_type="buy"
            )
            if recent_insider_buys:
                result["signals"].append({
                    "type": "insider_buying",
                    "description": f"{len(recent_insider_buys)} insider buy(s) within 30 days of earnings",
                    "trades": recent_insider_buys[:5],
                    "strength": min(len(recent_insider_buys) * 15, 40),
                })
                result["signal_strength"] += min(len(recent_insider_buys) * 15, 40)

            # Check politician trades near earnings
            politician_trades = await self.quiver.get_congress_trading(ticker)
            recent_politician_buys = self._filter_politician_trades(
                politician_trades, days_back=60, trade_type="purchase"
            )
            if recent_politician_buys:
                result["signals"].append({
                    "type": "politician_buying",
                    "description": f"{len(recent_politician_buys)} politician purchase(s) within 60 days of earnings",
                    "trades": recent_politician_buys[:5],
                    "strength": min(len(recent_politician_buys) * 20, 40),
                })
                result["signal_strength"] += min(len(recent_politician_buys) * 20, 40)

            # Compute combined strength (cap at 100)
            result["signal_strength"] = min(result["signal_strength"], 100)
            result["recommendation"] = self._recommendation(result["signal_strength"])
            results.append(result)

        return sorted(results, key=lambda x: x["signal_strength"], reverse=True)

    async def analyze_single(self, ticker: str, price_data: pd.DataFrame | None = None) -> dict:
        """Full earnings signal analysis for a single ticker."""
        # Get earnings
        earnings = await self.fmp.get_earnings_for_ticker(ticker)
        if not earnings:
            return {"ticker": ticker, "has_upcoming_earnings": False, "signals": []}

        # Find next upcoming earnings
        today = dt.date.today()
        upcoming = None
        for e in earnings:
            try:
                edate = dt.date.fromisoformat(e.get("date", "")[:10])
                if edate >= today:
                    upcoming = e
                    break
            except (ValueError, TypeError):
                continue

        result = {
            "ticker": ticker,
            "has_upcoming_earnings": upcoming is not None,
            "earnings_date": upcoming.get("date", "") if upcoming else None,
            "days_until_earnings": (dt.date.fromisoformat(upcoming["date"][:10]) - today).days if upcoming else None,
            "eps_estimated": upcoming.get("epsEstimated") if upcoming else None,
            "signals": [],
            "signal_strength": 0,
            "pre_earnings_momentum": None,
        }

        # Pre-earnings momentum from price data
        if price_data is not None and len(price_data) >= 40:
            momentum = self._compute_momentum(price_data)
            result["pre_earnings_momentum"] = momentum
            if abs(momentum["pct_change_5d"]) > 3.0:
                direction = "bullish" if momentum["pct_change_5d"] > 0 else "bearish"
                result["signals"].append({
                    "type": "pre_earnings_momentum",
                    "description": f"{direction.title()} momentum: {momentum['pct_change_5d']:+.1f}% in last 5 days",
                    "strength": min(int(abs(momentum["pct_change_5d"]) * 5), 30),
                })
                result["signal_strength"] += min(int(abs(momentum["pct_change_5d"]) * 5), 30)

        # Insider trades
        insider_trades = await self.fmp.get_insider_trades(ticker, limit=20)
        recent_insider_buys = self._filter_recent_trades(insider_trades, days_back=30, trade_type="buy")
        recent_insider_sells = self._filter_recent_trades(insider_trades, days_back=30, trade_type="sell")

        if recent_insider_buys:
            result["signals"].append({
                "type": "insider_buying",
                "description": f"{len(recent_insider_buys)} insider buy(s) in last 30 days",
                "strength": min(len(recent_insider_buys) * 15, 40),
            })
            result["signal_strength"] += min(len(recent_insider_buys) * 15, 40)

        if recent_insider_sells and len(recent_insider_sells) > 2:
            result["signals"].append({
                "type": "insider_selling",
                "description": f"{len(recent_insider_sells)} insider sell(s) in last 30 days",
                "strength": -min(len(recent_insider_sells) * 10, 30),
            })
            result["signal_strength"] -= min(len(recent_insider_sells) * 10, 30)

        # Politician trades
        politician_trades = await self.quiver.get_congress_trading(ticker)
        recent_buys = self._filter_politician_trades(politician_trades, days_back=60, trade_type="purchase")
        if recent_buys:
            result["signals"].append({
                "type": "politician_buying",
                "description": f"{len(recent_buys)} politician purchase(s) in last 60 days",
                "strength": min(len(recent_buys) * 20, 40),
            })
            result["signal_strength"] += min(len(recent_buys) * 20, 40)

        result["signal_strength"] = max(0, min(result["signal_strength"], 100))
        result["recommendation"] = self._recommendation(result["signal_strength"])
        return result

    def _compute_momentum(self, df: pd.DataFrame) -> dict:
        """Compute pre-earnings price momentum metrics."""
        close = df["close"]
        pct_1d = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else 0.0
        pct_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else 0.0
        pct_10d = float((close.iloc[-1] / close.iloc[-11] - 1) * 100) if len(close) >= 11 else 0.0

        # Volume trend (compare last 5 days avg to 20-day avg)
        vol = df.get("volume")
        vol_ratio = 1.0
        if vol is not None and len(vol) >= 20:
            avg_5 = float(vol.iloc[-5:].mean())
            avg_20 = float(vol.iloc[-20:].mean())
            vol_ratio = round(avg_5 / avg_20, 2) if avg_20 > 0 else 1.0

        return {
            "pct_change_1d": round(pct_1d, 2),
            "pct_change_5d": round(pct_5d, 2),
            "pct_change_10d": round(pct_10d, 2),
            "volume_ratio_5d_vs_20d": vol_ratio,
            "direction": "bullish" if pct_5d > 0 else "bearish" if pct_5d < 0 else "flat",
        }

    def _filter_recent_trades(
        self, trades: list[dict], days_back: int = 30, trade_type: str = "buy"
    ) -> list[dict]:
        """Filter insider trades by recency and type."""
        cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
        results = []
        for t in trades:
            trade_date = t.get("transactionDate", t.get("filingDate", ""))
            if trade_date < cutoff:
                continue
            tx_type = t.get("transactionType", "").lower()
            if trade_type == "buy" and ("purchase" in tx_type or "buy" in tx_type or "p-purchase" in tx_type):
                results.append(t)
            elif trade_type == "sell" and ("sale" in tx_type or "sell" in tx_type or "s-sale" in tx_type):
                results.append(t)
        return results

    def _filter_politician_trades(
        self, trades: list[dict], days_back: int = 60, trade_type: str = "purchase"
    ) -> list[dict]:
        """Filter politician trades by recency and type."""
        cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
        results = []
        for t in trades:
            trade_date = t.get("TransactionDate", t.get("transaction_date", ""))
            if trade_date < cutoff:
                continue
            tx_type = t.get("Transaction", t.get("type", "")).lower()
            if trade_type in tx_type:
                results.append(t)
        return results

    def _recommendation(self, strength: int) -> str:
        if strength >= 60:
            return "Strong pre-earnings signal — multiple bullish indicators aligned"
        elif strength >= 30:
            return "Moderate pre-earnings signal — some bullish activity detected"
        elif strength > 0:
            return "Weak pre-earnings signal — limited unusual activity"
        else:
            return "No notable pre-earnings signals"
