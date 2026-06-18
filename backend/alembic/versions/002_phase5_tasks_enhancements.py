"""Phase 5 — add display columns to tasks and seed regular user

Adds created_at, source_label, sender, action_type to the tasks table
so the PIL dashboard can show rich context without extra lookups.
Also seeds the demo regular user (roberto.leal@acme.com).

Revision ID: 002
Revises: 001
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import os

import bcrypt
import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column("tasks", sa.Column("source_label", sa.Text()))
    op.add_column("tasks", sa.Column("sender", sa.Text()))
    op.add_column("tasks", sa.Column("action_type", sa.Text()))

    user_password = os.environ.get("USER_BOOTSTRAP_PASSWORD", "user123")
    pw_hash = bcrypt.hashpw(user_password.encode(), bcrypt.gensalt(12)).decode()
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO users (id, email, hashed_password, role) "
            "VALUES (gen_random_uuid(), :email, :pw, :role) "
            "ON CONFLICT (email) DO NOTHING"
        ),
        {"email": "roberto.leal@acme.com", "pw": pw_hash, "role": "user"},
    )


def downgrade() -> None:
    op.drop_column("tasks", "action_type")
    op.drop_column("tasks", "sender")
    op.drop_column("tasks", "source_label")
    op.drop_column("tasks", "created_at")
