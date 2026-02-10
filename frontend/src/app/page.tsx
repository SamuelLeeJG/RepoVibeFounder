"use client";

import { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SignalGrid } from "@/components/dashboard/signal-grid";
import { ThesisCard } from "@/components/dashboard/thesis-card";
import { AnalysisPane } from "@/components/dashboard/analysis-pane";
import { PortfolioVisualizer } from "@/components/dashboard/portfolio-visualizer";
import { VIXBanner } from "@/components/dashboard/vix-banner";
import { EventCalendar } from "@/components/dashboard/event-calendar";
import { NewsPanel } from "@/components/dashboard/news-panel";
import { LoginForm } from "@/components/dashboard/login-form";
import { NotificationCenter } from "@/components/dashboard/notification-center";
import {
  useSignalGrid, useThesis, useChartData, useAuth,
  useNotifications, useSectors, exportSignalsCSV,
} from "@/hooks/use-api";

export default function Dashboard() {
  const { user, loading: authLoading, login, register, requestAccess, resetPassword, logout } = useAuth();
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState("1Day_6M");
  const [search, setSearch] = useState<string | undefined>();
  const [sectorFilter, setSectorFilter] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState("probability_score");
  const [sortDir, setSortDir] = useState("desc");

  const { data: gridData, loading: gridLoading, refetch } = useSignalGrid(
    undefined, 20, search, sectorFilter, sortBy, sortDir,
  );
  const { data: thesis, loading: thesisLoading } = useThesis(selectedTicker);
  const { data: chartData, loading: chartLoading } = useChartData(selectedTicker, timeframe);
  const sectors = useSectors();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications(user?.id ?? null);

  const pinnedTickers = user?.pinned_tickers ?? [];

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#09090b] text-zinc-500">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-4 sm:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-base sm:text-lg font-semibold tracking-tight">
            Alpha-Beta<span className="text-zinc-500 hidden sm:inline"> Decision Intelligence Terminal</span>
          </h1>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/50 text-emerald-400 font-mono">v2.1</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          {user && (
            <span className="text-xs text-zinc-400">
              {user.display_name}
              {user.role === "admin" && <span className="ml-1 text-amber-400">(admin)</span>}
            </span>
          )}
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={() => exportSignalsCSV()}
            className="text-xs px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors"
          >
            CSV
          </button>
          <NotificationCenter
            notifications={notifications}
            unreadCount={unreadCount}
            onMarkRead={markRead}
            onMarkAllRead={markAllRead}
          />
          <div className="text-xs text-zinc-500 font-mono">
            {gridData?.updated_at
              ? new Date(gridData.updated_at).toLocaleTimeString()
              : "--:--:--"}
          </div>
          {user && (
            <button
              onClick={logout}
              className="text-xs px-2 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors text-zinc-400"
            >
              Logout
            </button>
          )}
        </div>
      </header>

      {/* VIX Banner */}
      {gridData?.vix && (
        <div className="px-4 sm:px-6 pt-3">
          <VIXBanner vix={gridData.vix} />
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 px-4 sm:px-6 py-4">
        <Tabs defaultValue="signals" className="h-full">
          <TabsList className="flex-wrap">
            <TabsTrigger value="signals">Signals + Analysis</TabsTrigger>
            <TabsTrigger value="events">Events & Insiders</TabsTrigger>
            <TabsTrigger value="portfolio">Portfolio Optimizer</TabsTrigger>
          </TabsList>

          {/* Signals Tab */}
          <TabsContent value="signals">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mt-2">
              {/* Signal Grid — left panel */}
              <div className="lg:col-span-4">
                {gridLoading ? (
                  <div className="flex items-center justify-center h-64 text-zinc-500">
                    Loading signals...
                  </div>
                ) : gridData ? (
                  <SignalGrid
                    signals={gridData.signals}
                    vix={gridData.vix}
                    updatedAt={gridData.updated_at}
                    onSelect={setSelectedTicker}
                    selectedTicker={selectedTicker}
                    pinnedTickers={pinnedTickers}
                    sectors={sectors}
                  />
                ) : (
                  <div className="text-zinc-500">Failed to load signals</div>
                )}
              </div>

              {/* Analysis + Thesis + News — right panel */}
              <div className="lg:col-span-8 space-y-4">
                {/* Chart */}
                <AnalysisPane
                  data={chartData}
                  ticker={selectedTicker || ""}
                  loading={chartLoading}
                  timeframe={timeframe}
                  onTimeframeChange={setTimeframe}
                />

                {/* Thesis Card */}
                {thesisLoading && (
                  <div className="text-zinc-500 text-center py-4">Generating thesis...</div>
                )}
                {thesis && (
                  <ThesisCard
                    thesis={thesis}
                    onQuickTrade={() => {
                      alert(
                        `Quick-Trade: ${thesis.signal_direction.toUpperCase()} $100 of ${thesis.ticker} with stop-loss at -${thesis.risk.suggested_stop_loss_pct}%`
                      );
                    }}
                  />
                )}

                {/* News Panel */}
                <NewsPanel ticker={selectedTicker} />
              </div>
            </div>
          </TabsContent>

          {/* Events & Insiders Tab */}
          <TabsContent value="events">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mt-2">
              <div className="lg:col-span-4">
                {gridData && (
                  <SignalGrid
                    signals={gridData.signals}
                    vix={gridData.vix}
                    updatedAt={gridData.updated_at}
                    onSelect={setSelectedTicker}
                    selectedTicker={selectedTicker}
                    pinnedTickers={pinnedTickers}
                    sectors={sectors}
                  />
                )}
              </div>
              <div className="lg:col-span-8">
                <EventCalendar ticker={selectedTicker} />
              </div>
            </div>
          </TabsContent>

          {/* Portfolio Tab */}
          <TabsContent value="portfolio">
            <div className="mt-2">
              <PortfolioVisualizer />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
