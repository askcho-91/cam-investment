import uuid
from datetime import UTC, datetime

from sqlalchemy import UUID, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

time = "%Y-%m-%dT%H:%M:%S.%fZ"

Base = declarative_base()


class BaseModel:
    """The BaseModel class from which future classes will be derived"""

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __init__(self, *args, **kwargs):
        """Initialization of the base model"""
        if kwargs:
            for key, value in kwargs.items():
                if key != "__class__":
                    setattr(self, key, value)
            if kwargs.get("created_at", None) and type(self.created_at) is str:
                self.created_at = datetime.strptime(kwargs["created_at"], time)
            else:
                self.created_at = datetime.now(UTC)
            if kwargs.get("updated_at", None) and type(self.updated_at) is str:
                self.updated_at = datetime.strptime(kwargs["updated_at"], time)
            else:
                self.updated_at = datetime.now(UTC)
            if kwargs.get("id", None) is None:
                self.id = str(uuid.uuid4())
        else:
            self.id = str(uuid.uuid4())
            self.created_at = datetime.now(UTC)
            self.updated_at = self.created_at

    def __str__(self):
        """String representation of the BaseModel class"""
        return f"<{self.__class__.__name__} id={self.id}>"

    def to_dict(self, save_to_file=False):
        """returns a dictionary containing all keys/values of the instance"""
        new_dict = self.__dict__.copy()
        if "created_at" in new_dict:
            new_dict["created_at"] = new_dict["created_at"].strftime(time)
        if "updated_at" in new_dict:
            new_dict["updated_at"] = new_dict["updated_at"].strftime(time)
        new_dict["__class__"] = self.__class__.__name__

        return new_dict

    def json_data(self) -> dict:
        """return a dictionary removing internal atrtributes and sqlalchemy state"""
        data = self.to_dict()
        # Remove internal attributes and sqlalchemy state
        data.pop("_sa_instance_state", None)
        data.pop("__class__", None)
        return data