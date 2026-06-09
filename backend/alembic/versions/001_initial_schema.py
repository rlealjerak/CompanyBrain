"""Initial schema — all tables for Company Brain + PIL

Creates every table up front (including Phase 5 tables) to avoid disruptive
migrations once ingestion data exists.

Revision ID: 001
Revises: —
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
    )
    op.create_index("uq_users_email", "users", ["email"], unique=True)

    # --------------------------------------------------------- ingestion_jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("locked_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Partial unique index covers both active states so no duplicate run can
    # be admitted during the retry window (the "retry-gap race").
    # UPDATE-then-INSERT in Algorithm C works because PostgreSQL evaluates
    # non-deferrable unique constraints per-statement: the UPDATE removes the
    # old row from the partial index scope before the INSERT's check fires.
    # Order is load-bearing — INSERT before UPDATE would fail.
    op.execute(
        "CREATE UNIQUE INDEX uq_ingestion_jobs_active_source "
        "ON ingestion_jobs (source_id) "
        "WHERE status IN ('running', 'retrying')"
    )

    # ------------------------------------------------------------ documents
    op.create_table(
        "documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("source_mtime", sa.TIMESTAMP(timezone=True)),
        sa.Column("ingestion_status", sa.Text(), nullable=False),
        sa.Column(
            "ingestion_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestion_jobs.id"),
        ),
        sa.Column("raw_content", sa.Text()),
        sa.Column("extracted_knowledge", JSONB),
        sa.Column("source_quality_score", sa.Integer()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # At most one row per file version can exist at any time.
    op.create_unique_constraint(
        "uq_documents_source_hash", "documents", ["source_id", "content_hash"]
    )

    # --------------------------------------------------------------- chunks
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
    )

    # ---------------------------------------------------------- embeddings
    op.create_table(
        "embeddings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "chunk_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        # Dimension must be exactly 1024 — voyage-3 output size.
        # Wrong dimension silently corrupts similarity scores.
        sa.Column("vector", Vector(1024), nullable=False),
        # source_timestamp: source file's own creation/modified time.
        # Used for Phase 4 recency reranking. Never substitute created_at.
        sa.Column("source_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        # created_at: ingestion time. Audit use only — never used for reranking.
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # HNSW index for fast approximate cosine similarity search.
    # Created here — not as a manual step — so it is always present.
    op.execute(
        "CREATE INDEX idx_embeddings_vector_hnsw "
        "ON embeddings USING hnsw (vector vector_cosine_ops)"
    )

    # ----------- tasks (Phase 5 — created now to avoid later re-migrations)
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("urgency_score", sa.Float()),
        sa.Column("urgency_band", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("deadline", sa.TIMESTAMP(timezone=True)),
        sa.Column("context_bundle", JSONB),
        # source_reference format: slack:{thread_ts} | email:{message_id} | ticket:{ticket_id}
        sa.Column("source_reference", sa.Text(), nullable=False),
        # SHA-256 of source_reference + normalized description
        sa.Column("task_fingerprint", sa.Text(), nullable=False),
    )
    # UNIQUE on (user_id, source_reference, task_fingerprint) — not just
    # (user_id, source_reference) — so multiple distinct tasks from the same
    # source container are allowed while exact duplicates are blocked.
    op.create_unique_constraint(
        "uq_tasks_user_source_fingerprint",
        "tasks",
        ["user_id", "source_reference", "task_fingerprint"],
    )

    # ------------------------------------------------------ corpus_version
    # PRIMARY KEY enforces the single-row invariant at the database level —
    # a duplicate insert raises a unique-violation rather than silently
    # creating a second version row that would corrupt cache invalidation.
    op.create_table(
        "corpus_version",
        sa.Column("version", sa.Integer(), primary_key=True, nullable=False),
    )
    op.execute("INSERT INTO corpus_version (version) VALUES (0)")

    # ---------------------------------------------- seed: admin user
    # Reads ADMIN_BOOTSTRAP_PASSWORD from the environment at migration time.
    # If the variable is not set the seed is skipped — no privileged account
    # is created and the deployer must run scripts/bootstrap_admin.py later.
    # This prevents a known-credential account from existing in every deployed
    # database by default.
    import os

    import bcrypt  # imported here to keep the migration self-contained

    admin_password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if admin_password:
        pw_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt(12)).decode()
        conn = op.get_bind()
        conn.execute(
            sa.text(
                "INSERT INTO users (id, email, hashed_password, role) "
                "VALUES (gen_random_uuid(), :email, :pw, :role)"
            ),
            {"email": "admin@acme.com", "pw": pw_hash, "role": "admin"},
        )
    else:
        print(
            "\n[migration] ADMIN_BOOTSTRAP_PASSWORD not set — admin user not seeded. "
            "Run scripts/bootstrap_admin.py with the variable set to create it.\n"
        )


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("corpus_version")
    op.drop_table("embeddings")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("ingestion_jobs")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
