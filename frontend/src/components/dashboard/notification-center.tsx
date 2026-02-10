"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Notification } from "@/lib/types";

interface NotificationCenterProps {
  notifications: Notification[];
  unreadCount: number;
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
}

function severityColor(severity: string) {
  if (severity === "critical") return "text-red-400 bg-red-950/30";
  if (severity === "warning") return "text-amber-400 bg-amber-950/30";
  return "text-blue-400 bg-blue-950/30";
}

function typeIcon(type: string) {
  if (type === "phase3_trigger") return "P3";
  if (type === "macd_extreme") return "MX";
  if (type === "earnings_approaching") return "ER";
  if (type === "shock_detected") return "!!";
  return "i";
}

export function NotificationCenter({ notifications, unreadCount, onMarkRead, onMarkAllRead }: NotificationCenterProps) {
  const [expanded, setExpanded] = useState(false);

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="relative px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs transition-colors"
      >
        Alerts
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end pt-14 pr-4">
      <div className="absolute inset-0 bg-black/30" onClick={() => setExpanded(false)} />
      <Card className="relative z-10 w-96 max-h-[70vh] flex flex-col shadow-xl">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Notifications</CardTitle>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={onMarkAllRead}
                  className="text-xs text-emerald-400 hover:underline"
                >
                  Mark all read
                </button>
              )}
              <button
                onClick={() => setExpanded(false)}
                className="text-zinc-500 hover:text-white text-lg"
              >
                x
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="overflow-auto flex-1">
          {notifications.length === 0 ? (
            <div className="text-zinc-500 text-sm text-center py-8">No notifications yet</div>
          ) : (
            <div className="space-y-2">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.read && onMarkRead(n.id)}
                  className={`rounded-lg p-3 cursor-pointer transition-colors ${
                    n.read ? "bg-zinc-900/50" : "bg-zinc-900 border border-zinc-800"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${severityColor(n.severity)}`}>
                      {typeIcon(n.type)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold font-mono">{n.ticker}</span>
                        <span className="text-xs text-zinc-500">{n.title}</span>
                        {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />}
                      </div>
                      <p className="text-xs text-zinc-400 mt-0.5 line-clamp-2">{n.message}</p>
                      <div className="text-[10px] text-zinc-600 mt-1">
                        {new Date(n.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
