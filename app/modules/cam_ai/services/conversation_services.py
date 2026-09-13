from app.core.models.support_conversations import SupportConversation
from app.core.models.user import User
from app.core.dependencies import db_dependency, current_user_dependency
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..exceptions import SupportConversationNotFound

from ..schemas import (
    CreateSupportConversation,
    UpdateSupportConversation,
    ReadSupportConversation,
)
from uuid import UUID


async def create_support_conversation(
    db: db_dependency,
    current_user: current_user_dependency,
) -> SupportConversation:
    """
    Create a new support conversation.

    Args:
        db: Database session dependency.
        current_user (Employee): The currently authenticated employee.

    Returns:
        SupportConversation: The created support conversation instance.
    """

    # Create a new SupportConversation instance
    new_conversation = SupportConversation(
        user_id=current_user.id,
        title="New Chat",  # Default title for a new conversation
        last_interaction_id=None,  # Set to None initially
    )

    # Add the new conversation to the database
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)

    return new_conversation


async def get_support_conversations(
    db: db_dependency,
    current_user: current_user_dependency,
) -> list[SupportConversation]:
    """
    Retrieve all support conversations for the current user.

    Args:
        db: Database session dependency.
        current_user (User): The currently authenticated user.
    Returns:
        List[SupportConversation]: A list of support conversation instances.
    """

    conversations = await db.execute(
        select(SupportConversation)
        .where(
            SupportConversation.user_id == current_user.id,
        )
        .order_by(SupportConversation.created_at.desc())
    )
    return conversations.scalars().all()


async def get_support_conversation_by_id(
    conversation_id: UUID,
    db: db_dependency,
    current_user: current_user_dependency,
) -> SupportConversation | None:
    """
    Retrieve a support conversation by its ID.

    Args:
        conversation_id (str): The ID of the support conversation.
        db: Database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        SupportConversation | None: The support conversation instance if found, otherwise None.
    """

    # Query the database for the support conversation with the given ID
    conversation = await db.execute(
        select(SupportConversation)
        .options(selectinload(SupportConversation.messages))
        .where(
            SupportConversation.id == conversation_id,
            SupportConversation.user_id == current_user.id,
        )
    )
    conversation_instance = conversation.scalar_one_or_none()

    if not conversation_instance:
        raise SupportConversationNotFound(conversation_id)

    return conversation_instance


async def update_conversation(
    conversation_id: UUID,
    update_data: UpdateSupportConversation,
    db: db_dependency,
    current_user: current_user_dependency,
) -> SupportConversation | None:
    """
    Update  a support conversation.

    Args:
        conversation_id (str): The ID of the support conversation.
        update_data (UpdateSupportConversation): The data to update the support conversation with.
        db: Database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        SupportConversation | None: The updated support conversation instance if found, otherwise None.
    """

    # Query the database for the support conversation with the given ID
    conversation = await db.execute(
        select(SupportConversation).where(
            SupportConversation.id == conversation_id,
            SupportConversation.user_id == current_user.id,
        )
    )
    conversation_instance = conversation.scalar_one_or_none()

    if conversation_instance:
        # Update the conversation instance with the provided data
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(conversation_instance, field, value)

        # Commit the changes to the database
        await db.commit()
        await db.refresh(conversation_instance)

    return conversation_instance


async def delete_support_conversation(
    conversation_id: UUID,
    db: db_dependency,
    current_user: current_user_dependency,
) -> bool:
    """
    Delete a support conversation by its ID.

    Args:
        conversation_id (UUID): The ID of the support conversation to delete.
        db: Database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        bool: True if the conversation was deleted, False if not found.
    """

    # Query the database for the support conversation with the given ID
    conversation = await db.execute(
        select(SupportConversation).where(
            SupportConversation.id == conversation_id,
            SupportConversation.user_id == current_user.id,
        )
    )
    conversation_instance = conversation.scalar_one_or_none()

    if conversation_instance:
        # Delete the support conversation
        await db.delete(conversation_instance)
        await db.commit()
        return True

    return False
