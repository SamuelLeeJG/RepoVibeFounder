"""In-app notification service — triggers on Phase 3, shocks, earnings, extreme moves."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Notification:
    id: str
    user_id: str
    ticker: str
    notification_type: str  # phase3_trigger | shock_event | earnings_soon | extreme_move | threshold_90pct
    title: str
    message: str
    severity: str  # info | warning | critical
    created_at: str
    read: bool = False
    data: dict = field(default_factory=dict)


class NotificationService:
    """In-memory notification store (upgradeable to DB/Redis later).

    Generates notifications when signals fire for a user's pinned tickers.
    """

    def __init__(self, max_per_user: int = 100):
        self._notifications: dict[str, list[Notification]] = defaultdict(list)
        self.max_per_user = max_per_user

    def add(
        self,
        user_id: str,
        ticker: str,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
        data: dict | None = None,
    ) -> Notification:
        """Add a notification for a user."""
        n = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            ticker=ticker,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            data=data or {},
        )
        self._notifications[user_id].append(n)
        # Trim old notifications
        if len(self._notifications[user_id]) > self.max_per_user:
            self._notifications[user_id] = self._notifications[user_id][-self.max_per_user:]
        return n

    def get_unread(self, user_id: str) -> list[dict]:
        """Get all unread notifications for a user."""
        return [self._to_dict(n) for n in self._notifications.get(user_id, []) if not n.read]

    def get_all(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get all notifications for a user (newest first)."""
        notes = self._notifications.get(user_id, [])
        return [self._to_dict(n) for n in reversed(notes[-limit:])]

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a single notification as read."""
        for n in self._notifications.get(user_id, []):
            if n.id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_read(self, user_id: str):
        """Mark all notifications as read for a user."""
        for n in self._notifications.get(user_id, []):
            n.read = True

    def unread_count(self, user_id: str) -> int:
        """Count unread notifications."""
        return sum(1 for n in self._notifications.get(user_id, []) if not n.read)

    def check_and_notify_signals(
        self,
        user_id: str,
        pinned_tickers: list[str],
        signal_data: dict,
    ):
        """Check signal data and generate notifications for pinned tickers.

        signal_data should contain keys like:
        - 'phase3_triggers': list of tickers with active Phase 3
        - 'shock_events': list of {ticker, severity, direction}
        - 'extreme_moves': list of {ticker, period, direction, z_score}
        - 'threshold_90pct': list of {ticker, reversal_rate}
        - 'upcoming_earnings': list of {ticker, days_until, signal_strength}
        """
        if not pinned_tickers:
            return

        pinned_set = set(pinned_tickers)

        for ticker in signal_data.get("phase3_triggers", []):
            if ticker in pinned_set:
                # Deduplicate: don't send same alert within 1 hour
                if not self._recent_alert(user_id, ticker, "phase3_trigger", hours=1):
                    self.add(
                        user_id, ticker, "phase3_trigger",
                        f"{ticker} Phase 3 Triggered",
                        f"RSI Triple-Alignment Phase 3 active — buy signal confirmed for {ticker}.",
                        severity="critical",
                    )

        for shock in signal_data.get("shock_events", []):
            ticker = shock.get("ticker", "")
            if ticker in pinned_set:
                if not self._recent_alert(user_id, ticker, "shock_event", hours=1):
                    self.add(
                        user_id, ticker, "shock_event",
                        f"{ticker} MACD Velocity Shock",
                        f"{shock.get('severity', 'moderate').title()} {shock.get('direction', '')} shock detected.",
                        severity="warning" if shock.get("severity") == "moderate" else "critical",
                        data=shock,
                    )

        for move in signal_data.get("extreme_moves", []):
            ticker = move.get("ticker", "")
            if ticker in pinned_set:
                if not self._recent_alert(user_id, ticker, "extreme_move", hours=4):
                    self.add(
                        user_id, ticker, "extreme_move",
                        f"{ticker} Extreme MACD Move",
                        f"{move.get('period', '1d')} MACD histogram {move.get('direction', 'move')}: "
                        f"Z-score {move.get('z_score', 0):.1f}",
                        severity="warning",
                        data=move,
                    )

        for threshold in signal_data.get("threshold_90pct", []):
            ticker = threshold.get("ticker", "")
            if ticker in pinned_set:
                if not self._recent_alert(user_id, ticker, "threshold_90pct", hours=4):
                    self.add(
                        user_id, ticker, "threshold_90pct",
                        f"{ticker} 90% Reversal Threshold",
                        f"Historical reversal rate at current Z-level: {threshold.get('reversal_rate', 0):.1f}%",
                        severity="critical",
                    )

        for earnings in signal_data.get("upcoming_earnings", []):
            ticker = earnings.get("ticker", "")
            if ticker in pinned_set:
                days = earnings.get("days_until", 99)
                if days <= 7 and not self._recent_alert(user_id, ticker, "earnings_soon", hours=24):
                    self.add(
                        user_id, ticker, "earnings_soon",
                        f"{ticker} Earnings in {days} day(s)",
                        f"Earnings date approaching with signal strength: {earnings.get('signal_strength', 0)}",
                        severity="info",
                    )

    def _recent_alert(self, user_id: str, ticker: str, ntype: str, hours: int) -> bool:
        """Check if a similar notification was sent recently."""
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)).isoformat()
        for n in self._notifications.get(user_id, []):
            if n.ticker == ticker and n.notification_type == ntype and n.created_at > cutoff:
                return True
        return False

    def _to_dict(self, n: Notification) -> dict:
        return {
            "id": n.id,
            "ticker": n.ticker,
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "created_at": n.created_at,
            "read": n.read,
            "data": n.data,
        }


# Singleton instance
notification_service = NotificationService()
