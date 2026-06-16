"""Run the full ingestion pipeline against data/raw/ without Celery.

Requires real ANTHROPIC_API_KEY and VOYAGE_API_KEY in the environment.
Connects to DATABASE_URL directly (defaults to the local Docker postgres).

Usage:
    # From the project root:
    export DATABASE_URL=postgresql://company_brain:company_brain@localhost:5432/company_brain
    export ANTHROPIC_API_KEY=sk-ant-...
    export VOYAGE_API_KEY=pa-...
    python scripts/ingest_all.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow importing from backend/app when run from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://company_brain:company_brain@localhost:5432/company_brain",
)

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.pipeline.ingestion import claim_job, needs_ingestion, release_job, run_file_pipeline

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
SUPPORTED = {".md", ".json"}


def main() -> None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    voyage_key = os.environ.get("VOYAGE_API_KEY", "")
    if not anthropic_key or anthropic_key.startswith("sk-ant-placeholder"):
        print("ERROR: ANTHROPIC_API_KEY is not set or is a placeholder.", file=sys.stderr)
        sys.exit(1)
    if not voyage_key or voyage_key.startswith("pa-placeholder"):
        print("ERROR: VOYAGE_API_KEY is not set or is a placeholder.", file=sys.stderr)
        sys.exit(1)

    database_url = os.environ["DATABASE_URL"]
    engine = sa.create_engine(database_url)

    files = sorted(p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix in SUPPORTED)
    print(f"Found {len(files)} files in {RAW_DIR}")

    success = 0
    skipped = 0
    failed = 0

    for path in files:
        file_source_id = str(path.relative_to(RAW_DIR))
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

        with Session(engine) as db:
            if not needs_ingestion(db, file_source_id, mtime):
                print(f"  [skip]    {file_source_id}")
                skipped += 1
                continue

            job_id = claim_job(db, file_source_id)
            if job_id is None:
                print(f"  [held]    {file_source_id}")
                skipped += 1
                continue

            try:
                processed = run_file_pipeline(db, path, job_id)
                release_job(db, job_id, success=True)
                print(f"  [ok]      {file_source_id}  ({processed} doc(s))")
                success += 1
            except Exception as exc:
                release_job(db, job_id, success=False, error_message=str(exc))
                print(f"  [FAILED]  {file_source_id}  — {exc}", file=sys.stderr)
                failed += 1

    print(f"\nDone: {success} ingested, {skipped} skipped, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
