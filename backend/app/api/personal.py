"""Personal Intelligence Layer API.

All endpoints require a valid JWT (get_current_user dependency).
Every query filters by both tasks.id AND tasks.user_id — returning 404 on a
mismatch so the mere existence of another user's task is not disclosed.
"""

from __future__ import annotations

from typing import Annotated, Literal

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.tasks.personal_tasks import scan_and_extract_personal

router = APIRouter(prefix="/v1/personal", tags=["personal"])


# ─────────────────────────────────────────────────────────────────── schemas


class TaskOut(BaseModel):
    id: str
    description: str
    urgency_score: float | None
    urgency_band: str | None
    status: str
    deadline: str | None
    context_bundle: list | None
    source_reference: str
    source_label: str | None
    sender: str | None
    action_type: str | None
    created_at: str | None


class PatchTaskBody(BaseModel):
    status: Literal["open", "complete", "snoozed", "dismissed"]


class SummaryOut(BaseModel):
    high: int
    medium: int
    low: int
    total: int


# ─────────────────────────────────────────────────────────────────── helpers


def _row_to_task(row) -> TaskOut:
    return TaskOut(
        id=str(row.id),
        description=row.description,
        urgency_score=row.urgency_score,
        urgency_band=row.urgency_band,
        status=row.status,
        deadline=row.deadline.isoformat() if row.deadline else None,
        context_bundle=row.context_bundle,
        source_reference=row.source_reference,
        source_label=row.source_label,
        sender=row.sender,
        action_type=row.action_type,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


# ──────────────────────────────────────────────────────────────────── routes


@router.get("/tasks", response_model=dict)
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    status_filter: str | None = None,
):
    """Return the current user's tasks sorted by urgency score descending."""
    user_id = current_user["id"]

    query = sa.text(
        "SELECT id, description, urgency_score, urgency_band, status, deadline, "
        "       context_bundle, source_reference, source_label, sender, action_type, created_at "
        "FROM tasks "
        "WHERE user_id = :uid "
        + ("AND status = :status " if status_filter else "")
        + "ORDER BY urgency_score DESC NULLS LAST"
    )
    params: dict = {"uid": user_id}
    if status_filter:
        params["status"] = status_filter

    rows = db.execute(query, params).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    return {"tasks": [t.model_dump() for t in tasks], "count": len(tasks)}


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Return a single task with full context bundle.

    Returns 404 (not 403) on ownership mismatch — leaking existence is a
    disclosure risk.
    """
    row = db.execute(
        sa.text(
            "SELECT id, description, urgency_score, urgency_band, status, deadline, "
            "       context_bundle, source_reference, source_label, sender, action_type, created_at "
            "FROM tasks "
            "WHERE id = :id AND user_id = :uid"
        ),
        {"id": task_id, "uid": current_user["id"]},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return _row_to_task(row)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def patch_task(
    task_id: str,
    body: PatchTaskBody,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update the status of a task. Allowed values: open, complete, snoozed, dismissed."""
    row = db.execute(
        sa.text(
            "UPDATE tasks SET status = :status "
            "WHERE id = :id AND user_id = :uid "
            "RETURNING id, description, urgency_score, urgency_band, status, deadline, "
            "          context_bundle, source_reference, source_label, sender, action_type, created_at"
        ),
        {"status": body.status, "id": task_id, "uid": current_user["id"]},
    ).fetchone()
    db.commit()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return _row_to_task(row)


@router.post("/trigger")
def trigger_extraction(
    _: Annotated[dict, Depends(get_current_user)],
):
    """Manually kick off PIL extraction for all Slack/email files."""
    scan_and_extract_personal.delay()
    return {"status": "triggered"}


@router.get("/summary", response_model=SummaryOut)
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Task counts grouped by urgency band for the dashboard header."""
    rows = db.execute(
        sa.text(
            "SELECT urgency_band, COUNT(*) "
            "FROM tasks "
            "WHERE user_id = :uid AND status = 'open' "
            "GROUP BY urgency_band"
        ),
        {"uid": current_user["id"]},
    ).fetchall()

    counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for band, count in rows:
        if band in counts:
            counts[band] = count

    return SummaryOut(
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        total=sum(counts.values()),
    )
