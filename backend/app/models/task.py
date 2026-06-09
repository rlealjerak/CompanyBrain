import uuid
from datetime import datetime
from typing import Optional  # used by urgency_score, deadline, context_bundle

from sqlalchemy import Float, Text, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source_reference", "task_fingerprint",
            name="uq_tasks_user_source_fingerprint",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    urgency_score: Mapped[Optional[float]] = mapped_column(Float)
    urgency_band: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    context_bundle: Mapped[Optional[dict]] = mapped_column(JSONB)
    # source_reference format: slack:{thread_ts} | email:{message_id} | ticket:{ticket_id}
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    # task_fingerprint = SHA-256(source_reference + normalized description)
    task_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="tasks")  # noqa: F821
