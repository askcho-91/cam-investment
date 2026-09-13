from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from app.core.models.support_conversations import MessageRole


class CreateSupportConversation(BaseModel):
    user_id: UUID = Field(..., description="The ID of the user")


class UpdateSupportConversation(BaseModel):
    title: Optional[str] = Field(
        None, description="The title of the support conversation"
    )
    last_interaction_id: Optional[str] = Field(
        None, description="The ID of the last interaction in the conversation"
    )


class CreateSupportMessage(BaseModel):
    conversation_id: UUID = Field(..., description="The ID of the support conversation")
    role: MessageRole = Field(..., description="The role of the sender (bot or user)")
    message: str = Field(..., description="The content of the support message")


class ReadSupportMessage(BaseModel):
    id: UUID = Field(..., description="The ID of the support message")
    conversation_id: UUID = Field(..., description="The ID of the support conversation")
    role: MessageRole = Field(..., description="The role of the sender (bot or user)")
    message: str = Field(..., description="The content of the support message")
    created_at: datetime = Field(
        ..., description="The timestamp when the message was created"
    )
    updated_at: datetime = Field(
        ..., description="The timestamp when the message was last updated"
    )

    class Config:
        from_attributes = True


class ReadPublicSupportMessage(BaseModel):
    message: str = Field(..., description="The content of the support message")
    interaction_id: str = Field(
        ..., description="The ID of the interaction associated with the message"
    )


class ReadSupportConversationMessages(BaseModel):
    id: UUID = Field(..., description="The ID of the support conversation")
    user_id: UUID = Field(..., description="The ID of the user")
    title: str = Field(..., description="The title of the support conversation")
    last_interaction_id: str | None = Field(
        None, description="The ID of the last interaction in the conversation"
    )
    created_at: datetime = Field(
        ..., description="The timestamp when the conversation was created"
    )
    updated_at: datetime = Field(
        ..., description="The timestamp when the conversation was last updated"
    )
    messages: list[ReadSupportMessage] | None = Field(
        default_factory=list,
        description="A list of messages associated with the support conversation",
    )

    class Config:
        from_attributes = True


class ReadSupportConversation(BaseModel):
    id: UUID = Field(..., description="The ID of the support conversation")
    user_id: UUID = Field(..., description="The ID of the user")
    title: str = Field(..., description="The title of the support conversation")
    last_interaction_id: str | None = Field(
        None, description="The ID of the last interaction in the conversation"
    )
    created_at: datetime = Field(
        ..., description="The timestamp when the conversation was created"
    )
    updated_at: datetime = Field(
        ..., description="The timestamp when the conversation was last updated"
    )

    class Config:
        from_attributes = True
