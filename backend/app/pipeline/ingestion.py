"""Ingestion pipeline and job state machine.

Three-entry algorithm for concurrency-safe job ownership:

  Algorithm A — first claim:
    INSERT ... ON CONFLICT (source_id) WHERE status IN ('running','retrying') DO NOTHING
    Returns the new job_id when we win the race, None when another worker holds it.

  Algorithm C — stale takeover:
    If Algorithm A found an existing active job, check whether locked_at is older
    than stale_job_threshold_minutes. If so, UPDATE to take ownership.

  Commit step — after successful pipeline:
    UPDATE document ingestion_status + increment corpus_version in one transaction
    so no reader ever sees a committed document without a bumped corpus version.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.connectors import Document, get_connector
from app.core.config import settings
from app.pipeline.chunker import chunk_text
from app.pipeline.embedder import embed_texts
from app.pipeline.extractor import extract_knowledge

log = logging.getLogger(__name__)

_STALE_MINUTES = settings.stale_job_threshold_minutes


# ──────────────────────────────────────────────────────────── job state machine


def claim_job(db: Session, file_source_id: str) -> uuid.UUID | None:
    """Algorithm A + C: atomically claim an ingestion job for *file_source_id*.

    Returns the job UUID we own, or None if another worker holds a fresh job.
    """
    new_id = uuid.uuid4()

    # Algorithm A — INSERT ON CONFLICT against the partial unique index.
    # The index predicate is: status IN ('running', 'retrying').
    row = db.execute(
        sa.text(
            "INSERT INTO ingestion_jobs "
            "  (id, source_id, status, locked_at, attempt_number) "
            "VALUES "
            "  (:id, :source_id, 'running', now(), 1) "
            "ON CONFLICT (source_id) WHERE status IN ('running', 'retrying') "
            "DO NOTHING "
            "RETURNING id"
        ),
        {"id": str(new_id), "source_id": file_source_id},
    ).fetchone()
    db.commit()

    if row:
        return uuid.UUID(str(row[0]))

    # Algorithm C — stale takeover: the existing active job may have been
    # abandoned by a crashed worker.
    row = db.execute(
        sa.text(
            "UPDATE ingestion_jobs "
            "SET status = 'running', "
            "    locked_at = now(), "
            "    attempt_number = attempt_number + 1 "
            "WHERE source_id = :source_id "
            "  AND status IN ('running', 'retrying') "
            "  AND locked_at < now() - (interval '1 minute' * :minutes) "
            "RETURNING id"
        ),
        {"source_id": file_source_id, "minutes": _STALE_MINUTES},
    ).fetchone()
    db.commit()

    if row:
        return uuid.UUID(str(row[0]))

    return None


def release_job(
    db: Session,
    job_id: uuid.UUID,
    *,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Mark a job completed or failed."""
    status = "completed" if success else "failed"
    db.execute(
        sa.text(
            "UPDATE ingestion_jobs "
            "SET status = :status, error_message = :error "
            "WHERE id = :id"
        ),
        {"status": status, "error": error_message, "id": str(job_id)},
    )
    db.commit()


def mark_job_retrying(db: Session, job_id: uuid.UUID, error_message: str) -> None:
    """Transition a running job to 'retrying' so another worker can take over
    after the stale threshold if this attempt fails."""
    db.execute(
        sa.text(
            "UPDATE ingestion_jobs "
            "SET status = 'retrying', error_message = :error "
            "WHERE id = :id"
        ),
        {"error": error_message, "id": str(job_id)},
    )
    db.commit()


