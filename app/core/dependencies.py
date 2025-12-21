"""FastAPI dependencies."""
from app.core.config import settings
from app.services.menu.repository import MenuRepository
from app.services.menu.in_memory_menu import InMemoryMenuProvider


def get_menu_repository() -> MenuRepository:
    """Get menu repository instance."""
    return MenuRepository(provider=InMemoryMenuProvider())

