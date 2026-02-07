"""FastAPI routes for the Decision Intelligence Terminal."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.api.models import (
    PortfolioPointModel,
    SignalGridResponse,
    SignalRow,
    TangencyResponse,
    ThesisResponse,
    TradeImpactRequest,
    TradeImpactResponse,
    VIXInfo,
)
from backend.api.thesis_generator import ThesisGenerator
from backend.data_provider import fetch_ohlcv, fetch_vix
from backend.engine.macd_zscore import MACDZScoreAnalyzer
from backend.engine.portfolio import PortfolioAnalyzer
from backend.engine.reversal_analyzer import ReversalAnalyzer
from backend.engine.vix_filter import VIXBetaFilter

router = APIRouter(prefix="/api/v1")
thesis_gen = ThesisGenerator()

# S&P 100 representative tickers (subset for demo)
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMZN", "AVGO",
    "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C", "CAT",
    "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS", "CVX",
    "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX", "GD",
    "GE", "GILD", "GM", "GOOG", "GS", "HD", "HON", "IBM", "INTC", "JNJ",
    "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ",
    "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX",
    "NKE", "NVDA", "ORCL", "OXY", "PEP", "PFE", "PG", "PM", "PYPL", "QCOM",
    "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS", "TSLA",
    "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WBA", "WFC", "WMT",
    "XOM",
]


@router.get("/thesis/{ticker}", response_model=ThesisResponse)
async def get_thesis(ticker: str) -> ThesisResponse:
    """Generate a full structured thesis for a ticker."""
    ticker = ticker.upper()
    try:
        return await thesis_gen.generate(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=SignalGridResponse)
async def get_signal_grid(
    tickers: Optional[str] = Query(
        default=None,
        description="Comma-separated tickers. Defaults to S&P 100 subset.",
    ),
    limit: int = Query(default=20, ge=1, le=101),
) -> SignalGridResponse:
    """Return signal rows for the grid view."""
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        ticker_list = SP100_TICKERS[:limit]

    reversal = ReversalAnalyzer()
    macd_analyzer = MACDZScoreAnalyzer()
    vix_filter = VIXBetaFilter()
    vix_df = await fetch_vix()
    vix_status = vix_filter.analyze(vix_df)

    rows: list[SignalRow] = []
    for t in ticker_list:
        try:
            df = await fetch_ohlcv(t)
            rsi_aug = reversal.compute_indicators(df)
            last = rsi_aug.iloc[-1]
            macd_data = macd_analyzer.latest_zscore(df)

            active = bool(last.get("phase3", False))
            if macd_data["regime"] == "statistical_washout" or active:
                direction = "buy"
            elif macd_data["regime"] == "exhaustion":
                direction = "sell"
            else:
                direction = "neutral"

            # Quick probability estimate
            score = 0.0
            if active:
                score += 30
            z = abs(macd_data["zscore"])
            if z > 2.0:
                score += 25
            elif z > 1.5:
                score += 15
            if vix_status.regime in ("extreme_fear_peaking", "normal"):
                score += 15
            score = min(score, 100)

            rows.append(
                SignalRow(
                    ticker=t,
                    price=round(float(df["close"].iloc[-1]), 2),
                    signal_direction=direction,
                    probability_score=round(score, 1),
                    rsi_5=round(float(last["rsi_5"]), 2) if not pd.isna(last["rsi_5"]) else 50.0,
                    macd_zscore=macd_data["zscore"],
                    vix_regime=vix_status.regime,
                )
            )
        except Exception:
            continue

    vix_info = VIXInfo(
        current_vix=vix_status.current_vix,
        vix_rsi2=vix_status.vix_rsi2,
        extreme_fear=vix_status.extreme_fear,
        lower_high_confirmed=vix_status.lower_high_confirmed,
        regime=vix_status.regime,
        recommendation=vix_status.recommendation,
    )

    return SignalGridResponse(
        signals=sorted(rows, key=lambda r: r.probability_score, reverse=True),
        vix=vix_info,
        updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )


@router.get("/chart-data/{ticker}")
async def get_chart_data(ticker: str, bars: int = Query(default=500, ge=50, le=5000)):
    """Return OHLCV + indicator data for charting."""
    ticker = ticker.upper()
    df = await fetch_ohlcv(ticker)
    reversal = ReversalAnalyzer()
    macd_analyzer = MACDZScoreAnalyzer()

    rsi_aug = reversal.compute_indicators(df)
    macd_aug = macd_analyzer.compute_indicators(df)

    # Merge
    rsi_aug["macd_line"] = macd_aug["macd_line"]
    rsi_aug["macd_signal"] = macd_aug["macd_signal"]
    rsi_aug["macd_hist"] = macd_aug["macd_hist"]
    rsi_aug["hist_zscore"] = macd_aug["hist_zscore"]

    tail = rsi_aug.tail(bars).copy()
    tail.index = tail.index.astype(str)
    records = tail.reset_index().to_dict(orient="records")

    return {"ticker": ticker, "bars": records}


@router.post("/portfolio/tangency", response_model=TangencyResponse)
async def compute_tangency(
    tickers: str = Query(description="Comma-separated tickers"),
    weights: Optional[str] = Query(default=None, description="Comma-separated weights (same order as tickers)"),
):
    """Compute portfolio tangency / efficient frontier."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    # Build returns DataFrame
    returns_dict: dict[str, pd.Series] = {}
    for t in ticker_list:
        df = await fetch_ohlcv(t, timeframe="1Day")
        returns_dict[t] = df["close"].pct_change().dropna()

    returns_df = pd.DataFrame(returns_dict).dropna()
    if returns_df.empty or len(returns_df) < 30:
        raise HTTPException(status_code=400, detail="Insufficient data for portfolio analysis")

    current_weights = None
    if weights:
        w_list = [float(w.strip()) for w in weights.split(",")]
        current_weights = dict(zip(ticker_list, w_list))

    analyzer = PortfolioAnalyzer()
    result = analyzer.compute_tangency(returns_df, current_weights)

    return TangencyResponse(
        current=PortfolioPointModel(**result.current.__dict__),
        tangency=PortfolioPointModel(**result.tangency.__dict__),
        frontier=[PortfolioPointModel(**p.__dict__) for p in result.frontier],
        rebalance_suggestion=result.rebalance_suggestion,
    )