def needs_ingestion(db: Session, file_source_id: str, current_mtime: datetime) -> bool:
    """Return True if the file has never been successfully ingested or has changed."""
    row = db.execute(
        sa.text(
            "SELECT source_mtime FROM documents "
            "WHERE source_id = :source_id AND ingestion_status = 'complete' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"source_id": file_source_id},
    ).fetchone()

    if row is None:
        return True

    stored_mtime: datetime | None = row[0]
    if stored_mtime is None:
        return True

    if stored_mtime.tzinfo is None:
        stored_mtime = stored_mtime.replace(tzinfo=timezone.utc)

    return current_mtime > stored_mtime


# ──────────────────────────────────────────────────────────────────── pipeline


def _ingest_document(db: Session, doc: Document, job_id: uuid.UUID) -> bool:
    """Run the full pipeline for one Document.

    Returns True if the document was processed, False if it was already
    present (same content_hash) and skipped.
    """
    content_hash = hashlib.sha256(doc.raw_content.encode()).hexdigest()
    doc_id = uuid.uuid4()

    row = db.execute(
        sa.text(
            "INSERT INTO documents "
            "  (id, source_id, content_hash, source_mtime, ingestion_status, "
            "   ingestion_job_id, raw_content) "
            "VALUES "
            "  (:id, :source_id, :hash, :mtime, 'processing', :job_id, :raw) "
            "ON CONFLICT ON CONSTRAINT uq_documents_source_hash DO NOTHING "
            "RETURNING id"
        ),
        {
            "id": str(doc_id),
            "source_id": doc.source_id,
            "hash": content_hash,
            "mtime": doc.timestamp,
            "job_id": str(job_id),
            "raw": doc.raw_content,
        },
    ).fetchone()
    db.commit()

    if not row:
        log.debug("Skipping %s — content unchanged", doc.source_id)
        return False

    doc_id = uuid.UUID(str(row[0]))

    # Chunk → embed → extract
    chunks = chunk_text(doc.raw_content)
    if not chunks:
        log.warning("No chunks produced for %s", doc.source_id)
        return True

    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    knowledge = extract_knowledge(doc.raw_content, doc.content_type)

    # Persist chunks and embeddings
    for chunk, vector in zip(chunks, vectors):
        chunk_id = uuid.uuid4()
        db.execute(
            sa.text(
                "INSERT INTO chunks (id, document_id, chunk_index, text, token_count) "
                "VALUES (:id, :doc_id, :idx, :text, :tokens)"
            ),
            {
                "id": str(chunk_id),
                "doc_id": str(doc_id),
                "idx": chunk["chunk_index"],
                "text": chunk["text"],
                "tokens": chunk["token_count"],
            },
        )

        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        db.execute(
            sa.text(
                "INSERT INTO embeddings "
                "  (id, chunk_id, document_id, source_id, source_type, "
                "   chunk_index, vector, source_timestamp) "
                "VALUES "
                "  (:id, :chunk_id, :doc_id, :source_id, :source_type, "
                "   :idx, CAST(:vector AS vector), :ts)"
            ),
            {
                "id": str(uuid.uuid4()),
                "chunk_id": str(chunk_id),
                "doc_id": str(doc_id),
                "source_id": doc.source_id,
                "source_type": doc.content_type,
                "idx": chunk["chunk_index"],
                "vector": vector_str,
                "ts": doc.timestamp,
            },
        )

    # Atomic commit: mark document complete + bump corpus version together
    # so readers never see a complete document without an updated version.
    db.execute(
        sa.text(
            "UPDATE documents "
            "SET ingestion_status = 'complete', extracted_knowledge = CAST(:knowledge AS jsonb) "
            "WHERE id = :doc_id"
        ),
        {"knowledge": json.dumps(knowledge), "doc_id": str(doc_id)},
    )
    db.execute(sa.text("UPDATE corpus_version SET version = version + 1"))
    db.commit()

    log.info("Ingested %s (%d chunks)", doc.source_id, len(chunks))
    return True


def run_file_pipeline(db: Session, path: Path, job_id: uuid.UUID) -> int:
    """Load *path* via the appropriate connector and ingest all resulting documents.

    Returns the number of documents actually processed (skips unchanged content).
    """
    connector = get_connector(path)
    documents = connector.load(path)

    processed = 0
    for doc in documents:
        if _ingest_document(db, doc, job_id):
            processed += 1

    return processed
