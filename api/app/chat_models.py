"""ORM models for chat persistence (unit 08).

These share the declarative `Base` from app.models so they register on the same
metadata as Document, but they live in their own module to keep file ownership
clean (app.models is the foundation track's). Schema mirrors the shared contract
in specs/units/README.md:

  chat_sessions(id pk, title, created_at)
  chat_messages(id pk, session_id fk, role, content, citations jsonb, created_at)
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

# JSONB on Postgres (indexable, the production target); plain JSON elsewhere
# (e.g. SQLite in unit tests) so the same models run in both.
CitationsJSON = JSON().with_variant(JSONB(), "postgresql")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at, ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    # 'user' or 'assistant'
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text())
    # List[Citation] as JSON; empty list for user messages and refusals.
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        CitationsJSON, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
