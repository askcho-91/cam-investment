from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):
    email: EmailStr = Field(..., description="The user's email address")
    password: str = Field(..., description="The user's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "israelinene91@gmail.com",
                "password": "securepassword"
            }
        }