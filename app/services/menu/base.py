"""Menu provider interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class MenuItem(BaseModel):
    """Menu item model."""

    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    options: List[str] = []  # Available modifiers/options


class Menu(BaseModel):
    """Menu model."""

    items: List[MenuItem]
    categories: List[str] = []


class MenuProvider(ABC):
    """Abstract base class for menu providers."""

    @abstractmethod
    async def get_menu(self) -> Menu:
        """Get the full menu."""
        pass

    @abstractmethod
    async def validate_item(self, item_name: str) -> bool:
        """Check if an item exists in the menu."""
        pass

    @abstractmethod
    async def get_item_options(self, item_name: str) -> List[str]:
        """Get available options/modifiers for an item."""
        pass

    @abstractmethod
    async def get_item_by_name(self, item_name: str) -> Optional[MenuItem]:
        """Get a menu item by name."""
        pass

