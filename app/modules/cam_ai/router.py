from fastapi import APIRouter, Body
from typing import Optional
from uuid import UUID
from app.core.dependencies import db_dependency, authorization_header, current_user_dependency
from .services.conversation_services import (
    create_support_conversation,
    get_support_conversations,
    get_support_conversation_by_id,
    update_conversation,
    delete_support_conversation,
)
from .services.bot_response import get_bot_response, public_bot_response
from .schemas import (
    CreateSupportConversation,
    UpdateSupportConversation,
    ReadSupportConversation,
    ReadSupportMessage,
    ReadSupportConversationMessages,
    ReadPublicSupportMessage,
)
from uuid import UUID

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["Support Conversations"],
)


@conversation_router.post("/", response_model=ReadSupportConversation)
async def create_conversation(
    db: db_dependency,
    current_user: current_user_dependency,
    auth: authorization_header,
) -> ReadSupportConversation:
    """
    Create a new support conversation.
    """
    new_conversation = await create_support_conversation(
        db=db,
        current_user=current_user,
    )
    return ReadSupportConversation.model_validate(new_conversation)


@conversation_router.get("/", response_model=list[ReadSupportConversation])
async def list_conversations(
    db: db_dependency,
    current_user: current_user_dependency,
    auth: authorization_header,
) -> list[ReadSupportConversation]:
    """
    
    """
    conversations = await get_support_conversations(db=db, current_user=current_user)
    return [
        ReadSupportConversation.model_validate(conversation)
        for conversation in conversations
    ]


@conversation_router.get(
    "/{conversation_id}", response_model=ReadSupportConversationMessages
)
async def get_conversation_messages(
    conversation_id: UUID,
    db: db_dependency,
    current_user: current_user_dependency,
    auth: authorization_header,
) -> ReadSupportConversationMessages:
    """
    Retrieve a specific support conversation by its ID.
    """
    conversation = await get_support_conversation_by_id(
        conversation_id=conversation_id, db=db, current_user=current_user
    )
    return ReadSupportConversationMessages.model_validate(conversation)


@conversation_router.delete("/{conversation_id}", response_model=dict)
async def delete_conversation(
    conversation_id: UUID,
    db: db_dependency,
    current_user: current_user_dependency,
    auth: authorization_header,
) -> dict:
    """
    Delete a support conversation by its ID.
    """
    deleted_conversation = await delete_support_conversation(
        conversation_id=conversation_id, db=db, current_user=current_user
    )
    if deleted_conversation:
        return {"message": "Support conversation deleted successfully."}
    return {
        "message": "failed to delete support conversation with id: {conversation_id}"
    }


@conversation_router.post("/chat/{conversation_id}", response_model=ReadSupportMessage)
async def get_bot_response_endpoint(
    conversation_id: UUID,
    db: db_dependency,
    current_user: current_user_dependency,
    auth: authorization_header,
    message: str = Body(..., embed=True, description="The user's message to the bot"),
) -> ReadSupportMessage:
    """
    Get a bot response for a specific support conversation.
    """
    if not message:
        raise ValueError("Message cannot be empty")

    bot_response = await get_bot_response(
        db=db,
        current_user=current_user,
        message=message,
        conversation_id=conversation_id,
    )
    return ReadSupportMessage.model_validate(bot_response)


@conversation_router.post("/public/chat", response_model=ReadPublicSupportMessage)
async def public_bot_response_endpoint(
    message: str = Body(..., embed=True, description="The user's message to the bot"),
    last_conversation_id: Optional[str] = Body(
        None, description="The ID of the last conversation for context"
    ),
) -> ReadPublicSupportMessage:
    """
    Get a bot response for an anonymous user.
    """
    if not message:
        raise ValueError("Message cannot be empty")

    bot_response = await public_bot_response(
        message=message,
        last_conversation_id=last_conversation_id,
    )
    return bot_response
