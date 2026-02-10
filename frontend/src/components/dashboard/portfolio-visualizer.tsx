"use client";

import { useState, useMemo } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TangencyResponse, BenchmarkData, PerfMetrics } from "@/lib/types";
import { useTangency } from "@/hooks/use-api";

const DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "JPM", "JNJ", "XOM"];
const MAX_POSITION_PCT = 25;
const MAX_POSITIONS = 30;

interface PortfolioVisualizerProps {
  initialTickers?: string[];
  benchmark?: BenchmarkData | null;
}

export function PortfolioVisualizer({ initialTickers, benchmark }: PortfolioVisualizerProps) {
  const [tickers, setTickers] = useState<string[]>(initialTickers ?? DEFAULT_TICKERS);
  const [newTicker, setNewTicker] = useState("");
  const [error, setError] = useState("");
  const { data, loading } = useTangency(tickers);

  const addTicker = () => {
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    if (tickers.includes(t)) { setError(`${t} already in portfolio`); return; }
    if (tickers.length >= MAX_POSITIONS) { setError(`Max ${MAX_POSITIONS} positions`); return; }
    setTickers([...tickers, t]);
    setNewTicker("");
    setError("");
  };

  const removeTicker = (t: string) => {
    setTickers(tickers.filter((x) => x !== t));
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-zinc-500">Computing efficient frontier...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Holdings Management */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Portfolio Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-3">
            <input
              type="text"
              placeholder="Add ticker..."
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTicker()}
              className="flex-1 rounded-md bg-zinc-900 border border-zinc-800 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <button
              onClick={addTicker}
              className="px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-sm transition-colors"
            >
              Add
            </button>
          </div>
          {error && <div className="text-red-400 text-xs mb-2">{error}</div>}
          <div className="flex flex-wrap gap-2">
            {tickers.map((t) => {
              const weight = data?.current.weights[t];
              const tgtWeight = data?.tangency.weights[t];
              return (
                <div key={t} className="flex items-center gap-1 bg-zinc-900 rounded-md px-2 py-1 text-xs font-mono">
                  <span className="font-semibold">{t}</span>
                  {weight != null && (
                    <span className="text-zinc-500">{(weight * 100).toFixed(1)}%</span>
                  )}
                  {tgtWeight != null && weight != null && Math.abs(tgtWeight - weight) > 0.01 && (
                    <span className={tgtWeight > weight ? "text-emerald-400" : "text-red-400"}>
                      {tgtWeight > weight ? "+" : ""}{((tgtWeight - weight) * 100).toFixed(1)}%
                    </span>
                  )}
                  <button
                    onClick={() => removeTicker(t)}
                    className="ml-1 text-zinc-500 hover:text-red-400 transition-colors"
                  >
                    x
                  </button>
                </div>
              );
            })}
          </div>
          <div className="mt-2 text-xs text-zinc-500">
            {tickers.length} holdings | Max position: {MAX_POSITION_PCT}% | No shorts
          </div>
        </CardContent>
      </Card>

      {/* Efficient Frontier Chart */}
      {data && <PortfolioChart data={data} />}

      {/* Benchmark Comparison */}
      {benchmark && <BenchmarkCard benchmark={benchmark} />}

      {/* No data state */}
      {!data && !loading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-zinc-500">Add at least 2 tickers for portfolio analysis</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function PortfolioChart({ data }: { data: TangencyResponse }) {
  const frontierData = data.frontier.map((p) => ({
    x: +(p.volatility * 100).toFixed(2),
    y: +(p.expected_return * 100).toFixed(2),
    type: "frontier",
  }));

  const currentPt = {
    x: +(data.current.volatility * 100).toFixed(2),
    y: +(data.current.expected_return * 100).toFixed(2),
    type: "current",
  };

  const tangencyPt = {
    x: +(data.tangency.volatility * 100).toFixed(2),
    y: +(data.tangency.expected_return * 100).toFixed(2),
    type: "tangency",
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Efficient Frontier</CardTitle>
          <div className="flex gap-2">
            <Badge variant="info">Current Sharpe: {data.current.sharpe}</Badge>
            <Badge variant="buy">Tangency Sharpe: {data.tangency.sharpe}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis
                type="number"
                dataKey="x"
                name="Volatility"
                unit="%"
                tick={{ fontSize: 10, fill: "#71717a" }}
                label={{ value: "Risk (Volatility %)", position: "insideBottom", offset: -5, fill: "#71717a", fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Return"
                unit="%"
                tick={{ fontSize: 10, fill: "#71717a" }}
                label={{ value: "Return %", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any, name: any) => [`${value}%`, name]}
              />
              <Scatter name="Frontier" data={frontierData} fill="#3b82f6" line={{ stroke: "#3b82f6", strokeWidth: 2 }} lineType="fitting" />
              <Scatter name="Current" data={[currentPt]} fill="#f59e0b" shape="diamond" legendType="diamond" />
              <Scatter name="Tangency" data={[tangencyPt]} fill="#10b981" shape="star" legendType="star" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Rebalancing Suggestions */}
        <div className="mt-4 rounded-lg bg-zinc-900 p-3 space-y-2">
          <div className="text-xs text-zinc-400 font-semibold">Rebalancing Suggestions</div>
          {Object.keys(data.rebalance_suggestion).length === 0 ? (
            <p className="text-sm text-zinc-500">Portfolio is near optimal allocation.</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {Object.entries(data.rebalance_suggestion).map(([ticker, delta]) => (
                <div key={ticker} className="flex justify-between text-sm font-mono">
                  <span>{ticker}</span>
                  <span className={delta > 0 ? "text-emerald-400" : "text-red-400"}>
                    {delta > 0 ? "+" : ""}{delta.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function BenchmarkCard({ benchmark }: { benchmark: BenchmarkData }) {
  const metrics = [benchmark.portfolio, benchmark.spy, benchmark.qqq].filter(Boolean) as PerfMetrics[];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Benchmark Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="text-left py-2 px-2 font-medium">Metric</th>
                {metrics.map((m) => (
                  <th key={m.name} className="text-right py-2 px-2 font-medium">{m.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {([
                ["Total Return", "total_return_pct"],
                ["Ann. Return", "annualized_return_pct"],
                ["Ann. Vol", "annualized_vol_pct"],
                ["Sharpe", "sharpe_ratio"],
                ["Max DD", "max_drawdown_pct"],
              ] as [string, keyof PerfMetrics][]).map(([label, key]) => (
                <tr key={key} className="border-b border-zinc-800/50">
                  <td className="py-1.5 px-2 text-zinc-400">{label}</td>
                  {metrics.map((m) => {
                    const val = m[key] as number;
                    const isNeg = key === "max_drawdown_pct" || val < 0;
                    return (
                      <td key={m.name} className={`text-right py-1.5 px-2 font-mono ${isNeg ? "text-red-400" : "text-emerald-400"}`}>
                        {key === "sharpe_ratio" ? val.toFixed(2) : `${val.toFixed(1)}%`}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
