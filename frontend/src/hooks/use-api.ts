"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, setTokens, clearTokens, getAccessToken } from "@/lib/utils";
import type {
  AuthTokens,
  ChartBar,
  InsiderTrade,
  MultiTimeframeChart,
  NewsArticle,
  PoliticianTrade,
  RSIHistoryDay,
  SignalGridResponse,
  TangencyResponse,
  ThesisResponse,
  TickerEvent,
  TradeImpactResponse,
  UserProfile,
} from "@/lib/types";

export function useSignalGrid(tickers?: string, limit = 20) {
  const [data, setData] = useState<SignalGridResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (tickers) params.set("tickers", tickers);
      params.set("limit", String(limit));
      const res = await apiFetch<SignalGridResponse>(
        `/api/v1/signals?${params.toString()}`
      );
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch signals");
    } finally {
      setLoading(false);
    }
  }, [tickers, limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

export function useThesis(ticker: string | null) {
  const [data, setData] = useState<ThesisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch<ThesisResponse>(`/api/v1/thesis/${ticker}`)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return { data, loading, error };
}

export function useChartData(ticker: string | null, bars = 500) {
  const [data, setData] = useState<ChartBar[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) {
      setData([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiFetch<{ bars: ChartBar[] }>(
      `/api/v1/chart-data/${ticker}?bars=${bars}`
    )
      .then((res) => {
        if (!cancelled) setData(res.bars);
      })
      .catch(() => {
        if (!cancelled) setData([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, bars]);

  return { data, loading };
}

export function useTangency(tickers: string[], weights?: number[]) {
  const [data, setData] = useState<TangencyResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tickers.length < 2) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams();
    params.set("tickers", tickers.join(","));
    if (weights) params.set("weights", weights.join(","));
    apiFetch<TangencyResponse>(
      `/api/v1/portfolio/tangency?${params.toString()}`,
      { method: "POST" }
    )
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tickers.join(","), weights?.join(",")]);

  return { data, loading };
}

export async function fetchTradeImpact(
  holdings: Record<string, number>,
  buyTicker: string,
  buyAmountPct: number
): Promise<TradeImpactResponse> {
  return apiFetch<TradeImpactResponse>("/api/v1/portfolio/trade-impact", {
    method: "POST",
    body: JSON.stringify({
      holdings,
      buy_ticker: buyTicker,
      buy_amount_pct: buyAmountPct,
    }),
  });
}

// ── v2.0 Auth hooks ──

export function useAuth() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiFetch<UserProfile>("/api/v1/auth/me")
      .then(setUser)
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiFetch<AuthTokens>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(res.access_token, res.refresh_token);
    const profile = await apiFetch<UserProfile>("/api/v1/auth/me");
    setUser(profile);
    return profile;
  };

  const register = async (email: string, password: string, displayName: string, inviteCode: string) => {
    const res = await apiFetch<AuthTokens>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName, invite_code: inviteCode }),
    });
    setTokens(res.access_token, res.refresh_token);
    const profile = await apiFetch<UserProfile>("/api/v1/auth/me");
    setUser(profile);
    return profile;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  return { user, loading, login, register, logout };
}

// ── v2.0 Data hooks ──

export function useTickerNews(ticker: string | null) {
  const [data, setData] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<NewsArticle[]>(`/api/v1/news/${ticker}`)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  return { data, loading };
}

export function useTickerEvents(ticker: string | null) {
  const [data, setData] = useState<TickerEvent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<TickerEvent[]>(`/api/v1/events/${ticker}`)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  return { data, loading };
}

export function useInsiderTrades(ticker: string | null) {
  const [data, setData] = useState<InsiderTrade[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<InsiderTrade[]>(`/api/v1/insider-trades/${ticker}`)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  return { data, loading };
}

export function usePoliticianTrades(ticker: string | null) {
  const [data, setData] = useState<PoliticianTrade[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<PoliticianTrade[]>(`/api/v1/politician-trades/${ticker}`)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  return { data, loading };
}

export function useRSIHistory(ticker: string | null, days = 3) {
  const [data, setData] = useState<RSIHistoryDay[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<{ history: RSIHistoryDay[] }>(`/api/v1/rsi-history/${ticker}?days=${days}`)
      .then((res) => { if (!cancelled) setData(res.history); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, days]);

  return { data, loading };
}

export function useMultiTimeframeChart(ticker: string | null, timeframe = "1Hour", bars = 500) {
  const [data, setData] = useState<MultiTimeframeChart | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData(null); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<MultiTimeframeChart>(
      `/api/v1/chart-data/${ticker}/multi?timeframe=${timeframe}&bars=${bars}`
    )
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, timeframe, bars]);

  return { data, loading };
}
