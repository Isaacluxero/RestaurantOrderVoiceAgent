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

    async def _save_menu(self) -> None:
        """Save menu to YAML file."""
        if self._menu is None:
            return

        # Convert menu to dict format
        data = {
            "items": [
                {
                    "name": item.name,
                    "description": item.description,
                    "price": item.price,
                    "category": item.category,
                    "options": item.options
                }
                for item in self._menu.items
            ],
            "categories": self._menu.categories
        }

        # Write to file
        self.menu_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.menu_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    async def add_item(self, item: MenuItem) -> None:
        """Add a new item to the menu."""
        menu = await self._load_menu()

        # Check if item already exists
        if any(i.name.lower() == item.name.lower() for i in menu.items):
            raise ValueError(f"Item '{item.name}' already exists")

        menu.items.append(item)

        # Add category if new
        if item.category and item.category not in menu.categories:
            menu.categories.append(item.category)

        await self._save_menu()

    async def update_item(self, item_name: str, updated_item: MenuItem) -> None:
        """Update an existing menu item."""
        menu = await self._load_menu()

        # Find and update item
        found = False
        for i, item in enumerate(menu.items):
            if item.name.lower() == item_name.lower():
                menu.items[i] = updated_item
                found = True
                break

        if not found:
            raise ValueError(f"Item '{item_name}' not found")

        # Update categories
        all_categories = set(item.category for item in menu.items if item.category)
        menu.categories = sorted(list(all_categories))

        await self._save_menu()

    async def delete_item(self, item_name: str) -> None:
        """Delete a menu item."""
        menu = await self._load_menu()

        # Find and remove item
        item_name_lower = item_name.lower()
        menu.items = [item for item in menu.items if item.name.lower() != item_name_lower]

        # Update categories
        all_categories = set(item.category for item in menu.items if item.category)
        menu.categories = sorted(list(all_categories))

        await self._save_menu()

