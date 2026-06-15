from __future__ import annotations

from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.tasks.brain_tasks import ingest_file, scan_and_ingest

# require_admin applied at router level — every route in this file is admin-only
router = APIRouter(
    prefix="/v1/ingest",
    tags=["ingest"],
    dependencies=[Depends(require_admin)],
)


class TriggerRequest(BaseModel):
    source: str | None = None  # relative path under data/raw/; None = scan all


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
def trigger(body: TriggerRequest):
    if body.source:
        ingest_file.delay(body.source)
        return {"status": "enqueued", "source": body.source}
    scan_and_ingest.delay()
    return {"status": "enqueued", "source": "all"}


@router.get("/jobs")
def list_jobs(db: Annotated[Session, Depends(get_db)], limit: int = 50):
    rows = db.execute(
        sa.text(
            "SELECT id, source_id, status, locked_at, attempt_number, error_message "
            "FROM ingestion_jobs ORDER BY locked_at DESC LIMIT :limit"
        ),
        {"limit": limit},
    ).fetchall()

    return {
        "jobs": [
            {
                "id": str(r[0]),
                "source_id": r[1],
                "status": r[2],
                "locked_at": r[3].isoformat() if r[3] else None,
                "attempt_number": r[4],
                "error_message": r[5],
            }
            for r in rows
        ]
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Annotated[Session, Depends(get_db)]):
    row = db.execute(
        sa.text(
            "SELECT id, source_id, status, locked_at, attempt_number, error_message "
            "FROM ingestion_jobs WHERE id = :id"
        ),
        {"id": job_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return {
        "id": str(row[0]),
        "source_id": row[1],
        "status": row[2],
        "locked_at": row[3].isoformat() if row[3] else None,
        "attempt_number": row[4],
        "error_message": row[5],
    }