@router.post("/portfolio/trade-impact", response_model=TradeImpactResponse)
async def trade_impact(req: TradeImpactRequest):
    """Estimate Sharpe impact of a proposed trade."""
    tickers = list(req.holdings.keys())
    if req.buy_ticker not in tickers:
        tickers.append(req.buy_ticker)

    returns_dict: dict[str, pd.Series] = {}
    for t in tickers:
        df = await fetch_ohlcv(t, timeframe="1Day")
        returns_dict[t] = df["close"].pct_change().dropna()

    returns_df = pd.DataFrame(returns_dict).dropna()
    if returns_df.empty or len(returns_df) < 30:
        raise HTTPException(status_code=400, detail="Insufficient data")

    analyzer = PortfolioAnalyzer()
    impact = analyzer.impact_of_trade(returns_df, req.holdings, req.buy_ticker, req.buy_amount_pct)

    if impact["sharpe_delta"] >= 0:
        rec = f"Adding {req.buy_amount_pct:.1f}% to {req.buy_ticker} improves Sharpe by {impact['sharpe_delta']:.3f}."
    else:
        rec = (
            f"Adding {req.buy_amount_pct:.1f}% to {req.buy_ticker} reduces Sharpe by "
            f"{abs(impact['sharpe_delta']):.3f}. Consider rebalancing."
        )

    return TradeImpactResponse(recommendation=rec, **impact)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "alpha-beta-terminal"}
