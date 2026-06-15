"""Tests for the ingestion job state machine.

Covers: Algorithm A (fresh claim), Algorithm C (stale takeover), release,
retry transition, and the partial unique index that prevents duplicate active jobs.
All tests run against a real PostgreSQL instance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from app.pipeline.ingestion import claim_job, mark_job_retrying, needs_ingestion, release_job


def _job_status(db, job_id: uuid.UUID) -> str | None:
    row = db.execute(
        sa.text("SELECT status FROM ingestion_jobs WHERE id = :id"),
        {"id": str(job_id)},
    ).fetchone()
    return row[0] if row else None


def _active_job_count(db, source_id: str) -> int:
    """Count jobs in running or retrying state for a given source_id."""
    return db.execute(
        sa.text(
            "SELECT COUNT(*) FROM ingestion_jobs "
            "WHERE source_id = :sid AND status IN ('running', 'retrying')"
        ),
        {"sid": source_id},
    ).scalar()


def _insert_job(db, source_id: str, status: str, locked_at: datetime, attempt: int = 1) -> uuid.UUID:
    job_id = uuid.uuid4()
    db.execute(
        sa.text(
            "INSERT INTO ingestion_jobs "
            "(id, source_id, status, locked_at, attempt_number) "
            "VALUES (:id, :sid, :status, :locked_at, :attempt)"
        ),
        {
            "id": str(job_id),
            "sid": source_id,
            "status": status,
            "locked_at": locked_at,
            "attempt": attempt,
        },
    )
    db.commit()
    return job_id


# ─────────────────────────────────────────────── Algorithm A: fresh claim


def test_algorithm_a_fresh_claim_returns_job_id(db):
    job_id = claim_job(db, "policies/doc.md")
    assert job_id is not None
    assert isinstance(job_id, uuid.UUID)


def test_algorithm_a_sets_status_running(db):
    job_id = claim_job(db, "policies/doc.md")
    assert _job_status(db, job_id) == "running"


def test_algorithm_a_live_job_blocks_second_claim(db):
    """A live running job must prevent a second claim via Algorithm A."""
    claim_job(db, "policies/doc.md")
    second = claim_job(db, "policies/doc.md")
    assert second is None


def test_algorithm_a_retrying_job_blocks_new_claim(db):
    """A retrying job must block Algorithm A (covers the retry-gap race)."""
    job_id = claim_job(db, "policies/doc.md")
    mark_job_retrying(db, job_id, "transient error")
    second = claim_job(db, "policies/doc.md")
    assert second is None


def test_algorithm_a_succeeds_after_prior_job_completes(db):
    """Once a job reaches 'success', a new claim for the same source must be allowed."""
    job_id = claim_job(db, "policies/doc.md")
    release_job(db, job_id, success=True)

    new_job_id = claim_job(db, "policies/doc.md")
    assert new_job_id is not None
    assert new_job_id != job_id


def test_algorithm_a_succeeds_after_prior_job_fails(db):
    job_id = claim_job(db, "policies/doc.md")
    release_job(db, job_id, success=False, error_message="fatal error")

    new_job_id = claim_job(db, "policies/doc.md")
    assert new_job_id is not None


# ─────────────────────────────────────────────── Algorithm C: stale takeover


def test_algorithm_c_takes_over_stale_running_job(db):
    """A running job whose locked_at is older than the stale threshold must be evicted."""
    stale_locked_at = datetime.now(tz=timezone.utc) - timedelta(minutes=20)
    _insert_job(db, "policies/stale.md", "running", stale_locked_at)

    new_id = claim_job(db, "policies/stale.md")
    assert new_id is not None


def test_algorithm_c_takes_over_stale_retrying_job(db):
    stale_locked_at = datetime.now(tz=timezone.utc) - timedelta(minutes=20)
    _insert_job(db, "policies/stale_retry.md", "retrying", stale_locked_at)

    new_id = claim_job(db, "policies/stale_retry.md")
    assert new_id is not None


def test_algorithm_c_does_not_evict_fresh_running_job(db):
    """A job locked 5 minutes ago (within the 15-min threshold) must not be evicted."""
    fresh_locked_at = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    _insert_job(db, "policies/fresh.md", "running", fresh_locked_at)

    result = claim_job(db, "policies/fresh.md")
    assert result is None


def test_algorithm_c_does_not_evict_job_at_boundary(db):
    """A job locked exactly 14 minutes ago is still live — must not be evicted."""
    boundary_locked_at = datetime.now(tz=timezone.utc) - timedelta(minutes=14)
    _insert_job(db, "policies/boundary.md", "running", boundary_locked_at)

    result = claim_job(db, "policies/boundary.md")
    assert result is None


# ────────────────────────────────────────────────── release_job transitions


def test_release_job_success_sets_status_success(db):
    job_id = claim_job(db, "policies/doc.md")
    release_job(db, job_id, success=True)
    assert _job_status(db, job_id) == "success"


def test_release_job_failure_sets_status_failed(db):
    job_id = claim_job(db, "policies/doc.md")
    release_job(db, job_id, success=False, error_message="something broke")
    assert _job_status(db, job_id) == "failed"


def test_release_job_stores_error_message(db):
    job_id = claim_job(db, "policies/doc.md")
    release_job(db, job_id, success=False, error_message="API timeout")

    row = db.execute(
        sa.text("SELECT error_message FROM ingestion_jobs WHERE id = :id"),
        {"id": str(job_id)},
    ).fetchone()
    assert row[0] == "API timeout"


# ──────────────────────────────────────────────── mark_job_retrying transition


def test_mark_job_retrying_sets_status_retrying(db):
    job_id = claim_job(db, "policies/doc.md")
    mark_job_retrying(db, job_id, "transient failure")
    assert _job_status(db, job_id) == "retrying"


def test_mark_job_retrying_stores_error_message(db):
    job_id = claim_job(db, "policies/doc.md")
    mark_job_retrying(db, job_id, "voyage timeout")

    row = db.execute(
        sa.text("SELECT error_message FROM ingestion_jobs WHERE id = :id"),
        {"id": str(job_id)},
    ).fetchone()
    assert row[0] == "voyage timeout"


# ─────────────────────────────────────────── partial unique index enforcement


def test_partial_unique_index_prevents_two_running_jobs(db):
    """The partial unique index on (source_id) WHERE status IN ('running','retrying')
    must reject a second INSERT for the same source while the first is running.
    """
    source_id = "policies/contested.md"
    claim_job(db, source_id)

    # Direct INSERT should fail with a unique constraint violation
    with pytest.raises(Exception, match="unique|duplicate|constraint"):
        with db.begin_nested():
            db.execute(
                sa.text(
                    "INSERT INTO ingestion_jobs "
                    "(id, source_id, status, locked_at, attempt_number) "
                    "VALUES (gen_random_uuid(), :sid, 'running', now(), 1)"
                ),
                {"sid": source_id},
            )


def test_partial_unique_index_allows_new_job_after_success(db):
    """After a job reaches 'success', it leaves the partial index — new INSERT must succeed."""
    source_id = "policies/sequential.md"
    job_id = claim_job(db, source_id)
    release_job(db, job_id, success=True)

    # Direct INSERT into the now-vacated slot must not raise
    new_id = str(uuid.uuid4())
    db.execute(
        sa.text(
            "INSERT INTO ingestion_jobs "
            "(id, source_id, status, locked_at, attempt_number) "
            "VALUES (:id, :sid, 'running', now(), 1)"
        ),
        {"id": new_id, "sid": source_id},
    )
    db.commit()

    assert _job_status(db, uuid.UUID(new_id)) == "running"


def test_only_one_active_job_per_source_at_any_time(db):
    """Invariant: at most one job can be in running or retrying state per source."""
    source_id = "policies/invariant.md"
    claim_job(db, source_id)

    # Attempt multiple additional claims — all must fail
    for _ in range(3):
        result = claim_job(db, source_id)
        assert result is None

    assert _active_job_count(db, source_id) == 1
