"use client";

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

interface SignalGridProps {
  signals: SignalRow[];
  vix: VIXInfo;
  updatedAt: string;
  onSelect: (ticker: string) => void;
  selectedTicker: string | null;
}

export function SignalGrid({ signals, vix, updatedAt, onSelect, selectedTicker }: SignalGridProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Signal Grid</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={vix.extreme_fear ? "sell" : vix.regime === "normal" ? "buy" : "warning"}>
              VIX {vix.current_vix}
            </Badge>
            <span className="text-xs text-zinc-500">
              {new Date(updatedAt).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-auto max-h-[calc(100vh-220px)]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-zinc-950">
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="text-left py-2 px-2 font-medium">Ticker</th>
                <th className="text-right py-2 px-2 font-medium">Price</th>
                <th className="text-center py-2 px-2 font-medium">Signal</th>
                <th className="text-right py-2 px-2 font-medium">Prob %</th>
                <th className="text-right py-2 px-2 font-medium">RSI(5)</th>
                <th className="text-right py-2 px-2 font-medium">MACD-Z</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr
                  key={s.ticker}
                  onClick={() => onSelect(s.ticker)}
                  className={`border-b border-zinc-800/50 cursor-pointer transition-colors hover:bg-zinc-900 ${
                    selectedTicker === s.ticker ? "bg-zinc-800/60" : ""
                  }`}
                >
                  <td className="py-2 px-2 font-mono font-semibold">{s.ticker}</td>
                  <td className="text-right py-2 px-2 font-mono">${s.price.toFixed(2)}</td>
                  <td className="text-center py-2 px-2">
                    <Badge variant={directionVariant(s.signal_direction)}>
                      {s.signal_direction.toUpperCase()}
                    </Badge>
                  </td>
                  <td className={`text-right py-2 px-2 font-mono font-semibold ${probColor(s.probability_score)}`}>
                    {s.probability_score.toFixed(1)}
                  </td>
                  <td className="text-right py-2 px-2 font-mono">{s.rsi_5.toFixed(1)}</td>
                  <td className={`text-right py-2 px-2 font-mono ${
                    s.macd_zscore < -2 ? "text-emerald-400" : s.macd_zscore > 2 ? "text-red-400" : "text-zinc-400"
                  }`}>
                    {s.macd_zscore.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
