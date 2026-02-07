"use client";

import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ChartBar } from "@/lib/types";

interface AnalysisPaneProps {
  data: ChartBar[];
  ticker: string;
  loading: boolean;
}

export function AnalysisPane({ data, ticker, loading }: AnalysisPaneProps) {
  if (loading) {
    return (
      <Card className="h-full flex items-center justify-center">
        <div className="text-zinc-500">Loading chart data...</div>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card className="h-full flex items-center justify-center">
        <div className="text-zinc-500">Select a ticker to view analysis</div>
      </Card>
    );
  }

  // Take last 200 bars for readability
  const chartData = data.slice(-200).map((b) => ({
    ...b,
    time: b.timestamp.slice(5, 16).replace("T", " "),
  }));

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-mono">{ticker} Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="price">
          <TabsList>
            <TabsTrigger value="price">Price + BB</TabsTrigger>
            <TabsTrigger value="rsi">RSI 5/9/14</TabsTrigger>
            <TabsTrigger value="macd">MACD Z-Score</TabsTrigger>
          </TabsList>

          {/* Price + Bollinger Band */}
          <TabsContent value="price" className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#71717a" }} interval="preserveStartEnd" />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#71717a" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
                  labelStyle={{ color: "#a1a1aa" }}
                />
                <Area type="monotone" dataKey="bb_lower" stroke="none" fill="#3b82f6" fillOpacity={0.08} name="BB Lower" />
                <Line type="monotone" dataKey="close" stroke="#e4e4e7" dot={false} strokeWidth={1.5} name="Close" />
                <Line type="monotone" dataKey="bb_lower" stroke="#3b82f6" dot={false} strokeWidth={1} strokeDasharray="4 2" name="BB Lower" />
                {/* Highlight phase-3 bars */}
                <Bar dataKey={(d: Record<string, unknown>) => (d.phase3 ? d.close : null)} fill="#10b981" opacity={0.3} name="Signal" />
              </ComposedChart>
            </ResponsiveContainer>
          </TabsContent>

          {/* RSI Panel */}
          <TabsContent value="rsi" className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#71717a" }} interval="preserveStartEnd" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#71717a" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
                  labelStyle={{ color: "#a1a1aa" }}
                />
                <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" label={{ value: "30", fill: "#10b981", fontSize: 10 }} />
                <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "70", fill: "#ef4444", fontSize: 10 }} />
                <Line type="monotone" dataKey="rsi_5" stroke="#f59e0b" dot={false} strokeWidth={1.5} name="RSI(5)" />
                <Line type="monotone" dataKey="rsi_9" stroke="#8b5cf6" dot={false} strokeWidth={1.5} name="RSI(9)" />
                <Line type="monotone" dataKey="rsi_14" stroke="#06b6d4" dot={false} strokeWidth={1.5} name="RSI(14)" />
                <Legend />
              </ComposedChart>
            </ResponsiveContainer>
          </TabsContent>

          {/* MACD Z-Score */}
          <TabsContent value="macd" className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#71717a" }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: "#71717a" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
                  labelStyle={{ color: "#a1a1aa" }}
                />
                <ReferenceLine y={-2} stroke="#10b981" strokeDasharray="3 3" label={{ value: "-2 SD", fill: "#10b981", fontSize: 10 }} />
                <ReferenceLine y={2} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "+2 SD", fill: "#ef4444", fontSize: 10 }} />
                <ReferenceLine y={0} stroke="#3f3f46" />
                <Bar dataKey="macd_hist" name="MACD Hist">
                  {chartData.map((entry, index) => {
                    const color = entry.macd_hist >= 0 ? "#10b981" : "#ef4444";
                    return <rect key={index} fill={color} />;
                  })}
                </Bar>
                <Line type="monotone" dataKey="hist_zscore" stroke="#f59e0b" dot={false} strokeWidth={2} name="Z-Score" />
                <Legend />
              </ComposedChart>
            </ResponsiveContainer>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
