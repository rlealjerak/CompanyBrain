from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CorpusVersion(Base):
    __tablename__ = "corpus_version"

    # Single-row table. version is incremented inside Commit 2 — the same
    # transaction that marks a document complete. One increment per committed
    # document. Never incremented at job success.
    version: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
