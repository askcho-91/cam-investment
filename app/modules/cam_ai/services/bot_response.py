from .genai_service import generate_response, generate_title
from .conversation_services import (
    create_support_conversation,
    get_support_conversations,
    get_support_conversation_by_id,
    update_conversation,
    delete_support_conversation,
)
from app.core.models.support_conversations import (
    SupportMessages,
    MessageRole,
    SupportConversation,
)
from ..schemas import CreateSupportMessage, ReadPublicSupportMessage
from uuid import UUID
from ..exceptions import SupportConversationNotFound
from app.core.dependencies import db_dependency, current_user_dependency


async def get_bot_response(
    db: db_dependency,
    current_user: current_user_dependency,
    message: str,
    conversation_id: UUID,
) -> SupportMessages:
    """
    Generate a response from the bot based on the user's message.

    Args:
        db (db_dependency): The database dependency.
        current_user (current_user): The current user.
        message (str): The user's message.
        conversation_id (UUID): The ID of the support conversation.

    Returns:
        SupportMessages: The bot's response.
    """
    conversation = await get_support_conversation_by_id(
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )

    validate_user_message = CreateSupportMessage(
        conversation_id=conversation.id,
        role=MessageRole.user,
        message=message,
    )
    user_message = SupportMessages(**validate_user_message.model_dump())
    db.add(user_message)

    bot_response = generate_response(message, conversation.last_interaction_id)

    # Create a new support message for the bot's response
    validate_bot_message = CreateSupportMessage(
        conversation_id=conversation.id,
        role=MessageRole.bot,
        message=bot_response.output_text,
    )
    bot_message = SupportMessages(**validate_bot_message.model_dump())

    if conversation.last_interaction_id is None:
        title = generate_title(message)
        conversation.title = title

    conversation.last_interaction_id = bot_response.id

    db.add(bot_message)
    await db.commit()
    await db.refresh(bot_message)

    return bot_message


async def public_bot_response(
    message: str, last_conversation_id: str
) -> ReadPublicSupportMessage:
    """
    Generate a response from the bot for an anonymous user.

    Args:
        message (str): The user's message.

    Returns:
        tuple[SupportMessages, UUID]: The bot's response and the conversation ID.
    """
    bot_response = generate_response(
        prompt=message, previous_interaction_id=last_conversation_id
    )

    response = ReadPublicSupportMessage(
        message=bot_response.output_text,
        interaction_id=bot_response.id,
    )

    return response
