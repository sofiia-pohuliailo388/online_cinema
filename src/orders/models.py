from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, func, String, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base


if TYPE_CHECKING:
    from src.accounts.models import User
    from src.movies.models import Movie


class StatusEnum(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[StatusEnum] = mapped_column(String, default=StatusEnum.PENDING)
    total_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)

    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="order")
    user: Mapped["User"] = relationship()


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))

    order: Mapped["Order"] = relationship(back_populates="order_items")
    movie: Mapped["Movie"] = relationship()
