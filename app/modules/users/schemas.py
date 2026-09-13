from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUserSchema(BaseModel):
    email: EmailStr = Field(..., description="The user's email address")
    password: str = Field(..., description="The user's password")
    first_name: str = Field(..., description="The user's first name")
    last_name: str = Field(..., description="The user's last name")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "securepassword",
                "first_name": "John",
                "last_name": "Doe",
            }
        }


class UpdateUserSchema(BaseModel):
    first_name: str | None = Field(
        None, min_length=1, description="The user's first name"
    )
    last_name: str | None = Field(
        None, min_length=1, description="The user's last name"
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    first_name: str
    last_name: str
    auth_user_id: str
    created_at: datetime
    updated_at: datetime
