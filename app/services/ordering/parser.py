"""Order parsing service."""
from typing import Dict, Any, List, Optional
from app.services.ordering.models import ParsedOrder, OrderItem
from app.services.menu.repository import MenuRepository


class OrderParser:
    """Service for parsing and structuring orders."""

    def __init__(self, menu_repository: MenuRepository):
        self.menu_repository = menu_repository

    async def parse_agent_action(
        self, action: Dict[str, Any], raw_text: Optional[str] = None
    ) -> Optional[OrderItem]:
        """
        Parse an action from the agent into an OrderItem.

        Args:
            action: Action dict from agent response
            raw_text: Original user input (for context)

        Returns:
            OrderItem if action is to add an item, None otherwise
        """
        action_type = action.get("type", "")
        if action_type != "add_item":
            return None

        item_name = action.get("item_name", "").strip()
        if not item_name:
            return None

        quantity = action.get("quantity", 1)
        modifiers = action.get("modifiers", [])
        if isinstance(modifiers, str):
            modifiers = [modifiers]

        return OrderItem(
            item_name=item_name,
            quantity=max(1, int(quantity)) if isinstance(quantity, (int, float)) else 1,
            modifiers=[str(m).strip() for m in modifiers if m],
        )

    async def validate_order_item(self, item: OrderItem) -> tuple[bool, List[str]]:
        """
        Validate an order item against the menu.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check if item exists
        item_exists = await self.menu_repository.validate_item(item.item_name)
        if not item_exists:
            errors.append(f"Item '{item.item_name}' is not on the menu")

        # Check modifiers if item exists
        if item_exists and item.modifiers:
            available_options = await self.menu_repository.get_item_options(item.item_name)
            for modifier in item.modifiers:
                # Normalize for comparison (case-insensitive, partial match)
                modifier_lower = modifier.lower()
                if not any(
                    opt.lower() in modifier_lower or modifier_lower in opt.lower()
                    for opt in available_options
                ):
                    # Don't fail validation for modifiers, just note it
                    # The agent can clarify if needed
                    pass

        return len(errors) == 0, errors

    async def parse_and_validate_order(
        self, items: List[OrderItem], raw_text: Optional[str] = None
    ) -> ParsedOrder:
        """
        Parse and validate a complete order.

        Args:
            items: List of order items
            raw_text: Original order text

        Returns:
            ParsedOrder with validation results
        """
        validation_errors = []
        valid_items = []

        for item in items:
            is_valid, errors = await self.validate_order_item(item)
            if is_valid:
                valid_items.append(item)
            else:
                validation_errors.extend(errors)

        return ParsedOrder(
            items=valid_items,
            raw_text=raw_text,
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
        )

