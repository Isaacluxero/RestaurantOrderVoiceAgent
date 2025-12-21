"""In-memory menu provider."""
import yaml
from pathlib import Path
from typing import List, Optional
from app.services.menu.base import Menu, MenuItem, MenuProvider


class InMemoryMenuProvider(MenuProvider):
    """In-memory menu provider using YAML configuration."""

    def __init__(self, menu_file: Optional[str] = None):
        """Initialize with optional menu file path."""
        if menu_file is None:
            menu_file = Path(__file__).parent / "data" / "menu.yaml"
        self.menu_file = Path(menu_file)
        self._menu: Optional[Menu] = None

    async def _load_menu(self) -> Menu:
        """Load menu from YAML file."""
        if self._menu is None:
            if not self.menu_file.exists():
                # Default menu if file doesn't exist
                self._menu = Menu(
                    items=[
                        MenuItem(
                            name="cheeseburger",
                            description="Classic cheeseburger",
                            price=8.99,
                            category="burgers",
                            options=["no onions", "extra cheese", "no pickles"],
                        ),
                        MenuItem(
                            name="fries",
                            description="Crispy french fries",
                            price=3.99,
                            category="sides",
                            options=["large", "small"],
                        ),
                        MenuItem(
                            name="coca cola",
                            description="Classic cola",
                            price=2.99,
                            category="drinks",
                            options=["large", "medium", "small"],
                        ),
                    ],
                    categories=["burgers", "sides", "drinks"],
                )
            else:
                with open(self.menu_file, "r") as f:
                    data = yaml.safe_load(f)
                    items = [
                        MenuItem(**item) for item in data.get("items", [])
                    ]
                    self._menu = Menu(
                        items=items,
                        categories=data.get("categories", []),
                    )
        return self._menu

    async def get_menu(self) -> Menu:
        """Get the full menu."""
        return await self._load_menu()

    async def validate_item(self, item_name: str) -> bool:
        """Check if an item exists in the menu."""
        menu = await self._load_menu()
        item_name_lower = item_name.lower().strip()
        return any(
            item.name.lower() == item_name_lower for item in menu.items
        )

    async def get_item_options(self, item_name: str) -> List[str]:
        """Get available options/modifiers for an item."""
        item = await self.get_item_by_name(item_name)
        return item.options if item else []

    async def get_item_by_name(self, item_name: str) -> Optional[MenuItem]:
        """Get a menu item by name."""
        menu = await self._load_menu()
        item_name_lower = item_name.lower().strip()
        for item in menu.items:
            if item.name.lower() == item_name_lower:
                return item
        return None

