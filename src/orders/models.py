from decimal import Decimal
from enum import StrEnum
from typing import List

from sqlalchemy import ForeignKey, String, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.models import Base, TimestampMixin


class StatusEnum(StrEnum):
    """Available order statuses."""

    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base, TimestampMixin):
    """User order containing purchased movie items."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[StatusEnum] = mapped_column(String, default=StatusEnum.PENDING)
    total_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)

    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")
    user: Mapped["User"] = relationship("User")


class OrderItem(Base):
    """Movie included in an order with its price at order creation."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    movie: Mapped["Movie"] = relationship("Movie")
