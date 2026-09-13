"""
Exceptions for the support conversation service.
"""

from uuid import UUID


class SupportConversationNotFound(Exception):
    """Exception raised when a support conversation is not found."""

    def __init__(self, conversation_id: UUID):
        self.conversation_id = conversation_id
        self.message = f"Support conversation with ID {conversation_id} not found."
        super().__init__(self.message)
