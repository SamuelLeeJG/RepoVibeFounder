"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ThesisResponse } from "@/lib/types";

interface ThesisCardProps {
  thesis: ThesisResponse;
  onQuickTrade?: () => void;
}

export function ThesisCard({ thesis, onQuickTrade }: ThesisCardProps) {
  const { ticker, price, signal_direction, probability_score, why_now, macro_tailwind, risk_summary } = thesis;
  const { rsi, macd, vix, backtest, risk } = thesis;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-xl font-mono">{ticker}</CardTitle>
            <span className="text-2xl font-mono font-bold">${price.toFixed(2)}</span>
            <Badge variant={signal_direction === "buy" ? "buy" : signal_direction === "sell" ? "sell" : "neutral"}>
              {signal_direction.toUpperCase()}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="text-xs text-zinc-400">Probability</div>
              <div className={`text-2xl font-mono font-bold ${
                probability_score >= 60 ? "text-emerald-400" : probability_score >= 35 ? "text-amber-400" : "text-zinc-500"
              }`}>
                {probability_score.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Why Now */}
        <section>
          <h3 className="text-sm font-semibold text-emerald-400 mb-1">Why Now</h3>
          <p className="text-sm text-zinc-300">{why_now}</p>
        </section>

        {/* Macro Tailwind */}
        <section>
          <h3 className="text-sm font-semibold text-blue-400 mb-1">Macro Tailwind</h3>
          <p className="text-sm text-zinc-300">{macro_tailwind}</p>
        </section>

        {/* Risk */}
        <section>
          <h3 className="text-sm font-semibold text-amber-400 mb-1">Risk</h3>
          <p className="text-sm text-zinc-300">{risk_summary}</p>
        </section>

        {/* Technical Grid */}
        <div className="grid grid-cols-3 gap-3">
          {/* RSI Panel */}
          <div className="rounded-lg bg-zinc-900 p-3">
            <div className="text-xs text-zinc-400 mb-2">RSI Alignment</div>
            <div className="space-y-1 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">RSI(5)</span>
                <span className={rsi.rsi_5 < 30 ? "text-emerald-400" : ""}>{rsi.rsi_5}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">RSI(9)</span>
                <span className={rsi.rsi_9 < 35 ? "text-emerald-400" : ""}>{rsi.rsi_9}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">RSI(14)</span>
                <span className={rsi.rsi_14 < 40 ? "text-emerald-400" : ""}>{rsi.rsi_14}</span>
              </div>
              <div className="pt-1 border-t border-zinc-800">
                <Badge variant={rsi.active ? "buy" : "neutral"}>Phase {rsi.phase}</Badge>
              </div>
            </div>
          </div>

          {/* MACD Panel */}
          <div className="rounded-lg bg-zinc-900 p-3">
            <div className="text-xs text-zinc-400 mb-2">MACD Z-Score</div>
            <div className="space-y-1 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">Z-Score</span>
                <span className={
                  macd.zscore < -2 ? "text-emerald-400" : macd.zscore > 2 ? "text-red-400" : ""
                }>
                  {macd.zscore.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Hist</span>
                <span>{macd.macd_hist.toFixed(4)}</span>
              </div>
              <div className="pt-1 border-t border-zinc-800">
                <Badge variant={
                  macd.regime === "statistical_washout" ? "buy" : macd.regime === "exhaustion" ? "sell" : "neutral"
                }>
                  {macd.regime.replace("_", " ")}
                </Badge>
              </div>
            </div>
          </div>

          {/* VIX Panel */}
          <div className="rounded-lg bg-zinc-900 p-3">
            <div className="text-xs text-zinc-400 mb-2">VIX Context</div>
            <div className="space-y-1 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">VIX</span>
                <span>{vix.current_vix}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">RSI(2)</span>
                <span className={vix.vix_rsi2 > 90 ? "text-red-400" : ""}>{vix.vix_rsi2}</span>
              </div>
              <div className="pt-1 border-t border-zinc-800">
                <Badge variant={
                  vix.extreme_fear ? (vix.lower_high_confirmed ? "buy" : "sell") : "neutral"
                }>
                  {vix.regime.replace(/_/g, " ")}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Backtest Stats */}
        <div className="rounded-lg bg-zinc-900 p-3 flex items-center justify-between">
          <div>
            <span className="text-xs text-zinc-400">Backtest</span>
            <span className="ml-2 text-sm font-mono">
              {backtest.reversal_pct}% reversal rate
            </span>
            <span className="ml-2 text-xs text-zinc-500">
              ({backtest.sample_count} samples, avg +{backtest.avg_gain_pct}%)
            </span>
          </div>
          <div>
            <span className="text-xs text-zinc-400">Stop-Loss</span>
            <span className="ml-2 text-sm font-mono text-red-400">
              {risk.suggested_stop_loss_pct}%
            </span>
          </div>
        </div>

        {/* Quick Trade */}
        {signal_direction === "buy" && (
          <button
            onClick={onQuickTrade}
            className="w-full rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 transition-colors"
          >
            Quick-Trade $100 &middot; Stop at -{risk.suggested_stop_loss_pct}%
          </button>
        )}
        {signal_direction === "sell" && (
          <button
            onClick={onQuickTrade}
            className="w-full rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold py-3 transition-colors"
          >
            Quick-Sell &middot; Exhaustion Signal
          </button>
        )}
      </CardContent>
    </Card>
  );
}
