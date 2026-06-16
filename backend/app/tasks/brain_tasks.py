"""Celery tasks for the Company Brain ingestion pipeline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

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
def ingest_file(self, file_path: str) -> dict:
    """Run the full ingestion pipeline for one file.

    Implements the three-entry Algorithm A/C job state machine:
    - Tries to claim the job atomically (Algorithm A).
    - If the job is held by a fresh worker, drops this attempt.
    - If the job is stale, takes it over (Algorithm C).
    - On failure, marks the job 'retrying' and asks Celery to retry later.
    """
    validate_ai_keys(settings)

    path = Path(file_path)
    file_source_id = _file_source_id(path)

    db_gen = get_db()
    db = next(db_gen)
    job_id = None

    try:
        job_id = claim_job(db, file_source_id)
        if job_id is None:
            log.info("Job held by another worker for %s — dropping", file_source_id)
            return {"status": "skipped", "source_id": file_source_id}

        processed = run_file_pipeline(db, path, job_id)
        release_job(db, job_id, success=True)

        return {
            "status": "completed",
            "source_id": file_source_id,
            "documents_processed": processed,
        }

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        log.exception("Ingestion failed for %s", file_source_id)

        if job_id is not None:
            try:
                mark_job_retrying(db, job_id, error_msg)
            except Exception:
                pass

        retry_in = settings.retry_backoff_base_seconds * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_in)

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
