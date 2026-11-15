from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from src.payments.models import PaymentStatus


class PaymentItemReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_item_id: int
    price_at_payment: Decimal


class PaymentReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    order_id: int
    created_at: datetime
    status: PaymentStatus
    amount: Decimal
    external_payment_id: str | None
    items: list[PaymentItemReadSchema]


class CheckoutResponseSchema(BaseModel):
    checkout_url: str


class PaymentHintSchema(BaseModel):
    message: str
