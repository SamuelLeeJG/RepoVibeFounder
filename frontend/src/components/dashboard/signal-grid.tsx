"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SignalRow, VIXInfo } from "@/lib/types";

function directionVariant(d: string) {
  if (d === "buy") return "buy" as const;
  if (d === "sell") return "sell" as const;
  return "neutral" as const;
}

function probColor(score: number) {
  if (score >= 60) return "text-emerald-400";
  if (score >= 35) return "text-amber-400";
  return "text-zinc-500";
}

const HEADER_TOOLTIPS: Record<string, string> = {
  ticker: "Stock ticker symbol. Click to sort A-Z.",
  price: "Latest closing price in USD.",
  signal: "Buy = RSI Phase 3 or MACD washout. Sell = MACD exhaustion.",
  prob: "Probability (0-100) combining RSI phase, MACD Z-score, and VIX regime.",
  rsi5: "RSI(5) — fast momentum. <30 = oversold.",
  rsi9: "RSI(9) — medium momentum. Alignment with RSI(5) strengthens signal.",
  rsi14: "RSI(14) — standard period. Triple alignment = Phase 3 trigger.",
  macdz: "MACD Histogram Z-Score. <-2 SD = washout (buy). >+2 SD = exhaustion (sell).",
  reversal: "Historical reversal rate at this signal level (3-year backtest).",
};

interface SignalGridProps {
  signals: SignalRow[];
  vix: VIXInfo;
  updatedAt: string;
  onSelect: (ticker: string) => void;
  selectedTicker: string | null;
  pinnedTickers?: string[];
  sectors?: string[];
}

type SortField = "ticker" | "price" | "signal_direction" | "probability_score" | "rsi_5" | "macd_zscore" | "reversal_pct";

