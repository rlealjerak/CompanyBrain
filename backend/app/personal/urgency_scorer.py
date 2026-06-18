"""Urgency scoring for PIL tasks.

Starts with Claude's raw score (1-10) and applies bonuses and decay
before clamping to [1, 10] and assigning a band.
"""

from __future__ import annotations

from datetime import datetime, timezone


def score_urgency(
    raw_score: float,
    deadline_str: str | None,
    explicitly_named: bool,
    sender_is_manager: bool,
    created_at: datetime | None = None,
) -> tuple[float, str]:
    """Return (final_score, band) where band is 'high', 'medium', or 'low'.

    Bonuses applied on top of raw_score:
      +2.0  deadline within 24 h
      +1.5  deadline within 3 days
      +1.0  deadline within 7 days
      +1.0  user explicitly named/mentioned
      +1.0  sender is in a management/leadership role

    Decay:
      -0.5/day for each day beyond 3 that the task has gone unactioned.

    Final score is clamped to [1, 10].
    Bands: high = 8–10, medium = 5–7, low = 1–4.
    """
    score = float(raw_score)
    now = datetime.now(timezone.utc)

    if deadline_str:
        try:
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            hours_until = (deadline - now).total_seconds() / 3600
            if hours_until <= 24:
                score += 2.0
            elif hours_until <= 72:
                score += 1.5
            elif hours_until <= 168:
                score += 1.0
        except (ValueError, TypeError):
            pass

    if explicitly_named:
        score += 1.0

    if sender_is_manager:
        score += 1.0

    if created_at is not None:
        days_old = max(0, (now - created_at).days)
        if days_old > 3:
            score -= 0.5 * (days_old - 3)

    score = max(1.0, min(10.0, score))

    if score >= 8.0:
        band = "high"
    elif score >= 5.0:
        band = "medium"
    else:
        band = "low"

    return score, band
