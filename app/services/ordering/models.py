"""Order models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class OrderItem(BaseModel):
    """Structured order item."""

    item_name: str
    quantity: int = 1
    modifiers: List[str] = []


class ParsedOrder(BaseModel):
    """Parsed order structure."""

    items: List[OrderItem]
    raw_text: Optional[str] = None
    is_valid: bool = True
    validation_errors: List[str] = []

