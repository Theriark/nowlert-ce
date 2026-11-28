"""Severity words grouped the way notification cards and filters show them.

The Discord and Teams card headers put an event in the Resolved, Critical or
Warning bucket (anything else reads as Information), and the Delivery history
severity filter groups the same words. All of them use these sets, so a word
added here changes the cards and the filter together.
"""

from __future__ import annotations

RESOLVED_WORDS = frozenset({
    "cleared", "normal", "ok", "recovered", "resolved", "success", "successful",
})
CRITICAL_WORDS = frozenset({
    "critical", "danger", "disaster", "emergency", "error", "failed", "failure", "high",
})
WARNING_WORDS = frozenset({
    "alert", "average", "caution", "degraded", "medium", "warn", "warning",
})
INFORMATION_WORDS = frozenset({"information", "informational", "info"})
