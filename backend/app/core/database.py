from typing import Generator

import redis as redis_client
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine is created lazily so importing this module doesn't crash when
# DATABASE_URL is not set (e.g. opening files in an IDE without .env).
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured. Copy .env.example to .env and fill in values.")
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        _get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_postgres() -> bool:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis() -> bool:
    try:
        r = redis_client.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return True
    except Exception:
        return False
