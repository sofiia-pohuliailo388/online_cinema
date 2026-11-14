from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from src.orders.models import StatusEnum


class OrderItemReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    price_at_order: Decimal


class OrderReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: StatusEnum
    created_at: datetime
    total_amount: Decimal | None = None
    order_items: list[OrderItemReadSchema]


class OrderForCreatedResponseSchema(BaseModel):
    id: int
    status: StatusEnum
    total_amount: Decimal | None


class CreatedResponseSchema(BaseModel):
    order: OrderForCreatedResponseSchema
    excluded_movie_ids: list[int]
