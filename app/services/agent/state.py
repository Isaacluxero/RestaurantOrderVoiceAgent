"""Conversation state management."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class OrderItem(BaseModel):
    """Order item in conversation state."""

    item_name: str
    quantity: int = 1
    modifiers: List[str] = []


class ConversationState(BaseModel):
    """Conversation state for the agent."""

    call_sid: str
    transcript: List[str] = []  # List of conversation turns
    current_order: List[OrderItem] = []
    pending_clarifications: List[str] = []  # Questions waiting for answers
    stage: str = "greeting"  # greeting, taking_order, confirming, completed
    menu_context: Optional[str] = None  # Menu text for LLM context
    current_item_being_discussed: Optional[str] = None  # Track which item is currently being customized
    current_item_needs_size: bool = False  # Track if current item needs size specification
    current_item_is_complete: bool = False  # Track if current item discussion is complete

    def add_transcript_turn(self, role: str, text: str) -> None:
        """Add a turn to the transcript."""
        self.transcript.append(f"{role}: {text}")

    def get_transcript_text(self) -> str:
        """Get full transcript as text."""
        return "\n".join(self.transcript)

    def add_order_item(self, item: OrderItem) -> None:
        """Add an item to the current order."""
        self.current_order.append(item)

    def clear_order(self) -> None:
        """Clear the current order."""
        self.current_order = []

    def get_order_summary(self) -> str:
        """Get a text summary of the current order."""
        if not self.current_order:
            return "No items in order yet."
        lines = []
        for item in self.current_order:
            mod_str = f" ({', '.join(item.modifiers)})" if item.modifiers else ""
            qty_str = f"{item.quantity}x " if item.quantity > 1 else ""
            lines.append(f"- {qty_str}{item.item_name}{mod_str}")
        return "\n".join(lines)
    
    def clear_current_item_discussion(self) -> None:
        """Clear the current item being discussed."""
        self.current_item_being_discussed = None
        self.current_item_needs_size = False
        self.current_item_is_complete = False

