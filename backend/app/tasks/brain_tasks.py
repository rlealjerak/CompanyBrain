from app.celery_app import celery_app  # noqa: F401

# Phase 3 tasks implemented here:
# - scan_and_ingest: scans data/raw/, enqueues ingestion for new/changed files
# - ingest_file: runs the full ingestion pipeline for a single source file
