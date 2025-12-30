"""Order history API endpoints."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Call, Order, OrderItem
from pydantic import BaseModel


router = APIRouter()


class OrderItemResponse(BaseModel):
    """Order item response model."""
    id: int
    item_name: str
    quantity: int
    modifiers: list[str] | None = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response model."""
    id: int
    status: str
    raw_text: str | None = None
    structured_order: dict | None = None
    created_at: str
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class CallResponse(BaseModel):
    """Call response model."""
    id: int
    call_sid: str
    started_at: str
    ended_at: str | None = None
    status: str
    transcript: str | None = None
    orders: List[OrderResponse] = []

    class Config:
        from_attributes = True


@router.get("/api/orders/history", response_model=List[CallResponse])
async def get_order_history(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all calls with their orders."""
    result = await db.execute(
        select(Call)
        .options(
            selectinload(Call.orders).selectinload(Order.items)
        )
        .order_by(desc(Call.started_at))
        .limit(limit)
    )
    calls = result.scalars().all()
    
    # Convert to response models
    call_responses = []
    for call in calls:
        order_responses = []
        for order in call.orders:
            item_responses = []
            for item in order.items:
                # Handle modifiers - ensure it's a list or None
                modifiers = item.modifiers
                if modifiers is not None and not isinstance(modifiers, list):
                    modifiers = list(modifiers) if modifiers else None
                
                item_responses.append(
                    OrderItemResponse(
                        id=item.id,
                        item_name=item.item_name,
                        quantity=item.quantity,
                        modifiers=modifiers
                    )
                )
            
            order_responses.append(
                OrderResponse(
                    id=order.id,
                    status=order.status,
                    raw_text=order.raw_text,
                    structured_order=order.structured_order,
                    created_at=order.created_at.isoformat() if order.created_at else "",
                    items=item_responses
                )
            )
        
        call_responses.append(
            CallResponse(
                id=call.id,
                call_sid=call.call_sid,
                started_at=call.started_at.isoformat() if call.started_at else "",
                ended_at=call.ended_at.isoformat() if call.ended_at else None,
                status=call.status,
                transcript=call.transcript,
                orders=order_responses
            )
        )
    
    return call_responses

