"use client";

import { Badge } from "@/components/ui/badge";
import type { VIXInfo } from "@/lib/types";

interface VIXBannerProps {
  vix: VIXInfo;
}

export function VIXBanner({ vix }: VIXBannerProps) {
  const bgColor = vix.extreme_fear
    ? "bg-red-950/50 border-red-800/50"
    : vix.regime === "elevated"
    ? "bg-amber-950/50 border-amber-800/50"
    : "bg-zinc-900 border-zinc-800";

  return (
    <div className={`rounded-lg border px-4 py-2 flex items-center justify-between ${bgColor}`}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400">VIX</span>
          <span className="font-mono font-bold text-lg">{vix.current_vix}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400">RSI(2)</span>
          <span className="font-mono">{vix.vix_rsi2}</span>
        </div>
        <Badge
          variant={
            vix.extreme_fear
              ? vix.lower_high_confirmed
                ? "buy"
                : "sell"
              : "neutral"
          }
        >
          {vix.regime.replace(/_/g, " ").toUpperCase()}
        </Badge>
        {vix.lower_high_confirmed && (
          <Badge variant="buy">Lower High Confirmed</Badge>
        )}
      </div>
      <div className="text-xs text-zinc-400 max-w-md text-right">{vix.recommendation}</div>
    </div>
  );
}
