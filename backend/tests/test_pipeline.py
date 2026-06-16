"""Integration tests for the ingestion pipeline.

These tests run against a real PostgreSQL instance (TEST_DATABASE_URL) and
use mocked Voyage AI + Claude calls so no real API keys are needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from app.connectors.base import Document
from app.pipeline.ingestion import _ingest_document, claim_job, needs_ingestion


def _make_doc(
    source_id: str = "policy:test",
    content: str = "This is a test policy document with enough words to chunk.",
    ts: datetime | None = None,
    content_type: str = "policy",
) -> Document:
    return Document(
        raw_content=content,
        source_id=source_id,
        source_name="Test Document",
        author="test",
        timestamp=ts or datetime(2024, 1, 1, tzinfo=timezone.utc),
        content_type=content_type,
    )


def _corpus_version(db) -> int:
    return db.execute(sa.text("SELECT version FROM corpus_version")).scalar()


def _doc_status(db, source_id: str) -> str | None:
    row = db.execute(
        sa.text("SELECT ingestion_status FROM documents WHERE source_id = :sid"),
        {"sid": source_id},
    ).fetchone()
    return row[0] if row else None


# ─────────────────────────────────────────────────────────── happy path


def test_happy_path_creates_document(db, mock_ai):
    job_id = claim_job(db, "file:test_policy.md")
    doc = _make_doc()

    result = _ingest_document(db, doc, job_id)

    assert result is True
    assert _doc_status(db, "policy:test") == "complete"


def test_happy_path_creates_chunks(db, mock_ai):
    job_id = claim_job(db, "file:test_policy.md")
    _ingest_document(db, _make_doc(), job_id)

    count = db.execute(sa.text("SELECT COUNT(*) FROM chunks")).scalar()
    assert count >= 1


def test_happy_path_creates_embeddings(db, mock_ai):
    job_id = claim_job(db, "file:test_policy.md")
    _ingest_document(db, _make_doc(), job_id)

    count = db.execute(sa.text("SELECT COUNT(*) FROM embeddings")).scalar()
    assert count >= 1


def test_happy_path_increments_corpus_version(db, mock_ai):
    assert _corpus_version(db) == 0

    job_id = claim_job(db, "file:test_policy.md")
    _ingest_document(db, _make_doc(), job_id)

    assert _corpus_version(db) == 1


def test_happy_path_stores_extracted_knowledge(db, mock_ai):
    job_id = claim_job(db, "file:test_policy.md")
    _ingest_document(db, _make_doc(), job_id)

    row = db.execute(
        sa.text("SELECT extracted_knowledge FROM documents WHERE source_id = 'policy:test'")
    ).fetchone()
    assert row is not None
    knowledge = row[0]
    assert "key_facts" in knowledge
    assert "summary" in knowledge


# ─────────────────────────────────────────────────────────── corpus_version


def test_corpus_version_increments_once_per_document(db, mock_ai):
    """Each unique document increments corpus_version exactly once."""
    job_a = claim_job(db, "file:doc_a.md")
    job_b = claim_job(db, "file:doc_b.md")

    _ingest_document(db, _make_doc(source_id="policy:a", content="Document A content here."), job_a)
    _ingest_document(db, _make_doc(source_id="policy:b", content="Document B content here."), job_b)

    assert _corpus_version(db) == 2


def test_corpus_version_does_not_increment_on_hash_skip(db, mock_ai):
    """Re-ingesting the same content must not advance corpus_version."""
    doc = _make_doc()
    job_id = claim_job(db, "file:test.md")
    _ingest_document(db, doc, job_id)
    assert _corpus_version(db) == 1

    job_id2 = claim_job(db, "file:test.md")
    # A new job won't be created because the first one is 'success'; but
    # even if claim succeeds, the document hash is already present.
    if job_id2 is not None:
        result = _ingest_document(db, doc, job_id2)
        assert result is False

    assert _corpus_version(db) == 1


# ─────────────────────────────────────────────────────────── idempotency


def test_second_ingest_of_same_content_is_skipped(db, mock_ai):
    """Hash-skip: identical document ingested twice → second call returns False."""
    doc = _make_doc(content="Identical content that will not change.")
    job_id = claim_job(db, "file:idempotent.md")
    first = _ingest_document(db, doc, job_id)
    assert first is True

    # Force a second ingestion with the same content
    job_id2 = claim_job(db, "file:idempotent2.md")
    assert job_id2 is not None
    second = _ingest_document(db, doc, job_id2)
    assert second is False


def test_changed_content_is_re_ingested(db, mock_ai):
    """Different content for the same source_id must produce a second document row."""
    job_a = claim_job(db, "file:changing.md")
    _ingest_document(db, _make_doc(source_id="policy:change", content="Original content."), job_a)

    job_b = claim_job(db, "file:changing2.md")
    assert job_b is not None
    result = _ingest_document(
        db,
        _make_doc(source_id="policy:change", content="Completely different content now."),
        job_b,
    )
    assert result is True

    count = db.execute(
        sa.text("SELECT COUNT(*) FROM documents WHERE source_id = 'policy:change'")
    ).scalar()
    assert count == 2


# ───────────────────────────────────────────── source_timestamp vs created_at


def test_source_timestamp_reflects_document_timestamp_not_ingestion_time(db, mock_ai):
    """Embeddings must carry the source document's own timestamp, not now()."""
    source_ts = datetime(2020, 6, 15, tzinfo=timezone.utc)
    doc = _make_doc(source_id="policy:dated", ts=source_ts)

    job_id = claim_job(db, "file:dated.md")
    _ingest_document(db, doc, job_id)

    row = db.execute(
        sa.text("SELECT source_timestamp FROM embeddings WHERE source_id = 'policy:dated' LIMIT 1")
    ).fetchone()
    assert row is not None

    stored = row[0]
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    assert stored == source_ts


