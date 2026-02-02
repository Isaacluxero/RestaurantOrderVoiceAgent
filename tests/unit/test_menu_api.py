"""Unit tests for menu API endpoints."""
import pytest


class TestMenuAPI:
    """Test menu API endpoints."""

    def test_get_menu_success(self, authenticated_client):
        """Test GET /api/menu returns full menu."""
        response = authenticated_client.get("/api/menu")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "categories" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["categories"], list)

    def test_get_menu_includes_test_items(self, authenticated_client):
        """Test that menu includes items from test fixture."""
        response = authenticated_client.get("/api/menu")

        assert response.status_code == 200
        data = response.json()

        # Should have 3 items from test menu
        assert len(data["items"]) == 3

        # Check item names
        item_names = [item["name"] for item in data["items"]]
        assert "burger" in item_names
        assert "fries" in item_names
        assert "soda" in item_names

        # Check categories
        assert len(data["categories"]) == 3
        assert "mains" in data["categories"]
        assert "sides" in data["categories"]
        assert "drinks" in data["categories"]

    def test_create_item_success(self, authenticated_client):
        """Test POST /api/menu/items creates new item."""
        new_item = {
            "name": "pizza",
            "description": "Delicious pizza",
            "price": 12.99,
            "category": "mains",
            "options": ["large", "extra cheese"]
        }

        response = authenticated_client.post("/api/menu/items", json=new_item)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pizza"
        assert data["description"] == "Delicious pizza"
        assert data["price"] == 12.99
        assert data["category"] == "mains"
        assert data["options"] == ["large", "extra cheese"]

    def test_create_item_appears_in_menu(self, authenticated_client):
        """Test that created item appears in menu."""
        new_item = {
            "name": "salad",
            "description": "Fresh salad",
            "price": 8.99,
            "category": "sides",
            "options": []
        }

        # Create item
        response = authenticated_client.post("/api/menu/items", json=new_item)
        assert response.status_code == 200

        # Get menu and verify item exists
        menu_response = authenticated_client.get("/api/menu")
        data = menu_response.json()
        item_names = [item["name"] for item in data["items"]]
        assert "salad" in item_names

    def test_create_item_invalid_data(self, authenticated_client):
        """Test POST with missing required fields returns 422."""
        # Missing price and category
        invalid_item = {
            "name": "invalid_item",
            "description": "Missing required fields"
        }

        response = authenticated_client.post("/api/menu/items", json=invalid_item)
        assert response.status_code == 422  # Validation error

    def test_create_item_duplicate_name(self, authenticated_client):
        """Test creating item with existing name returns 400."""
        # Try to create duplicate "burger" (exists in test menu)
        duplicate_item = {
            "name": "burger",
            "description": "Duplicate burger",
            "price": 9.99,
            "category": "mains",
            "options": []
        }

        response = authenticated_client.post("/api/menu/items", json=duplicate_item)
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_update_item_success(self, authenticated_client):
        """Test PUT /api/menu/items/{item_name} updates item."""
        updated_item = {
            "name": "burger",
            "description": "Updated burger description",
            "price": 11.99,  # Changed from 10.00
            "category": "mains",
            "options": ["no onions", "well done"]
        }

        response = authenticated_client.put("/api/menu/items/burger", json=updated_item)

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 11.99
        assert data["description"] == "Updated burger description"

    def test_update_item_reflects_in_menu(self, authenticated_client):
        """Test that updated item changes appear in menu."""
        updated_item = {
            "name": "fries",
            "description": "Updated fries",
            "price": 4.99,  # Changed from 3.50
            "category": "sides",
            "options": ["large"]
        }

        # Update item
        response = authenticated_client.put("/api/menu/items/fries", json=updated_item)
        assert response.status_code == 200

        # Get menu and verify update
        menu_response = authenticated_client.get("/api/menu")
        data = menu_response.json()

        fries_item = next((item for item in data["items"] if item["name"] == "fries"), None)
        assert fries_item is not None
        assert fries_item["price"] == 4.99
        assert fries_item["description"] == "Updated fries"

    def test_update_item_not_found(self, authenticated_client):
        """Test PUT with non-existent item returns 404."""
        updated_item = {
            "name": "nonexistent",
            "description": "Does not exist",
            "price": 9.99,
            "category": "mains",
            "options": []
        }

        response = authenticated_client.put("/api/menu/items/nonexistent", json=updated_item)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_item_success(self, authenticated_client):
        """Test DELETE /api/menu/items/{item_name} removes item."""
        # First verify item exists
        menu_response = authenticated_client.get("/api/menu")
        item_names = [item["name"] for item in menu_response.json()["items"]]
        assert "soda" in item_names

        # Delete item
        response = authenticated_client.delete("/api/menu/items/soda")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "soda" in data["message"]

        # Verify item removed from menu
        menu_response = authenticated_client.get("/api/menu")
        item_names = [item["name"] for item in menu_response.json()["items"]]
        assert "soda" not in item_names

    def test_delete_item_not_found(self, authenticated_client):
        """Test DELETE with non-existent item succeeds silently."""
        # Note: Current implementation doesn't raise error for non-existent items
        # It silently succeeds (no-op)
        response = authenticated_client.delete("/api/menu/items/nonexistent_item")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_menu_categories_update_with_operations(self, authenticated_client):
        """Test that categories automatically update with item operations."""
        # Add item with new category
        new_item = {
            "name": "ice cream",
            "description": "Frozen dessert",
            "price": 5.99,
            "category": "desserts",  # New category
            "options": ["vanilla", "chocolate"]
        }

        authenticated_client.post("/api/menu/items", json=new_item)

        # Get menu and verify new category exists
        menu_response = authenticated_client.get("/api/menu")
        data = menu_response.json()
        assert "desserts" in data["categories"]
