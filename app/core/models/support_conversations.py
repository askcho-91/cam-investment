from .base_models import BaseModel, Base
from sqlalchemy import Text, ForeignKey, DateTime, Enum

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, mapped_column, Mapped
from datetime import datetime
import enum


class SupportConversation(Base, BaseModel):
    __tablename__ = "support_conversations"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)

    last_interaction_id: Mapped[str] = mapped_column(Text, nullable=True)

    user = relationship(
        "User",
        back_populates="support_conversations",
    )

    messages = relationship(
        "SupportMessages",
        order_by="SupportMessages.created_at",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class MessageRole(enum.Enum):
    bot = "bot"
    user = "user"


class SupportMessages(Base, BaseModel):
    __tablename__ = "support_messages"

    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "support_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", default=MessageRole.user),
        nullable=False,
    )

    conversation = relationship(
        "SupportConversation",
        back_populates="messages",
    )
