import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_documents_source_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    source_mtime: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    ingestion_status: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id")
    )
    raw_content: Mapped[Optional[str]] = mapped_column(Text)
    extracted_knowledge: Mapped[Optional[dict]] = mapped_column(JSONB)
    source_quality_score: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(  # noqa: F821
        "IngestionJob", back_populates="documents"
    )
    chunks: Mapped[list["Chunk"]] = relationship(  # noqa: F821
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(  # noqa: F821
        "Embedding", back_populates="document"
    )
