from datetime import datetime
from typing import List

from sqlalchemy import ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.models import Base


class Cart(Base):
    """Shopping cart belonging to a single user."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    user: Mapped["User"] = relationship("User")
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart")


class CartItem(Base):
    """Movie added to a user's shopping cart."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cart: Mapped["Cart"] = relationship("Cart", back_populates="cart_items")
    movie: Mapped["Movie"] = relationship("Movie")

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)
