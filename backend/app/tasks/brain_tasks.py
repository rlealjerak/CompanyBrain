"""Celery tasks for the Company Brain ingestion pipeline."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa

from app.celery_app import celery_app
from app.core.config import settings, validate_ai_keys
from app.core.database import get_db
from app.pipeline.ingestion import (
    claim_job,
    mark_job_retrying,
    needs_ingestion,
    release_job,
    run_file_pipeline,
)

log = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".md", ".json"}


def _raw_dir() -> Path:
    return Path(settings.data_dir) / "raw"


def _file_source_id(path: Path) -> str:
    """Stable identifier for a file — used as the ingestion_jobs.source_id."""
    try:
        return str(path.relative_to(_raw_dir()))
    except ValueError:
        return str(path)


# ──────────────────────────────────────────────────────────────────────── tasks


@celery_app.task(name="app.tasks.brain_tasks.scan_and_ingest")
def scan_and_ingest() -> dict:
    """Scan data/raw/ and enqueue ingest_file for every file that needs ingestion.

    Called by Celery Beat every 5 minutes.  Returns a summary dict so the
    result can be inspected in the Celery result backend.
    """
    raw_dir = _raw_dir()
    if not raw_dir.exists():
        log.warning("Data directory not found: %s", raw_dir)
        return {"enqueued": 0, "skipped": 0}

    enqueued = 0
    skipped = 0

    db_gen = get_db()
    db = next(db_gen)
    try:
        for path in sorted(raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue

            file_source_id = _file_source_id(path)
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

            if needs_ingestion(db, file_source_id, mtime):
                ingest_file.delay(str(path))
                enqueued += 1
                log.info("Enqueued ingestion for %s", file_source_id)
            else:
                skipped += 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info("scan_and_ingest: enqueued=%d skipped=%d", enqueued, skipped)
    return {"enqueued": enqueued, "skipped": skipped}


@celery_app.task(
    name="app.tasks.brain_tasks.ingest_file",
    bind=True,
    max_retries=settings.max_ingestion_retries,
)
def ingest_file(self, file_path: str, job_id: str | None = None) -> dict:
    """Run the full ingestion pipeline for one file.

    Implements the three-entry Algorithm A/C job state machine:
    - On first attempt, claims the job atomically (Algorithm A/C).
    - On retry, resumes the same job by ID so the retrying row is not
      treated as a fresh active job and blocked by claim_job.
    - On final retry exhaustion, marks the job permanently failed.
    """
    validate_ai_keys(settings)

    path = Path(file_path)
    file_source_id = _file_source_id(path)

    db_gen = get_db()
    db = next(db_gen)
    claimed_job_id = None

    try:
        # Resume the same job on retries so the 'retrying' row is reused
        # rather than blocking a fresh claim via the partial unique index.
        if job_id:
            row = db.execute(
                sa.text(
                    "UPDATE ingestion_jobs "
                    "SET status = 'running', locked_at = now(), "
                    "    attempt_number = attempt_number + 1 "
                    "WHERE id = :id AND status = 'retrying' "
                    "RETURNING id"
                ),
                {"id": job_id},
            ).fetchone()
            db.commit()
            claimed_job_id = uuid.UUID(str(row[0])) if row else None

        if claimed_job_id is None:
            claimed_job_id = claim_job(db, file_source_id)

        if claimed_job_id is None:
            log.info("Job held by another worker for %s — dropping", file_source_id)
            return {"status": "skipped", "source_id": file_source_id}

        processed = run_file_pipeline(db, path, claimed_job_id)
        release_job(db, claimed_job_id, success=True)

        return {
            "status": "completed",
            "source_id": file_source_id,
            "documents_processed": processed,
        }

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        log.exception("Ingestion failed for %s", file_source_id)

        if claimed_job_id is not None:
            try:
                db.rollback()
                mark_job_retrying(db, claimed_job_id, error_msg)
            except Exception:
                log.warning("Could not mark job retrying for %s", file_source_id)

        retry_in = settings.retry_backoff_base_seconds * (2 ** self.request.retries)
        try:
            raise self.retry(
                exc=exc,
                countdown=retry_in,
                kwargs={"file_path": file_path, "job_id": str(claimed_job_id) if claimed_job_id else None},
            )
        except self.MaxRetriesExceededError:
            if claimed_job_id is not None:
                try:
                    db.rollback()
                    release_job(db, claimed_job_id, success=False, error_message=error_msg)
                except Exception:
                    log.warning("Could not mark job failed for %s", file_source_id)
            raise

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