def test_older_source_does_not_outrank_newer_source(db, mock_ai):
    """An older source_timestamp must sort below a newer one.

    Guards against the failure mode where ingestion order determines ranking
    instead of actual source recency.
    """
    old_ts = datetime(2020, 1, 1, tzinfo=timezone.utc)
    new_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Ingest the OLDER document first, the NEWER document second.
    job_old = claim_job(db, "file:old.md")
    _ingest_document(db, _make_doc(source_id="policy:old", content="Old policy content.", ts=old_ts), job_old)

    job_new = claim_job(db, "file:new.md")
    _ingest_document(db, _make_doc(source_id="policy:new", content="New policy content.", ts=new_ts), job_new)

    rows = db.execute(
        sa.text(
            "SELECT source_id, source_timestamp FROM embeddings "
            "ORDER BY source_timestamp DESC"
        )
    ).fetchall()

    assert rows[0][0] == "policy:new"
    assert rows[-1][0] == "policy:old"


# ─────────────────────────────────────────────────────── needs_ingestion


def test_needs_ingestion_true_when_no_job_exists(db):
    result = needs_ingestion(db, "policies/new_file.md", datetime.now(tz=timezone.utc))
    assert result is True


def test_needs_ingestion_false_after_successful_job(db):
    db.execute(
        sa.text(
            "INSERT INTO ingestion_jobs (id, source_id, status, locked_at, attempt_number) "
            "VALUES (gen_random_uuid(), :sid, 'success', now(), 1)"
        ),
        {"sid": "policies/known_policy.md"},
    )
    db.commit()

    result = needs_ingestion(db, "policies/known_policy.md", datetime.now(tz=timezone.utc))
    assert result is False


def test_needs_ingestion_true_after_failed_job(db):
    db.execute(
        sa.text(
            "INSERT INTO ingestion_jobs (id, source_id, status, locked_at, attempt_number) "
            "VALUES (gen_random_uuid(), :sid, 'failed', now(), 3)"
        ),
        {"sid": "policies/failed_policy.md"},
    )
    db.commit()

    result = needs_ingestion(db, "policies/failed_policy.md", datetime.now(tz=timezone.utc))
    assert result is True
