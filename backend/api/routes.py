"""FastAPI routes for the Decision Intelligence Terminal."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.api.models import (
    BacktestDetailResponse,
    EventModel,
    InsiderTradeModel,
    NewsArticleModel,
    PoliticianTradeModel,
    PortfolioPointModel,
    ShockEventModel,
    SignalGridResponse,
    SignalRow,
    TangencyResponse,
    ThesisResponse,
    ThresholdCheckResponse,
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
from backend.integrations.fmp_client import FMPClient
from backend.integrations.news_client import NewsClient
from backend.integrations.quiver_client import QuiverClient
from backend.services.backtest_service import get_historical_win_rate
from backend.services.shock_detector import MACDVelocityShockDetector

router = APIRouter(prefix="/api/v1")
thesis_gen = ThesisGenerator()
fmp = FMPClient()
news_client = NewsClient()
quiver = QuiverClient()
shock_detector = MACDVelocityShockDetector()

# S&P 500 tickers
SP500_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE",
    "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK",
    "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMZN",
    "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO",
    "ATVI", "AVGO", "AVY", "AWK", "AXP", "AZO", "BA", "BAC", "BAX", "BBWI",
    "BBY", "BDX", "BEN", "BF.B", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK",
    "BMY", "BR", "BRK.B", "BRO", "BSX", "BWA", "BXP", "C", "CAG", "CAH",
    "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDAY", "CDNS", "CDW",
    "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL",
    "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF",
    "COO", "COP", "COST", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP",
    "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D",
    "DAL", "DD", "DE", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DISH",
    "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN",
    "DXC", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN",
    "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS", "ETN",
    "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG",
    "FAST", "FBHS", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS", "FISV", "FITB",
    "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV", "GD", "GE",
    "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN",
    "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HOLX", "HON",
    "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUM", "HWM", "IBM", "ICE",
    "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH", "IP", "IPG",
    "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JCI",
    "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM",
    "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "L", "LDOS", "LEN", "LH",
    "LHX", "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX", "LUMN",
    "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD",
    "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC",
    "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR",
    "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD",
    "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC",
    "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS",
    "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE", "OMC", "ON", "ORCL", "ORLY",
    "OTIS", "OXY", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG", "PEP",
    "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PKI", "PLD", "PM",
    "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC",
    "PVH", "PWR", "PXD", "PYPL", "QCOM", "QRVO", "RCL", "RE", "REG", "REGN",
    "RF", "RHI", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG",
    "RTX", "SBAC", "SBNY", "SBUX", "SCHW", "SEE", "SHW", "SIVB", "SJM", "SLB",
    "SNA", "SNPS", "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ",
    "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH",
    "TEL", "TER", "TFC", "TFX", "TGT", "TMO", "TMUS", "TPR", "TRGP", "TRMB",
    "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL",
    "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V",
    "VFC", "VICI", "VLO", "VMC", "VNO", "VRSK", "VRSN", "VRTX", "VTR", "VTRS",
    "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR",
    "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL",
    "XOM", "XRAY", "XYL", "YUM", "ZBH", "ZBRA", "ZION", "ZTS",
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
    limit: int = Query(default=503, ge=1, le=503),
) -> SignalGridResponse:
    """Return signal rows for the grid view."""
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        ticker_list = SP500_TICKERS[:limit]

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
            zscore = macd_data["zscore"]

            # Direction: buy on washout/RSI alignment, sell on exhaustion
            if macd_data["regime"] == "statistical_washout" or active:
                direction = "buy"
            elif macd_data["regime"] == "exhaustion":
                direction = "sell"
            else:
                direction = "neutral"

            # Arrow indicator per PRD:
            #   Green arrow (buy): MACD-Hist Z < -2 SD OR RSI Phase-3 active
            #   Red arrow (sell):  MACD-Hist Z > +2 SD (exhaustion)
            if zscore < -2.0 or active:
                arrow = "green_up"
            elif zscore > 2.0:
                arrow = "red_down"
            else:
                arrow = "none"

            # Quick probability estimate
            score = 0.0
            if active:
                score += 30
            z = abs(zscore)
            if z > 2.0:
                score += 25
            elif z > 1.5:
                score += 15
            if vix_status.regime in ("extreme_fear_peaking", "normal"):
                score += 15
            score = min(score, 100)

            # Quick reversal backtest
            bt = reversal.backtest_reversal(df, vix_df)

            rows.append(
                SignalRow(
                    ticker=t,
                    price=round(float(df["close"].iloc[-1]), 2),
                    signal_direction=direction,
                    signal_arrow=arrow,
                    probability_score=round(score, 1),
                    rsi_5=round(float(last["rsi_5"]), 2) if not pd.isna(last["rsi_5"]) else 50.0,
                    macd_zscore=macd_data["zscore"],
                    vix_regime=vix_status.regime,
                    reversal_pct=bt["reversal_pct"],
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
    return {"status": "ok", "service": "alpha-beta-terminal", "version": "2.0.0"}


# ── v2.0 Routes ──


@router.get("/backtest/{ticker}", response_model=BacktestDetailResponse)
async def get_ticker_backtest(
    ticker: str,
    signal_type: str = Query(default="rsi_phase3", description="rsi_phase3 | macd_washout | combined"),
    timeframe: str = Query(default="1Hour"),
):
    """Get ticker-specific backtest results (replaces flat 72% rate)."""
    ticker = ticker.upper()
    result = await get_historical_win_rate(ticker, signal_type, timeframe)
    return BacktestDetailResponse(**result)


@router.get("/shock/{ticker}")
async def get_shock_status(ticker: str):
    """Check for MACD velocity shock on a ticker."""
    ticker = ticker.upper()
    df = await fetch_ohlcv(ticker)
    shock = shock_detector.latest_shock(df, ticker)
    threshold = shock_detector.check_90pct_threshold(df)
    return {
        "ticker": ticker,
        "latest_shock": shock,
        "threshold_check": threshold,
    }


@router.get("/threshold/{ticker}", response_model=ThresholdCheckResponse)
async def check_90pct_threshold(ticker: str):
    """Check if MACD-Z reversal rate exceeds 90% threshold for a ticker."""
    ticker = ticker.upper()
    df = await fetch_ohlcv(ticker)
    result = shock_detector.check_90pct_threshold(df)
    return ThresholdCheckResponse(**result)


@router.get("/news/{ticker}", response_model=list[NewsArticleModel])
async def get_ticker_news(ticker: str, days: int = Query(default=7, ge=1, le=30)):
    """Get recent news for a ticker."""
    ticker = ticker.upper()
    articles = await news_client.get_news(ticker, days)
    return [
        NewsArticleModel(
            headline=a.get("headline", ""),
            source=a.get("source", ""),
            url=a.get("url", ""),
            published_at=a.get("published_at", ""),
            sentiment=a.get("sentiment", "neutral"),
            summary=a.get("summary", ""),
        )
        for a in articles
    ]


@router.get("/events/{ticker}", response_model=list[EventModel])
async def get_ticker_events(ticker: str):
    """Get upcoming events (earnings, etc.) for a ticker."""
    ticker = ticker.upper()
    events = []

    # Earnings from FMP
    earnings = await fmp.get_earnings_for_ticker(ticker)
    for e in earnings[:5]:
        events.append(
            EventModel(
                ticker=ticker,
                event_type="earnings",
                event_date=e.get("date", ""),
                details={
                    "eps_estimated": e.get("epsEstimated"),
                    "eps_actual": e.get("eps"),
                    "revenue_estimated": e.get("revenueEstimated"),
                    "revenue_actual": e.get("revenue"),
                },
                source="FMP",
            )
        )

    return events


@router.get("/insider-trades/{ticker}", response_model=list[InsiderTradeModel])
async def get_insider_trades(ticker: str, limit: int = Query(default=20, ge=1, le=100)):
    """Get insider trading activity for a ticker."""
    ticker = ticker.upper()
    trades = await fmp.get_insider_trades(ticker, limit)
    return [
        InsiderTradeModel(
            ticker=ticker,
            name=t.get("reportingName", t.get("reportingCik", "Unknown")),
            transaction_type=t.get("transactionType", ""),
            value=float(t.get("securitiesTransacted", 0) or 0) * float(t.get("price", 0) or 0),
            wealth_impact_score=0.0,  # Computed by Quiver enrichment if available
            date=t.get("transactionDate", t.get("filingDate", "")),
        )
        for t in trades
    ]


@router.get("/politician-trades/{ticker}", response_model=list[PoliticianTradeModel])
async def get_politician_trades(ticker: str):
    """Get politician/congressional trading data for a ticker."""
    ticker = ticker.upper()

    # Try Quiver first, fall back to FMP senate
    congress_trades = await quiver.get_congress_trading(ticker)
    if not congress_trades:
        congress_trades = await fmp.get_senate_trades(ticker)

    results = []
    for t in congress_trades[:20]:
        results.append(
            PoliticianTradeModel(
                politician=t.get("Representative", t.get("senator", "Unknown")),
                ticker=ticker,
                transaction_type=t.get("Transaction", t.get("type", "")),
                amount=str(t.get("Amount", t.get("amount", ""))),
                date=t.get("TransactionDate", t.get("transaction_date", "")),
                source="Quiver" if "Representative" in t else "FMP",
            )
        )

    return results


@router.get("/company/{ticker}")
async def get_company_info(ticker: str):
    """Get company profile info (full name, etc.)."""
    ticker = ticker.upper()
    profile = await fmp.get_company_profile(ticker)
    if profile:
        return {
            "ticker": ticker,
            "company_name": profile.get("companyName", ticker),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "market_cap": profile.get("mktCap", 0),
            "description": profile.get("description", ""),
        }
    return {"ticker": ticker, "company_name": ticker}


@router.get("/chart-data/{ticker}/multi")
async def get_multi_timeframe_chart(
    ticker: str,
    timeframe: str = Query(default="1Hour", description="1Hour | 1Day"),
    bars: int = Query(default=500, ge=50, le=5000),
):
    """Return OHLCV + indicator data for charting at multiple timeframes."""
    ticker = ticker.upper()
    tf = timeframe if timeframe in ("1Hour", "1Day") else "1Hour"
    df = await fetch_ohlcv(ticker, timeframe=tf)

    reversal = ReversalAnalyzer()
    macd_analyzer = MACDZScoreAnalyzer()

    rsi_aug = reversal.compute_indicators(df)
    macd_aug = macd_analyzer.compute_indicators(df)

    rsi_aug["macd_line"] = macd_aug["macd_line"]
    rsi_aug["macd_signal"] = macd_aug["macd_signal"]
    rsi_aug["macd_hist"] = macd_aug["macd_hist"]
    rsi_aug["hist_zscore"] = macd_aug["hist_zscore"]

    # Find MACD-Z reversal points for labeling
    reversal_points = []
    zscores = rsi_aug["hist_zscore"].dropna()
    for idx in zscores.index:
        z = float(zscores.loc[idx])
        if abs(z) > 2.0:
            reversal_points.append({"timestamp": str(idx), "zscore": round(z, 2)})

    tail = rsi_aug.tail(bars).copy()
    tail.index = tail.index.astype(str)
    records = tail.reset_index().to_dict(orient="records")

    return {
        "ticker": ticker,
        "timeframe": tf,
        "bars": records,
        "reversal_points": reversal_points[-20:],  # Last 20 reversal points
    }


@router.get("/rsi-history/{ticker}")
async def get_rsi_history(ticker: str, days: int = Query(default=3, ge=1, le=30)):
    """Return RSI history table for the last N days."""
    ticker = ticker.upper()
    df = await fetch_ohlcv(ticker)
    reversal = ReversalAnalyzer()
    aug = reversal.compute_indicators(df)

    bars_per_day = 8  # Hourly bars in a trading day
    tail = aug.tail(days * bars_per_day)

    # Resample to daily for the table
    daily_data = []
    current_date = None
    day_rows = []

    for idx in tail.index:
        date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
        if date_str != current_date:
            if day_rows:
                last_row = day_rows[-1]
                daily_data.append({
                    "date": current_date,
                    "rsi_5": round(float(last_row.get("rsi_5", 50)), 2),
                    "rsi_9": round(float(last_row.get("rsi_9", 50)), 2),
                    "rsi_14": round(float(last_row.get("rsi_14", 50)), 2),
                    "phase": 3 if last_row.get("phase3") else (2 if last_row.get("phase2") else (1 if last_row.get("phase1") else 0)),
                    "close": round(float(last_row.get("close", 0)), 2),
                })
            current_date = date_str
            day_rows = []
        day_rows.append(tail.loc[idx])

    # Don't forget the last day
    if day_rows and current_date:
        last_row = day_rows[-1]
        daily_data.append({
            "date": current_date,
            "rsi_5": round(float(last_row.get("rsi_5", 50)), 2),
            "rsi_9": round(float(last_row.get("rsi_9", 50)), 2),
            "rsi_14": round(float(last_row.get("rsi_14", 50)), 2),
            "phase": 3 if last_row.get("phase3") else (2 if last_row.get("phase2") else (1 if last_row.get("phase1") else 0)),
            "close": round(float(last_row.get("close", 0)), 2),
        })

    return {"ticker": ticker, "days": days, "history": daily_data}
