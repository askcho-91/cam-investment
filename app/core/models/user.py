from .base_models import Base, BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, UUID as SQLAlchemyUUID
from uuid import UUID


class User(BaseModel, Base):
    """user class"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    auth_user_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, unique=True, nullable=False)

    def __init__(self, *args, **kwargs):
        """Initializes the Employee instance."""
        super().__init__(*args, **kwargs)
