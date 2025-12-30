"""Conversation stage enumeration."""
from enum import Enum


class ConversationStage(str, Enum):
    """Conversation stages for the ordering flow."""
    
    GREETING = "greeting"  # Initial greeting when call starts
    ORDERING = "ordering"  # Taking orders from customer
    REVIEW = "review"  # Reviewing the entire order before finalizing
    CONCLUSION = "conclusion"  # Finalizing order and saying goodbye
    
    def __str__(self) -> str:
        """Return the string value of the stage."""
        return self.value

