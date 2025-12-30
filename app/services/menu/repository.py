"""Menu repository."""
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.services.menu.base import Menu, MenuItem, MenuProvider


class MenuRepository:
    """Repository for menu operations."""

    def __init__(self, provider: MenuProvider):
        self.provider = provider
        self._item_requirements: Optional[Dict[str, Any]] = None

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

    def _load_item_requirements(self) -> Dict[str, Any]:
        """Load item requirements from JSON file."""
        if self._item_requirements is None:
            requirements_file = Path(__file__).parent / "data" / "item_requirements.json"
            if requirements_file.exists():
                with open(requirements_file, 'r') as f:
                    self._item_requirements = json.load(f)
            else:
                # Default empty requirements if file doesn't exist
                self._item_requirements = {"items": {}, "rules": {}}
        return self._item_requirements

    async def get_item_requirements(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Get requirements for a specific item."""
        requirements = self._load_item_requirements()
        item_name_lower = item_name.lower().strip()
        return requirements.get("items", {}).get(item_name_lower)

    async def get_item_requirements_text(self) -> str:
        """Get item requirements as formatted text for LLM context."""
        requirements = self._load_item_requirements()
        lines = ["Item Requirements and Rules:"]
        
        # Add item-specific requirements
        items_config = requirements.get("items", {})
        if items_config:
            lines.append("\nItem Requirements:")
            for item_name, item_config in items_config.items():
                lines.append(f"\n{item_name}:")
                if item_config.get("required_components"):
                    lines.append(f"  Required: {', '.join(item_config['required_components'])}")
                if item_config.get("size_required"):
                    lines.append(f"  Size required: Yes")
                if item_config.get("description"):
                    lines.append(f"  Description: {item_config['description']}")
        
        # Add rules
        rules = requirements.get("rules", {})
        if rules:
            lines.append("\nGeneral Rules:")
            for rule_name, rule_config in rules.items():
                if isinstance(rule_config, dict) and rule_config.get("description"):
                    lines.append(f"  {rule_name}: {rule_config['description']}")
        
        return "\n".join(lines)

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