export function SignalGrid({
  signals, vix, updatedAt, onSelect, selectedTicker,
  pinnedTickers = [], sectors = [],
}: SignalGridProps) {
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("probability_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [tooltip, setTooltip] = useState<string | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir(field === "ticker" ? "asc" : "desc");
    }
  };

  const filteredAndSorted = useMemo(() => {
    let rows = [...signals];
    if (search) {
      const s = search.toUpperCase();
      rows = rows.filter((r) => r.ticker.includes(s));
    }
    if (sectorFilter) {
      rows = rows.filter((r) => r.sector === sectorFilter);
    }
    const dir = sortDir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      if (sortField === "ticker") return a.ticker.localeCompare(b.ticker) * dir;
      if (sortField === "signal_direction") {
        const order: Record<string, number> = { buy: 0, sell: 1, neutral: 2 };
        return ((order[a.signal_direction] ?? 3) - (order[b.signal_direction] ?? 3)) * dir;
      }
      return ((a[sortField] as number) - (b[sortField] as number)) * dir;
    });
    if (pinnedTickers.length > 0) {
      const pinned = new Set(pinnedTickers);
      const pinnedRows = rows.filter((r) => pinned.has(r.ticker));
      const unpinned = rows.filter((r) => !pinned.has(r.ticker));
      rows = [...pinnedRows, ...unpinned];
    }
    return rows;
  }, [signals, search, sectorFilter, sortField, sortDir, pinnedTickers]);

  const sortArrow = (field: SortField) => sortField === field ? (sortDir === "asc" ? " ↑" : " ↓") : "";

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Signal Grid</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={vix.extreme_fear ? "sell" : vix.regime === "normal" ? "buy" : "warning"}>
              VIX {vix.current_vix}
            </Badge>
            <span className="text-xs text-zinc-500">{new Date(updatedAt).toLocaleTimeString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <input
            type="text"
            placeholder="Search ticker..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 rounded-md bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="rounded-md bg-zinc-900 border border-zinc-800 px-2 py-1 text-xs focus:outline-none"
          >
            <option value="">All Sectors</option>
            {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {tooltip && (
          <div className="mb-2 text-xs text-zinc-400 bg-zinc-900 rounded p-2 border border-zinc-800">{tooltip}</div>
        )}
        <div className="overflow-auto max-h-[calc(100vh-320px)]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-zinc-950 z-10">
              <tr className="border-b border-zinc-800 text-zinc-400">
                {([
                  ["ticker", "text-left", "Ticker"],
                  ["price", "text-right", "Price"],
                  ["signal_direction", "text-center", "Signal"],
                  ["probability_score", "text-right", "Prob%"],
                  ["rsi_5", "text-right", "RSI5"],
                ] as [SortField, string, string][]).map(([field, align, label]) => (
                  <th
                    key={field}
                    className={`${align} py-2 px-2 font-medium cursor-pointer hover:text-white`}
                    onClick={() => handleSort(field)}
                    onMouseEnter={() => setTooltip(HEADER_TOOLTIPS[field === "probability_score" ? "prob" : field === "signal_direction" ? "signal" : field === "rsi_5" ? "rsi5" : field])}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    {label}{sortArrow(field)}
                  </th>
                ))}
                <th className="text-right py-2 px-2 font-medium" onMouseEnter={() => setTooltip(HEADER_TOOLTIPS.rsi9)} onMouseLeave={() => setTooltip(null)}>RSI9</th>
                <th className="text-right py-2 px-2 font-medium" onMouseEnter={() => setTooltip(HEADER_TOOLTIPS.rsi14)} onMouseLeave={() => setTooltip(null)}>RSI14</th>
                <th
                  className="text-right py-2 px-2 font-medium cursor-pointer hover:text-white"
                  onClick={() => handleSort("macd_zscore")}
                  onMouseEnter={() => setTooltip(HEADER_TOOLTIPS.macdz)}
                  onMouseLeave={() => setTooltip(null)}
                >
                  MACD-Z{sortArrow("macd_zscore")}
                </th>
                <th
                  className="text-right py-2 px-2 font-medium cursor-pointer hover:text-white"
                  onClick={() => handleSort("reversal_pct")}
                  onMouseEnter={() => setTooltip(HEADER_TOOLTIPS.reversal)}
                  onMouseLeave={() => setTooltip(null)}
                >
                  Rev%{sortArrow("reversal_pct")}
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.map((s) => {
                const isPinned = pinnedTickers.includes(s.ticker);
                return (
                  <tr
                    key={s.ticker}
                    onClick={() => onSelect(s.ticker)}
                    className={`border-b border-zinc-800/50 cursor-pointer transition-colors hover:bg-zinc-900 ${
                      selectedTicker === s.ticker ? "bg-zinc-800/60" : ""
                    } ${isPinned ? "border-l-2 border-l-amber-500" : ""} ${s.is_extreme_move ? "bg-red-950/20" : ""}`}
                  >
                    <td className="py-1.5 px-2 font-mono font-semibold text-xs">
                      {isPinned && <span className="text-amber-400 mr-1">★</span>}{s.ticker}
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono text-xs">${s.price.toFixed(2)}</td>
                    <td className="text-center py-1.5 px-2">
                      <Badge variant={directionVariant(s.signal_direction)}>{s.signal_direction.toUpperCase()}</Badge>
                    </td>
                    <td className={`text-right py-1.5 px-2 font-mono font-semibold text-xs ${probColor(s.probability_score)}`}>
                      {s.probability_score.toFixed(1)}
                    </td>
                    <td className={`text-right py-1.5 px-2 font-mono text-xs ${s.rsi_5 < 30 ? "text-emerald-400" : ""}`}>{s.rsi_5.toFixed(1)}</td>
                    <td className={`text-right py-1.5 px-2 font-mono text-xs ${s.rsi_9 < 35 ? "text-emerald-400" : ""}`}>{s.rsi_9.toFixed(1)}</td>
                    <td className={`text-right py-1.5 px-2 font-mono text-xs ${s.rsi_14 < 40 ? "text-emerald-400" : ""}`}>{s.rsi_14.toFixed(1)}</td>
                    <td className={`text-right py-1.5 px-2 font-mono text-xs ${
                      s.macd_zscore < -2 ? "text-emerald-400" : s.macd_zscore > 2 ? "text-red-400" : "text-zinc-400"
                    }`}>
                      {s.macd_zscore.toFixed(2)}{s.is_extreme_move && <span className="ml-1 text-red-400">!</span>}
                    </td>
                    <td className="text-right py-1.5 px-2 font-mono text-xs">{s.reversal_pct.toFixed(0)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="text-xs text-zinc-500 mt-2 text-right">{filteredAndSorted.length} of {signals.length} tickers</div>
      </CardContent>
    </Card>
  );
}
