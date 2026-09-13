from .base_models import Base, BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column, Column, String, Text, UUID as SQLAlchemyUUID
from uuid import UUID


class User(BaseModel, Base):
    """user class"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    auth_user_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True), unique=True, nullable=False
    )
    auth_provider: Mapped[str] = mapped_column(Text, nullable=True)    # "firebase", etc.
    auth_provider_id: Mapped[str] = mapped_column(Text, nullable=True, index=True)

    support_conversations = relationship(
        "SupportConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __init__(self, *args, **kwargs):
        """Initializes the Employee instance."""
        super().__init__(*args, **kwargs)
