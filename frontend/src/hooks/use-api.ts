"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, setTokens, clearTokens, getAccessToken } from "@/lib/utils";
import type {
  AuthTokens,
  BenchmarkData,
  ChartBar,
  EarningsSignalData,
  InsiderTrade,
  MACDExtremeData,
  MultiTimeframeChart,
  NewsArticle,
  Notification,
  PoliticianTrade,
  PortfolioData,
  RSIHistoryDay,
  SignalGridResponse,
  TangencyResponse,
  ThesisResponse,
  TickerEvent,
  TradeImpactResponse,
  UpcomingEarningsItem,
  UserProfile,
} from "@/lib/types";

// ── Auto-refresh hook ──

function useAutoRefresh(callback: () => void, intervalMs: number, enabled = true) {
  const savedCallback = useRef(callback);
  useEffect(() => { savedCallback.current = callback; }, [callback]);

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;
    const id = setInterval(() => savedCallback.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}

// ── Signal Grid (with auto-refresh every 60s) ──

export function useSignalGrid(tickers?: string, limit = 20, search?: string, sector?: string, sortBy = "probability_score", sortDir = "desc") {
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
      if (search) params.set("search", search);
      if (sector) params.set("sector", sector);
      params.set("sort_by", sortBy);
      params.set("sort_dir", sortDir);
      const res = await apiFetch<SignalGridResponse>(
        `/api/v1/signals?${params.toString()}`
      );
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch signals");
    } finally {
      setLoading(false);
    }
  }, [tickers, limit, search, sector, sortBy, sortDir]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useAutoRefresh(fetchData, 60000);

  return { data, loading, error, refetch: fetchData };
}

export function useThesis(ticker: string | null) {
  const [data, setData] = useState<ThesisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) { setData(null); return; }
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch<ThesisResponse>(`/api/v1/thesis/${ticker}`)
      .then((res) => { if (!cancelled) setData(res); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  return { data, loading, error };
}

export function useChartData(ticker: string | null, timeframe = "1Hour", bars = 500) {
  const [data, setData] = useState<ChartBar[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    apiFetch<{ bars: ChartBar[] }>(
      `/api/v1/chart-data/${ticker}/multi?timeframe=${timeframe}&bars=${bars}`
    )
      .then((res) => { if (!cancelled) setData(res.bars); })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, timeframe, bars]);

  return { data, loading };
}

export function useTangency(tickers: string[], weights?: number[]) {
  const [data, setData] = useState<TangencyResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tickers.length < 2) { setData(null); return; }
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams();
    params.set("tickers", tickers.join(","));
    if (weights) params.set("weights", weights.join(","));
    apiFetch<TangencyResponse>(
      `/api/v1/portfolio/tangency?${params.toString()}`,
      { method: "POST" }
    )
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
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
    body: JSON.stringify({ holdings, buy_ticker: buyTicker, buy_amount_pct: buyAmountPct }),
  });
}

// ── Auth hooks ──

export function useAuth() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { setLoading(false); return; }
    apiFetch<UserProfile>("/api/v1/auth/me")
      .then(setUser)
      .catch(() => { clearTokens(); setUser(null); })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiFetch<AuthTokens>("/api/v1/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
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

  const requestAccess = async (email: string, displayName: string, reason: string) => {
    return apiFetch<{ message: string }>("/api/v1/auth/request-access", {
      method: "POST", body: JSON.stringify({ email, display_name: displayName, reason }),
    });
  };

  const resetPassword = async (email: string) => {
    return apiFetch<{ message: string }>("/api/v1/auth/password-reset/request", {
      method: "POST", body: JSON.stringify({ email }),
    });
  };

  const logout = () => { clearTokens(); setUser(null); };

  return { user, loading, login, register, requestAccess, resetPassword, logout };
}

// ── Data hooks ──

