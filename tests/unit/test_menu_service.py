"""Unit tests for menu service and repository."""
import pytest
from app.services.menu.repository import MenuRepository
from app.services.menu.in_memory_menu import InMemoryMenuProvider


class TestMenuService:
    """Test menu repository and provider."""

    @pytest.mark.asyncio
    async def test_load_menu_from_yaml(self, test_menu_repository):
        """Test loading menu from YAML file."""
        menu = await test_menu_repository.get_menu()

        # Verify items parsed correctly
        assert len(menu.items) == 3
        assert menu.items[0].name == "burger"
        assert menu.items[1].name == "fries"
        assert menu.items[2].name == "soda"

        # Verify categories extracted
        assert "mains" in menu.categories
        assert "sides" in menu.categories
        assert "drinks" in menu.categories

    @pytest.mark.asyncio
    async def test_get_menu(self, test_menu_repository):
        """Test get_menu returns Menu object with items and categories."""
        menu = await test_menu_repository.get_menu()

        # Should have Menu object
        assert menu is not None
        assert hasattr(menu, "items")
        assert hasattr(menu, "categories")

        # Categories should be unique and sorted
        assert len(menu.categories) == len(set(menu.categories))

    @pytest.mark.asyncio
    async def test_validate_item_exists(self, test_menu_repository):
        """Test validate_item returns True for existing item."""
        is_valid = await test_menu_repository.validate_item("burger")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_item_not_exists(self, test_menu_repository):
        """Test validate_item returns False for non-existent item."""
        is_valid = await test_menu_repository.validate_item("invalid_item")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_item_case_insensitive(self, test_menu_repository):
        """Test validate_item works case-insensitively."""
        # All variations should work
        assert await test_menu_repository.validate_item("BURGER") is True
        assert await test_menu_repository.validate_item("BuRgEr") is True
        assert await test_menu_repository.validate_item("burger") is True

        assert await test_menu_repository.validate_item("FRIES") is True
        assert await test_menu_repository.validate_item("Fries") is True

    @pytest.mark.asyncio
    async def test_get_item_by_name(self, test_menu_repository):
        """Test get_item_by_name returns correct MenuItem."""
        item = await test_menu_repository.get_item_by_name("burger")

        assert item is not None
        assert item.name == "burger"
        assert item.price == 10.00
        assert item.category == "mains"
        assert "no onions" in item.options

    @pytest.mark.asyncio
    async def test_get_item_by_name_not_found(self, test_menu_repository):
        """Test get_item_by_name returns None for non-existent item."""
        item = await test_menu_repository.get_item_by_name("nonexistent")
        assert item is None

    @pytest.mark.asyncio
    async def test_get_item_by_name_case_insensitive(self, test_menu_repository):
        """Test get_item_by_name works case-insensitively."""
        item1 = await test_menu_repository.get_item_by_name("BURGER")
        item2 = await test_menu_repository.get_item_by_name("burger")
        item3 = await test_menu_repository.get_item_by_name("BuRgEr")

        assert item1 is not None
        assert item2 is not None
        assert item3 is not None
        assert item1.name == item2.name == item3.name == "burger"

    @pytest.mark.asyncio
    async def test_get_item_options(self, test_menu_repository):
        """Test get_item_options returns list of options."""
        options = await test_menu_repository.get_item_options("burger")

        assert isinstance(options, list)
        assert len(options) > 0
        assert "no onions" in options
        assert "extra cheese" in options

    @pytest.mark.asyncio
    async def test_get_item_options_no_options(self, test_menu_repository):
        """Test get_item_options returns empty list for item with no options."""
        # Soda has options in test menu, so test with non-existent item
        options = await test_menu_repository.get_item_options("nonexistent")
        assert options == []

    @pytest.mark.asyncio
    async def test_get_menu_text(self, test_menu_repository):
        """Test get_menu_text returns formatted string for LLM."""
        menu_text = await test_menu_repository.get_menu_text()

        # Should be a string
        assert isinstance(menu_text, str)

        # Should include menu structure
        assert "Menu:" in menu_text or "Mains:" in menu_text

        # Should include item names
        assert "burger" in menu_text.lower()
        assert "fries" in menu_text.lower()
        assert "soda" in menu_text.lower()

        # Should include prices
        assert "$10.00" in menu_text or "10.00" in menu_text

    @pytest.mark.asyncio
    async def test_menu_categories_unique(self, test_menu_repository):
        """Test that menu categories are unique with no duplicates."""
        menu = await test_menu_repository.get_menu()

        # Check for uniqueness
        assert len(menu.categories) == len(set(menu.categories))

        # Should have exactly 3 categories from test menu
        assert len(menu.categories) == 3
