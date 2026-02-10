"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTickerEvents, useInsiderTrades, usePoliticianTrades } from "@/hooks/use-api";
import type { TickerEvent, InsiderTrade, PoliticianTrade } from "@/lib/types";

interface EventCalendarProps {
  ticker: string | null;
}

export function EventCalendar({ ticker }: EventCalendarProps) {
  const { data: events, loading: eventsLoading } = useTickerEvents(ticker);
  const { data: insiderTrades, loading: insiderLoading } = useInsiderTrades(ticker);
  const { data: politicianTrades, loading: politicianLoading } = usePoliticianTrades(ticker);

  if (!ticker) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-zinc-500">Select a ticker to view events</div>
        </CardContent>
      </Card>
    );
  }

  const loading = eventsLoading || insiderLoading || politicianLoading;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{ticker} Events & Activity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && <div className="text-zinc-500 text-sm">Loading events...</div>}

        {/* Earnings Events */}
        {events.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-blue-400 mb-2">Earnings Calendar</h3>
            <div className="space-y-2">
              {events.map((e, i) => (
                <EarningsRow key={i} event={e} />
              ))}
            </div>
          </section>
        )}

        {/* Insider Trades */}
        {insiderTrades.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-amber-400 mb-2">Insider Trades</h3>
            <div className="space-y-2 max-h-48 overflow-auto">
              {insiderTrades.slice(0, 10).map((t, i) => (
                <InsiderRow key={i} trade={t} />
              ))}
            </div>
          </section>
        )}

        {/* Politician Trades */}
        {politicianTrades.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-purple-400 mb-2">Politician Trades</h3>
            <div className="space-y-2 max-h-48 overflow-auto">
              {politicianTrades.slice(0, 10).map((t, i) => (
                <PoliticianRow key={i} trade={t} />
              ))}
            </div>
          </section>
        )}

        {!loading && events.length === 0 && insiderTrades.length === 0 && politicianTrades.length === 0 && (
          <div className="text-zinc-500 text-sm text-center py-4">
            No events data available. Configure API keys to enable.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EarningsRow({ event }: { event: TickerEvent }) {
  const details = (event.details || {}) as Record<string, string | number | null>;
  return (
    <div className="flex items-center justify-between rounded-lg bg-zinc-900 p-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant="info">Earnings</Badge>
        <span className="font-mono text-zinc-300">{event.event_date.slice(0, 10)}</span>
      </div>
      <div className="flex items-center gap-3 text-xs text-zinc-400">
        {details.eps_estimated != null && <span>Est EPS: ${String(details.eps_estimated)}</span>}
        {details.eps_actual != null && (
          <span className="text-emerald-400">Actual: ${String(details.eps_actual)}</span>
        )}
      </div>
    </div>
  );
}

function InsiderRow({ trade }: { trade: InsiderTrade }) {
  const isBuy = trade.transaction_type.toLowerCase().includes("purchase") ||
    trade.transaction_type.toLowerCase().includes("buy");
  return (
    <div className="flex items-center justify-between rounded-lg bg-zinc-900 p-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant={isBuy ? "buy" : "sell"}>
          {isBuy ? "BUY" : "SELL"}
        </Badge>
        <span className="text-zinc-300">{trade.name}</span>
      </div>
      <div className="flex items-center gap-3 text-xs font-mono">
        <span className="text-zinc-400">{trade.date.slice(0, 10)}</span>
        <span className={isBuy ? "text-emerald-400" : "text-red-400"}>
          ${trade.value.toLocaleString()}
        </span>
      </div>
    </div>
  );
}

function PoliticianRow({ trade }: { trade: PoliticianTrade }) {
  const isBuy = trade.transaction_type.toLowerCase().includes("purchase");
  return (
    <div className="flex items-center justify-between rounded-lg bg-zinc-900 p-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant={isBuy ? "buy" : "sell"}>
          {isBuy ? "BUY" : "SELL"}
        </Badge>
        <span className="text-zinc-300">{trade.politician}</span>
      </div>
      <div className="flex items-center gap-3 text-xs font-mono">
        <span className="text-zinc-400">{trade.date.slice(0, 10)}</span>
        <span className="text-zinc-300">{trade.amount}</span>
        <span className="text-zinc-500">{trade.source}</span>
      </div>
    </div>
  );
}
