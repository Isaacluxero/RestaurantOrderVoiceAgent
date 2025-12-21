"""Menu repository."""
from typing import List, Optional
from app.services.menu.base import Menu, MenuItem, MenuProvider


class MenuRepository:
    """Repository for menu operations."""

    def __init__(self, provider: MenuProvider):
        self.provider = provider

    async def get_menu(self) -> Menu:
        """Get the full menu."""
        return await self.provider.get_menu()

    async def validate_item(self, item_name: str) -> bool:
        """Check if an item exists."""
        return await self.provider.validate_item(item_name)

    async def get_item_options(self, item_name: str) -> List[str]:
        """Get item options."""
        return await self.provider.get_item_options(item_name)

    async def get_item_by_name(self, item_name: str) -> Optional[MenuItem]:
        """Get item by name."""
        return await self.provider.get_item_by_name(item_name)

    async def get_menu_text(self) -> str:
        """Get menu as formatted text for LLM context."""
        menu = await self.get_menu()
        lines = ["Menu:"]
        for category in menu.categories:
            lines.append(f"\n{category.title()}:")
            for item in menu.items:
                if item.category == category:
                    price_str = f" ${item.price:.2f}" if item.price else ""
                    desc_str = f" - {item.description}" if item.description else ""
                    options_str = f" (Options: {', '.join(item.options)})" if item.options else ""
                    lines.append(f"  - {item.name}{price_str}{desc_str}{options_str}")
        return "\n".join(lines)

