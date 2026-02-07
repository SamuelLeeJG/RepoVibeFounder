"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TangencyResponse } from "@/lib/types";
import { useTangency } from "@/hooks/use-api";

const DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "JPM", "JNJ", "XOM"];

export function PortfolioVisualizer() {
  const [tickers] = useState<string[]>(DEFAULT_TICKERS);
  const { data, loading } = useTangency(tickers);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-zinc-500">Computing efficient frontier...</div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-zinc-500">Portfolio analysis requires at least 2 holdings</div>
        </CardContent>
      </Card>
    );
  }

  return <PortfolioChart data={data} />;
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

  // Capital Market Line: from (0, rf) to tangency
  const rf = 5; // 5%
  const cmlData = [
    { x: 0, y: rf },
    { x: tangencyPt.x * 1.5, y: rf + (tangencyPt.y - rf) / tangencyPt.x * tangencyPt.x * 1.5 },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Portfolio Tangency Visualizer</CardTitle>
          <div className="flex gap-2">
            <Badge variant="info">Sharpe: {data.current.sharpe}</Badge>
            <Badge variant="buy">Tangency: {data.tangency.sharpe}</Badge>
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
              {/* Efficient Frontier */}
              <Scatter name="Frontier" data={frontierData} fill="#3b82f6" line={{ stroke: "#3b82f6", strokeWidth: 2 }} lineType="fitting" />
              {/* Current Portfolio */}
              <Scatter name="Current" data={[currentPt]} fill="#f59e0b" shape="diamond" legendType="diamond">
                <circle r={8} />
              </Scatter>
              {/* Tangency Portfolio */}
              <Scatter name="Tangency" data={[tangencyPt]} fill="#10b981" shape="star" legendType="star">
                <circle r={8} />
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* CML Gap Analysis */}
        <div className="mt-4 rounded-lg bg-zinc-900 p-3 space-y-2">
          <div className="text-xs text-zinc-400 font-semibold">Rebalancing Suggestions</div>
          {Object.keys(data.rebalance_suggestion).length === 0 ? (
            <p className="text-sm text-zinc-500">Portfolio is near optimal allocation.</p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
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
