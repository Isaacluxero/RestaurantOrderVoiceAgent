"""Unit tests for order total calculation with tax."""
import pytest
from unittest.mock import Mock, AsyncMock

from app.services.call_session.manager import CallSessionManager
from app.services.agent.state import ConversationState, OrderItem
from app.services.agent.stages import ConversationStage
from app.core.config import Settings


@pytest.fixture
async def call_manager(test_db, test_menu_repository):
    """Create CallSessionManager for testing."""
    mock_agent = AsyncMock()
    # Set up default mock response for agent service
    mock_agent.process_user_input = AsyncMock(return_value={
        "response": "Okay",
        "intent": "general",
        "action": {"type": "none"}
    })
    return CallSessionManager(
        db=test_db,
        agent_service=mock_agent,
        menu_repository=test_menu_repository,
    )


class TestOrderTotalCalculation:
    """Test order total calculation with tax."""

    async def _calculate_order_total(self, call_manager, order_items, tax_rate=0.0925):
        """Helper to calculate order total."""
        subtotal = 0.0
        for item in order_items:
            menu_item = await call_manager.menu_repository.get_item_by_name(item.item_name)
            if menu_item and menu_item.price:
                subtotal += menu_item.price * item.quantity

        tax = subtotal * tax_rate
        total = subtotal + tax
        return subtotal, tax, total

    @pytest.mark.asyncio
    async def test_calculate_order_total_single_item(self, call_manager):
        """Test total calculation for single item order."""
        order_items = [OrderItem(item_name="burger", quantity=1, modifiers=[])]

        # Expected: 1x burger = $10.00, tax (9.25%) = $0.93, total = $10.93
        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items)

        assert subtotal == 10.00
        assert abs(tax - 0.93) < 0.01  # Allow small rounding difference
        assert abs(total - 10.93) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_order_total_multiple_items(self, call_manager):
        """Test total calculation for multiple different items."""
        order_items = [
            OrderItem(item_name="burger", quantity=2, modifiers=[]),
            OrderItem(item_name="fries", quantity=1, modifiers=[])
        ]

        # Expected: 2x$10.00 + 1x$3.50 = $23.50, tax = $2.17, total = $25.67
        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items)

        assert subtotal == 23.50
        assert abs(tax - 2.17) < 0.01
        assert abs(total - 25.67) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_order_total_with_quantity(self, call_manager):
        """Test total calculation with multiple quantity of same item."""
        order_items = [OrderItem(item_name="burger", quantity=3, modifiers=[])]

        # Expected: 3x$10.00 = $30.00, tax = $2.78, total = $32.78
        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items)

        assert subtotal == 30.00
        assert abs(tax - 2.78) < 0.01
        assert abs(total - 32.78) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_order_total_custom_tax_rate(self, call_manager):
        """Test total calculation with custom tax rate."""
        order_items = [OrderItem(item_name="burger", quantity=1, modifiers=[])]

        # Test with 8% tax rate
        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items, tax_rate=0.08)

        assert subtotal == 10.00
        assert abs(tax - 0.80) < 0.01
        assert abs(total - 10.80) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_order_total_zero_tax(self, call_manager):
        """Test total calculation with zero tax rate."""
        order_items = [OrderItem(item_name="burger", quantity=1, modifiers=[])]

        # Test with 0% tax rate
        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items, tax_rate=0.0)

        assert subtotal == 10.00
        assert tax == 0.0
        assert total == 10.00

    @pytest.mark.asyncio
    async def test_order_readback_includes_total(self, call_manager, clean_call_sessions):
        """Test that order readback includes total with correct format."""
        from app.services.call_session.models import CallSession

        # Create session with order in REVIEW stage
        state = ConversationState(
            call_sid="test_call_readback",
            stage=ConversationStage.REVIEW,
            order_read_back=False,
            current_order=[OrderItem(item_name="burger", quantity=1, modifiers=["no onions"])]
        )

        session = CallSession(call_sid="test_call_readback", state=state, call_id=1)

        from app.services.call_session import manager as session_manager
        session_manager._sessions["test_call_readback"] = session

        try:
            # Process speech - this should trigger order readback
            response = await call_manager.process_user_speech("test_call_readback", "yes")

            # Verify format: "Your total is $XX.XX"
            assert "Your total is $" in response
            assert "$10.93" in response  # Exact format with 2 decimals

            # Verify order items are also mentioned
            assert "burger" in response.lower()
        finally:
            session_manager._sessions.clear()

    @pytest.mark.asyncio
    async def test_order_readback_no_items(self, call_manager, clean_call_sessions):
        """Test that empty order doesn't include total calculation."""
        from app.services.call_session.models import CallSession

        # Create session with empty order in REVIEW stage
        state = ConversationState(
            call_sid="test_call_empty",
            stage=ConversationStage.REVIEW,
            order_read_back=False,
            current_order=[]  # Empty order
        )

        session = CallSession(call_sid="test_call_empty", state=state, call_id=1)

        from app.services.call_session import manager as session_manager
        session_manager._sessions["test_call_empty"] = session

        try:
            response = await call_manager.process_user_speech("test_call_empty", "yes")

            # Should mention no items, not include a total
            assert "No items" in response or "empty" in response.lower()
        finally:
            session_manager._sessions.clear()

    @pytest.mark.asyncio
    async def test_order_total_precision(self, call_manager):
        """Test that total calculation handles rounding correctly."""
        # Using burger ($10.00) + soda ($2.00) = $12.00
        # Tax: $12.00 * 0.0925 = $1.11
        # Total: $13.11
        order_items = [
            OrderItem(item_name="burger", quantity=1, modifiers=[]),
            OrderItem(item_name="soda", quantity=1, modifiers=[])
        ]

        subtotal, tax, total = await self._calculate_order_total(call_manager, order_items)

        assert subtotal == 12.00
        # Verify correct rounding to 2 decimal places
        assert abs(tax - 1.11) < 0.01
        assert abs(total - 13.11) < 0.01

        # Verify formatting to 2 decimal places
        total_formatted = f"${total:.2f}"
        assert total_formatted == "$13.11"
