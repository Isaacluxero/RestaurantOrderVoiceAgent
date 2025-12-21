"""Order validation service."""
from typing import List, Optional
from app.services.ordering.models import OrderItem
from app.services.menu.repository import MenuRepository


class OrderValidator:
    """Service for validating orders."""

    def __init__(self, menu_repository: MenuRepository):
        self.menu_repository = menu_repository

    async def validate_item_exists(self, item_name: str) -> bool:
        """Check if an item exists in the menu."""
        return await self.menu_repository.validate_item(item_name)

    async def get_clarification_needed(
        self, item: OrderItem
    ) -> Optional[str]:
        """
        Determine if clarification is needed for an item.

        Returns:
            Question string if clarification needed, None otherwise
        """
        # Check if item exists
        if not await self.validate_item_exists(item.item_name):
            return f"I don't see '{item.item_name}' on our menu. Could you check the menu or try something else?"

        # Check if item has required options that weren't specified
        # For MVP, we'll keep this simple - just validate existence
        # Future: could check for required modifiers (e.g., size for drinks)

        return None

    async def suggest_alternatives(
        self, invalid_item_name: str, limit: int = 3
    ) -> List[str]:
        """
        Suggest alternative menu items for an invalid item name.

        Args:
            invalid_item_name: The invalid item name
            limit: Maximum number of suggestions

        Returns:
            List of suggested item names
        """
        menu = await self.menu_repository.get_menu()
        invalid_lower = invalid_item_name.lower()

        # Simple fuzzy matching - find items with similar names
        suggestions = []
        for item in menu.items:
            item_lower = item.name.lower()
            # Check if invalid name contains part of item name or vice versa
            if (
                invalid_lower in item_lower
                or item_lower in invalid_lower
                or any(word in item_lower for word in invalid_lower.split())
            ):
                suggestions.append(item.name)
                if len(suggestions) >= limit:
                    break

        return suggestions