export function useTickerNews(ticker: string | null) {
  const [data, setData] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let c = false;
    setLoading(true);
    apiFetch<NewsArticle[]>(`/api/v1/news/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function useTickerEvents(ticker: string | null) {
  const [data, setData] = useState<TickerEvent[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let c = false;
    setLoading(true);
    apiFetch<TickerEvent[]>(`/api/v1/events/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function useInsiderTrades(ticker: string | null) {
  const [data, setData] = useState<InsiderTrade[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let c = false;
    setLoading(true);
    apiFetch<InsiderTrade[]>(`/api/v1/insider-trades/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function usePoliticianTrades(ticker: string | null) {
  const [data, setData] = useState<PoliticianTrade[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let c = false;
    setLoading(true);
    apiFetch<PoliticianTrade[]>(`/api/v1/politician-trades/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function useRSIHistory(ticker: string | null, days = 3) {
  const [data, setData] = useState<RSIHistoryDay[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData([]); return; }
    let c = false;
    setLoading(true);
    apiFetch<{ history: RSIHistoryDay[] }>(`/api/v1/rsi-history/${ticker}?days=${days}`)
      .then((r) => { if (!c) setData(r.history); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker, days]);
  return { data, loading };
}

export function useMultiTimeframeChart(ticker: string | null, timeframe = "1Hour", bars = 500) {
  const [data, setData] = useState<MultiTimeframeChart | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData(null); return; }
    let c = false;
    setLoading(true);
    apiFetch<MultiTimeframeChart>(`/api/v1/chart-data/${ticker}/multi?timeframe=${timeframe}&bars=${bars}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData(null); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker, timeframe, bars]);
  return { data, loading };
}

// ── v2.1 hooks ──

export function useMACDExtreme(ticker: string | null) {
  const [data, setData] = useState<MACDExtremeData | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData(null); return; }
    let c = false;
    setLoading(true);
    apiFetch<MACDExtremeData>(`/api/v1/macd-extreme/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData(null); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function useEarningsSignal(ticker: string | null) {
  const [data, setData] = useState<EarningsSignalData | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!ticker) { setData(null); return; }
    let c = false;
    setLoading(true);
    apiFetch<EarningsSignalData>(`/api/v1/earnings-signal/${ticker}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData(null); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [ticker]);
  return { data, loading };
}

export function useUpcomingEarnings(days = 7) {
  const [data, setData] = useState<UpcomingEarningsItem[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let c = false;
    setLoading(true);
    apiFetch<UpcomingEarningsItem[]>(`/api/v1/upcoming-earnings?days=${days}`)
      .then((r) => { if (!c) setData(r); })
      .catch(() => { if (!c) setData([]); })
      .finally(() => { if (!c) setLoading(false); });
    return () => { c = true; };
  }, [days]);
  return { data, loading };
}

export function useNotifications(userId: string | null) {
  const [data, setData] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetch = useCallback(async () => {
    if (!userId) return;
    try {
      const notes = await apiFetch<Notification[]>(`/api/v1/notifications/${userId}`);
      setData(notes);
      setUnreadCount(notes.filter((n) => !n.read).length);
    } catch { /* ignore */ }
  }, [userId]);

  useEffect(() => { fetch(); }, [fetch]);
  useAutoRefresh(fetch, 30000, !!userId);

  const markRead = async (notificationId: string) => {
    if (!userId) return;
    await apiFetch(`/api/v1/notifications/${userId}/read/${notificationId}`, { method: "POST" });
    await fetch();
  };

  const markAllRead = async () => {
    if (!userId) return;
    await apiFetch(`/api/v1/notifications/${userId}/read-all`, { method: "POST" });
    await fetch();
  };

  return { notifications: data, unreadCount, markRead, markAllRead, refetch: fetch };
}

export function useSectors() {
  const [sectors, setSectors] = useState<string[]>([]);
  useEffect(() => {
    apiFetch<{ sectors: string[] }>("/api/v1/sectors")
      .then((r) => setSectors(r.sectors))
      .catch(() => {});
  }, []);
  return sectors;
}

export function usePortfolio(userId: string | null) {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    // Portfolio is loaded from the tangency endpoint for now
    // In production this would use the persistent portfolio service
  }, [userId]);

  return { data, loading, refetch: fetch };
}

export async function exportSignalsCSV(limit = 50) {
  const res = await window.fetch(
    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/export/signals?limit=${limit}`
  );
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `signals_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
