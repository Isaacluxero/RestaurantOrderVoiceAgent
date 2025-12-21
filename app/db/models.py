"""Database models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Call(Base):
    """Call metadata model."""

    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, unique=True, index=True, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="in_progress", nullable=False)  # in_progress, completed, failed
    transcript = Column(Text, nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="call")


class Order(Base):
    """Order model."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, confirmed, cancelled
    raw_text = Column(Text, nullable=True)
    structured_order = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    call = relationship("Call", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """Order item model."""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    modifiers = Column(JSON, nullable=True)  # List of modifier strings

    # Relationships
    order = relationship("Order", back_populates="items")

