"""Conversation state management."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.agent.stages import ConversationStage


class OrderItem(BaseModel):
    """Order item in conversation state."""

    item_name: str
    quantity: int = 1
    modifiers: List[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    """Conversation state for the agent."""

    call_sid: str
    transcript: List[str] = Field(default_factory=list)  # List of conversation turns
    current_order: List[OrderItem] = Field(default_factory=list)  # Items currently in the order
    stage: ConversationStage = ConversationStage.GREETING  # Current conversation stage
    menu_context: Optional[str] = None  # Menu text for LLM context
    pending_modifiers_item_name: Optional[str] = None  # If set, we're waiting for modifiers/customizations for this item
    pending_modifiers_item_index: Optional[int] = None  # Index into current_order for pending modifiers item
    order_read_back: bool = False  # Flag to track if order has been read back in REVIEW stage

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
        self.order_read_back = False
    
    def clear_pending_modifiers(self) -> None:
        """Clear pending modifiers state."""
        self.pending_modifiers_item_name = None
        self.pending_modifiers_item_index = None
    
    def has_items(self) -> bool:
        """Check if order has any items."""
        return len(self.current_order) > 0
    
    def get_order_summary(self) -> str:
        """Get a text summary of the current order."""
        if not self.current_order:
            return "No items in order yet."
        lines = []
        for item in self.current_order:
            mod_str = f" (notes: {', '.join(item.modifiers)})" if item.modifiers else ""
            qty_str = f"{item.quantity}x " if item.quantity > 1 else ""
            lines.append(f"- {qty_str}{item.item_name}{mod_str}")
        return "\n".join(lines)

