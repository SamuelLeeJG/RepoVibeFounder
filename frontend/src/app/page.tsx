"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SignalGrid } from "@/components/dashboard/signal-grid";
import { ThesisCard } from "@/components/dashboard/thesis-card";
import { AnalysisPane } from "@/components/dashboard/analysis-pane";
import { PortfolioVisualizer } from "@/components/dashboard/portfolio-visualizer";
import { VIXBanner } from "@/components/dashboard/vix-banner";
import { EventCalendar } from "@/components/dashboard/event-calendar";
import { NewsPanel } from "@/components/dashboard/news-panel";
import { LoginForm } from "@/components/dashboard/login-form";
import { useSignalGrid, useThesis, useChartData, useAuth } from "@/hooks/use-api";

export default function Dashboard() {
  const { user, loading: authLoading, login, register, logout } = useAuth();
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const { data: gridData, loading: gridLoading, refetch } = useSignalGrid(undefined, 20);
  const { data: thesis, loading: thesisLoading } = useThesis(selectedTicker);
  const { data: chartData, loading: chartLoading } = useChartData(selectedTicker);

  // Show login form if auth is configured but user isn't logged in
  // For now, auth is optional — skip if no backend auth is available
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
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">
            Alpha-Beta<span className="text-zinc-500"> Decision Intelligence Terminal</span>
          </h1>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/50 text-emerald-400 font-mono">v2.0</span>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-xs text-zinc-400">
              {user.display_name}
              {user.role === "admin" && (
                <span className="ml-1 text-amber-400">(admin)</span>
              )}
            </span>
          )}
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors"
          >
            Refresh Signals
          </button>
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
        <div className="px-6 pt-3">
          <VIXBanner vix={gridData.vix} />
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 px-6 py-4">
        <Tabs defaultValue="signals" className="h-full">
          <TabsList>
            <TabsTrigger value="signals">Signals + Analysis</TabsTrigger>
            <TabsTrigger value="events">Events & Insiders</TabsTrigger>
            <TabsTrigger value="portfolio">Portfolio Optimizer</TabsTrigger>
          </TabsList>

          {/* Signals Tab */}
          <TabsContent value="signals">
            <div className="grid grid-cols-12 gap-4 mt-2">
              {/* Signal Grid — left panel */}
              <div className="col-span-4">
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
                  />
                ) : (
                  <div className="text-zinc-500">Failed to load signals</div>
                )}
              </div>

              {/* Analysis + Thesis + News — right panel */}
              <div className="col-span-8 space-y-4">
                {/* Chart */}
                <AnalysisPane
                  data={chartData}
                  ticker={selectedTicker || ""}
                  loading={chartLoading}
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
            <div className="grid grid-cols-12 gap-4 mt-2">
              <div className="col-span-4">
                {gridData && (
                  <SignalGrid
                    signals={gridData.signals}
                    vix={gridData.vix}
                    updatedAt={gridData.updated_at}
                    onSelect={setSelectedTicker}
                    selectedTicker={selectedTicker}
                  />
                )}
              </div>
              <div className="col-span-8">
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
