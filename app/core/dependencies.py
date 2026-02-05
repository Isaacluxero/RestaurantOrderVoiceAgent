"""FastAPI dependencies."""
from app.core.config import settings
from app.services.menu.repository import MenuRepository
from app.services.menu.in_memory_menu import InMemoryMenuProvider


# Singleton instance of MenuRepository to avoid reloading menu.yaml on every request
_menu_repository: MenuRepository = None


def get_menu_repository() -> MenuRepository:
    """Get menu repository instance (singleton)."""
    global _menu_repository
    if _menu_repository is None:
        _menu_repository = MenuRepository(provider=InMemoryMenuProvider())
    return _menu_repository

