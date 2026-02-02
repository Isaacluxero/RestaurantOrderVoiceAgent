"""Unit tests for persistence services (calls and orders)."""
import pytest
from datetime import datetime

from app.services.persistence.calls import CallPersistenceService
from app.services.persistence.orders import OrderPersistenceService


class TestCallPersistence:
    """Test call persistence service."""

    @pytest.mark.asyncio
    async def test_create_call(self, test_db):
        """Test creating a new call record."""
        service = CallPersistenceService(test_db)
        call_sid = "test_call_sid_123"

        call = await service.create_call(call_sid)

        assert call is not None
        assert call.id is not None
        assert call.call_sid == call_sid
        assert call.status == "in_progress"
        assert call.started_at is not None

    @pytest.mark.asyncio
    async def test_get_call_by_sid(self, test_db):
        """Test retrieving call by call_sid."""
        service = CallPersistenceService(test_db)
        call_sid = "test_call_sid_456"

        # Create call
        created_call = await service.create_call(call_sid)

        # Retrieve it
        retrieved_call = await service.get_call_by_sid(call_sid)

        assert retrieved_call is not None
        assert retrieved_call.id == created_call.id
        assert retrieved_call.call_sid == call_sid

    @pytest.mark.asyncio
    async def test_create_call_idempotent(self, test_db):
        """Test that creating same call twice returns existing call."""
        service = CallPersistenceService(test_db)
        call_sid = "test_call_sid_789"

        # Create call first time
        call1 = await service.create_call(call_sid)

        # Try to create again
        call2 = await service.create_call(call_sid)

        # Should return same call
        assert call1.id == call2.id
        assert call1.call_sid == call2.call_sid

    @pytest.mark.asyncio
    async def test_update_call_transcript(self, test_db):
        """Test updating call transcript."""
        service = CallPersistenceService(test_db)
        call_sid = "test_call_sid_abc"

        # Create call
        call = await service.create_call(call_sid)
        assert call.transcript is None

        # Update transcript
        transcript = "User: I want a burger\nAgent: Sure, one burger."
        updated_call = await service.update_call_transcript(call_sid, transcript)

        assert updated_call is not None
        assert updated_call.transcript == transcript

    @pytest.mark.asyncio
    async def test_update_call_status(self, test_db):
        """Test updating call status."""
        service = CallPersistenceService(test_db)
        call_sid = "test_call_sid_def"

        # Create call
        call = await service.create_call(call_sid)
        assert call.status == "in_progress"
        assert call.ended_at is None

        # Update status to completed
        ended_at = datetime.utcnow()
        updated_call = await service.update_call_status(
            call_sid, "completed", ended_at=ended_at
        )

        assert updated_call is not None
        assert updated_call.status == "completed"
        assert updated_call.ended_at == ended_at


class TestOrderPersistence:
    """Test order persistence service."""

    @pytest.mark.asyncio
    async def test_create_order(self, test_db):
        """Test creating a new order linked to a call."""
        # Create a call first
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_order")

        # Create order
        order_service = OrderPersistenceService(test_db)
        raw_text = "I want a burger and fries"
        order = await order_service.create_order(call.id, raw_text=raw_text)

        assert order is not None
        assert order.id is not None
        assert order.call_id == call.id
        assert order.status == "pending"
        assert order.raw_text == raw_text
        assert order.created_at is not None

    @pytest.mark.asyncio
    async def test_get_order_by_id(self, test_db):
        """Test retrieving order with items."""
        # Create call and order
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_order_retrieve")

        order_service = OrderPersistenceService(test_db)
        order = await order_service.create_order(call.id, raw_text="Test order")

        # Retrieve order
        retrieved_order = await order_service.get_order_by_id(order.id)

        assert retrieved_order is not None
        assert retrieved_order.id == order.id
        assert retrieved_order.call_id == call.id
        # Items relationship should be loaded (even if empty)
        assert hasattr(retrieved_order, "items")

    @pytest.mark.asyncio
    async def test_confirm_order(self, test_db):
        """Test confirming an order (status change)."""
        # Create call and order
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_confirm")

        order_service = OrderPersistenceService(test_db)
        order = await order_service.create_order(call.id)
        assert order.status == "pending"

        # Confirm order
        confirmed_order = await order_service.confirm_order(order.id)

        assert confirmed_order is not None
        assert confirmed_order.status == "confirmed"

    @pytest.mark.asyncio
    async def test_add_order_items(self, test_db):
        """Test adding items to an order."""
        # Create call and order
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_items")

        order_service = OrderPersistenceService(test_db)
        order = await order_service.create_order(call.id)

        # Add items
        items_data = [
            {"item_name": "burger", "quantity": 2, "modifiers": None},
            {"item_name": "fries", "quantity": 1, "modifiers": None},
        ]
        order_items = await order_service.add_order_items(order.id, items_data)

        assert len(order_items) == 2
        assert order_items[0].item_name == "burger"
        assert order_items[0].quantity == 2
        assert order_items[1].item_name == "fries"
        assert order_items[1].quantity == 1

    @pytest.mark.asyncio
    async def test_create_order_with_structured_data(self, test_db):
        """Test creating order with structured_order JSON."""
        # Create call
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_structured")

        # Create order with structured data
        order_service = OrderPersistenceService(test_db)
        structured_data = {
            "items": [
                {"name": "burger", "quantity": 1, "modifiers": ["no onions"]},
                {"name": "fries", "quantity": 2, "modifiers": []},
            ]
        }
        order = await order_service.create_order(
            call.id, raw_text="Test order", structured_order=structured_data
        )

        assert order is not None
        assert order.structured_order == structured_data

    @pytest.mark.asyncio
    async def test_order_items_with_modifiers(self, test_db):
        """Test creating OrderItem with modifiers JSON."""
        # Create call and order
        call_service = CallPersistenceService(test_db)
        call = await call_service.create_call("test_call_for_modifiers")

        order_service = OrderPersistenceService(test_db)
        order = await order_service.create_order(call.id)

        # Add item with modifiers
        items_data = [
            {
                "item_name": "burger",
                "quantity": 1,
                "modifiers": ["no onions", "extra cheese"],
            }
        ]
        order_items = await order_service.add_order_items(order.id, items_data)

        # Verify items created with correct modifiers
        assert len(order_items) == 1
        assert order_items[0].item_name == "burger"
        assert order_items[0].quantity == 1
        assert order_items[0].modifiers == ["no onions", "extra cheese"]
        assert isinstance(order_items[0].modifiers, list)
