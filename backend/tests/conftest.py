"""Shared pytest fixtures for Phase 3 tests.

Requires a PostgreSQL 15 instance with the pgvector extension installed.
The test database must exist before running tests — create it once:

    # Inside the Docker postgres container:
    docker exec -it <postgres_container> createdb -U company_brain company_brain_test

    # Or in psql:
    CREATE DATABASE company_brain_test;

Then run tests from the backend/ directory:
    pytest
    # or with a custom URL:
    TEST_DATABASE_URL="postgresql://user:pass@host:5432/company_brain_test" pytest
"""

from __future__ import annotations

import os

# ── MUST be first: set DATABASE_URL before any app module is imported ────────
#
# alembic/env.py reads os.environ["DATABASE_URL"] directly (line 25).
# app/core/config.py instantiates Settings() at module level, which also
# reads env vars. Both fire the moment their modules are first imported.
# Setting the env var here, before any other imports, guarantees the test
# database URL is in place for both.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://company_brain:company_brain@localhost:5432/company_brain_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# ── Safe to import everything else now ───────────────────────────────────────
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).parent.parent


# ──────────────────────────────────────────────── database engine + schema


@pytest.fixture(scope="session")
def db_engine():
    """Drop and recreate the test schema, then run all Alembic migrations.

    Runs once per test session so migrations aren't repeated for every test.
    """
    engine = sa.create_engine(TEST_DATABASE_URL)

    # Wipe the public schema so every session starts from a clean slate.
    with engine.connect() as conn:
        conn.execute(sa.text("DROP SCHEMA public CASCADE"))
        conn.execute(sa.text("CREATE SCHEMA public"))
        conn.commit()

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    """Yield a Session and truncate all data tables after each test."""
    session = Session(db_engine)
    try:
        yield session
    finally:
        session.close()
        with db_engine.connect() as conn:
            conn.execute(sa.text(
                "TRUNCATE ingestion_jobs, documents, chunks, embeddings, corpus_version CASCADE"
            ))
            conn.execute(sa.text("INSERT INTO corpus_version (version) VALUES (0)"))
            conn.commit()


# ───────────────────────────────────────────────────────────── AI mocks


@pytest.fixture
def mock_ai():
    """Patch Voyage AI and Claude so tests never hit real APIs.

    embed_texts  → 1024-dim unit vectors (one per input text)
    extract_knowledge → minimal valid knowledge dict
    """
    fake_knowledge = {
        "key_facts": ["Test fact"],
        "entities": [],
        "action_items": [],
        "policy_rules": [],
        "summary": "Test document summary.",
    }

    def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1024 for _ in texts]

    with (
        patch("app.pipeline.ingestion.embed_texts", side_effect=fake_embed),
        patch("app.pipeline.ingestion.extract_knowledge", return_value=fake_knowledge),
    ):
        yield
