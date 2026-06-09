"""
Create the initial admin user.

Run this after `alembic upgrade head` if ADMIN_BOOTSTRAP_PASSWORD was not set
during migration, or to add a second admin account.

Usage:
    export DATABASE_URL=postgresql://...
    export ADMIN_BOOTSTRAP_PASSWORD=your_secure_password
    export ADMIN_EMAIL=admin@acme.com        # optional, defaults shown
    python scripts/bootstrap_admin.py
"""
import os
import sys
from pathlib import Path

# Allow importing from backend/app when run from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import bcrypt
import sqlalchemy as sa

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@acme.com")

if not DATABASE_URL:
    print("Error: DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

if not ADMIN_PASSWORD:
    print("Error: ADMIN_BOOTSTRAP_PASSWORD is not set.", file=sys.stderr)
    sys.exit(1)

engine = sa.create_engine(DATABASE_URL)
pw_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt(12)).decode()

with engine.begin() as conn:
    existing = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": ADMIN_EMAIL},
    ).fetchone()

    if existing:
        print(f"Admin account {ADMIN_EMAIL!r} already exists — skipping.")
        sys.exit(0)

    conn.execute(
        sa.text(
            "INSERT INTO users (id, email, hashed_password, role) "
            "VALUES (gen_random_uuid(), :email, :pw, :role)"
        ),
        {"email": ADMIN_EMAIL, "pw": pw_hash, "role": "admin"},
    )

print(f"Admin account created: {ADMIN_EMAIL}")
