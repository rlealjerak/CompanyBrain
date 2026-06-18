"""Celery tasks for the Personal Intelligence Layer (PIL).

scan_and_extract_personal — Beat-driven scanner; enqueues extract_tasks_for_file
  for each Slack / email file.

extract_tasks_for_file — Runs Claude task extraction for every user in the DB
  against one source file, stores new tasks, then dispatches bundle_task_context.

bundle_task_context — Calls the Brain search API and writes context_bundle onto
  the task row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa

from app.celery_app import celery_app
from app.connectors.base import Document
from app.connectors.json_connector import EmailConnector, SlackConnector
from app.core.config import settings
from app.core.database import get_db
from app.personal.context_bundler import bundle_context
from app.personal.task_extractor import extract_tasks
from app.personal.urgency_scorer import score_urgency

log = logging.getLogger(__name__)

# Only these source types carry personal action items
_PIL_CONTENT_TYPES = {"slack", "email"}


def _raw_dir() -> Path:
    return Path(settings.data_dir) / "raw"


def _load_document(path: Path) -> Document | None:
    """Load a single Document from a Slack or email file; return None otherwise."""
    suffix = path.suffix.lower()
    if suffix != ".json":
        return None

    # Identify content type from parent directory
    parent = path.parent.name.lower()
    try:
        if parent == "slack":
            docs = SlackConnector().load(path)
        elif parent == "emails":
            docs = EmailConnector().load(path)
        else:
            return None
        return docs[0] if docs else None
    except Exception as exc:
        log.warning("Could not load PIL document %s: %s", path, exc)
        return None


# ─────────────────────────────────────────────────────────────────────── tasks


@celery_app.task(name="app.tasks.personal_tasks.scan_and_extract_personal")
def scan_and_extract_personal() -> dict:
    """Scan data/raw/slack/ and data/raw/emails/ and enqueue per-file extraction."""
    raw_dir = _raw_dir()
    if not raw_dir.exists():
        log.warning("Data directory not found: %s", raw_dir)
        return {"enqueued": 0}

    enqueued = 0
    for path in sorted(raw_dir.rglob("*.json")):
        parent = path.parent.name.lower()
        if parent not in ("slack", "emails"):
            continue
        extract_tasks_for_file.delay(str(path))
        enqueued += 1
        log.info("Enqueued PIL extraction for %s", path.name)

    log.info("scan_and_extract_personal: enqueued=%d", enqueued)
    return {"enqueued": enqueued}


@celery_app.task(
    name="app.tasks.personal_tasks.extract_tasks_for_file",
    bind=True,
    max_retries=3,
)
def extract_tasks_for_file(self, file_path: str) -> dict:
    """Extract tasks from one Slack/email file for all users in the database."""
    path = Path(file_path)
    doc = _load_document(path)
    if doc is None:
        return {"status": "skipped", "file": file_path}

    db_gen = get_db()
    db = next(db_gen)
    stored = 0
    try:
        users = db.execute(
            sa.text("SELECT id, email, role FROM users")
        ).fetchall()

        # Build a human-readable source label for UI display
        if doc.content_type == "slack":
            source_label = f"Slack: {doc.source_name}"
        else:
            source_label = f"Email: {doc.source_name}"

        for user_row in users:
            user_id = str(user_row[0])
            user_email = user_row[1]
            user_role = user_row[2]
            # Use the part before @ as the display name (e.g. "roberto.leal" → "Roberto Leal")
            name_part = user_email.split("@")[0]
            user_name = " ".join(p.capitalize() for p in name_part.replace(".", " ").split())

            try:
                tasks = extract_tasks(doc, user_name, user_role)
            except Exception as exc:
                log.error(
                    "Task extraction failed for %s / %s: %s",
                    file_path,
                    user_email,
                    exc,
                )
                continue

            for t in tasks:
                deadline_dt: datetime | None = None
                if t["deadline_str"]:
                    try:
                        deadline_dt = datetime.fromisoformat(
                            t["deadline_str"].replace("Z", "+00:00")
                        )
                        if deadline_dt.tzinfo is None:
                            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        deadline_dt = None

                urgency_score, urgency_band = score_urgency(
                    raw_score=t["raw_urgency_score"],
                    deadline_str=t["deadline_str"],
                    explicitly_named=t["explicitly_named"],
                    sender_is_manager=t["sender_is_manager"],
                )

                try:
                    row = db.execute(
                        sa.text(
                            "INSERT INTO tasks "
                            "  (id, user_id, description, urgency_score, urgency_band, "
                            "   status, deadline, source_reference, task_fingerprint, "
                            "   source_label, sender, action_type, created_at) "
                            "VALUES "
                            "  (gen_random_uuid(), :user_id, :desc, :score, :band, "
                            "   'open', :deadline, :source_ref, :fingerprint, "
                            "   :source_label, :sender, :action_type, now()) "
                            "ON CONFLICT (user_id, source_reference, task_fingerprint) "
                            "DO NOTHING "
                            "RETURNING id"
                        ),
                        {
                            "user_id": user_id,
                            "desc": t["description"],
                            "score": urgency_score,
                            "band": urgency_band,
                            "deadline": deadline_dt,
                            "source_ref": t["source_reference"],
                            "fingerprint": t["task_fingerprint"],
                            "source_label": source_label,
                            "sender": t["sender"],
                            "action_type": t["action_type"],
                        },
                    ).fetchone()
                    db.commit()

                    if row:
                        task_id = str(row[0])
                        stored += 1
                        # Dispatch context bundling as a follow-up task
                        bundle_task_context.delay(task_id, user_id)
                        log.info(
                            "Stored task %s for %s (band=%s)", task_id, user_email, urgency_band
                        )
                except Exception as exc:
                    db.rollback()
                    log.error("Failed to store task for %s: %s", user_email, exc)

    except Exception as exc:
        log.exception("extract_tasks_for_file failed for %s", file_path)
        try:
            next(db_gen)
        except StopIteration:
            pass
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    return {"status": "completed", "file": file_path, "tasks_stored": stored}


@celery_app.task(
    name="app.tasks.personal_tasks.bundle_task_context",
    bind=True,
    max_retries=3,
)
def bundle_task_context(self, task_id: str, user_id: str) -> dict:
    """Fetch relevant Brain chunks for a task and write them to context_bundle."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        row = db.execute(
            sa.text("SELECT description FROM tasks WHERE id = :id AND user_id = :uid"),
            {"id": task_id, "uid": user_id},
        ).fetchone()

        if not row:
            log.warning("bundle_task_context: task %s not found", task_id)
            return {"status": "not_found"}

        description = row[0]
        chunks = bundle_context(description, user_id)

        import json as _json
        db.execute(
            sa.text(
                "UPDATE tasks SET context_bundle = CAST(:bundle AS jsonb) "
                "WHERE id = :id AND user_id = :uid"
            ),
            {
                "bundle": _json.dumps(chunks) if chunks else None,
                "id": task_id,
                "uid": user_id,
            },
        )
        db.commit()
        log.info("Bundled %d chunk(s) onto task %s", len(chunks), task_id)
        return {"status": "bundled", "task_id": task_id, "chunks": len(chunks)}

    except Exception as exc:
        log.exception("bundle_task_context failed for task %s", task_id)
        try:
            db.rollback()
        except Exception:
            pass
        try:
            next(db_gen)
        except StopIteration:
            pass
        raise self.retry(exc=exc, countdown=15 * (2 ** self.request.retries))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
