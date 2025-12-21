"""Order persistence service."""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Order, OrderItem


class OrderPersistenceService:
    """Service for persisting order data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(
        self,
        call_id: int,
        raw_text: Optional[str] = None,
        structured_order: Optional[Dict[str, Any]] = None,
    ) -> Order:
        """Create a new order."""
        order = Order(
            call_id=call_id,
            status="pending",
            raw_text=raw_text,
            structured_order=structured_order,
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def confirm_order(self, order_id: int) -> Optional[Order]:
        """Confirm an order."""
        order = await self.get_order_by_id(order_id)
        if order:
            order.status = "confirmed"
            await self.db.commit()
            await self.db.refresh(order)
        return order

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID with items."""
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def add_order_items(
        self, order_id: int, items: List[Dict[str, Any]]
    ) -> List[OrderItem]:
        """Add items to an order."""
        order = await self.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order_items = []
        for item_data in items:
            order_item = OrderItem(
                order_id=order_id,
                item_name=item_data["item_name"],
                quantity=item_data.get("quantity", 1),
                modifiers=item_data.get("modifiers"),
            )
            order_items.append(order_item)
            self.db.add(order_item)

        await self.db.commit()
        for item in order_items:
            await self.db.refresh(item)
        return order_items

