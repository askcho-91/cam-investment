from pydantic import BaseModel, EmailStr, Field


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
                "last_name": "Doe"
            }
        }



class UpdateUserSchema(BaseModel):
    first_name: str = Field(..., description="The user's first name")
    last_name: str = Field(..., description="The user's last name")

    