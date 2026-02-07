"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/utils";
import type {
  ChartBar,
  SignalGridResponse,
  TangencyResponse,
  ThesisResponse,
  TradeImpactResponse,
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
