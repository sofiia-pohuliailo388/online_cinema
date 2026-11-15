
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.orders.models import StatusEnum
from src.orders.schemas import (
    CreatedResponseSchema,
    OrderForCreatedResponseSchema,
    OrderItemReadSchema,
    OrderReadSchema,
)


def test_order_item_schema_from_attributes() -> None:
    item = SimpleNamespace(
        id=1,
        movie_id=10,
        price_at_order=Decimal("12.50"),
    )

    schema = OrderItemReadSchema.model_validate(item)

    assert schema.id == 1
    assert schema.movie_id == 10
    assert schema.price_at_order == Decimal("12.50")


def test_order_read_schema_from_attributes() -> None:
    created_at = datetime(2026, 11, 15, 12, 30)

    order = SimpleNamespace(
        id=1,
        user_id=5,
        status=StatusEnum.PENDING,
        created_at=created_at,
        total_amount=Decimal("25.00"),
        order_items=[
            SimpleNamespace(
                id=2,
                movie_id=10,
                price_at_order=Decimal("25.00"),
            )
        ],
    )

    schema = OrderReadSchema.model_validate(order)

    assert schema.id == 1
    assert schema.user_id == 5
    assert schema.status == StatusEnum.PENDING
    assert schema.created_at == created_at
    assert schema.total_amount == Decimal("25.00")
    assert len(schema.order_items) == 1
    assert schema.order_items[0].movie_id == 10


def test_order_read_schema_without_total_amount() -> None:
    schema = OrderReadSchema.model_validate(
        {
            "id": 1,
            "user_id": 5,
            "status": "pending",
            "created_at": "2026-11-15T12:30:00",
            "order_items": [],
        }
    )

    assert schema.total_amount is None
    assert schema.order_items == []


def test_order_read_schema_invalid_status() -> None:
    with pytest.raises(ValidationError):
        OrderReadSchema.model_validate(
            {
                "id": 1,
                "user_id": 5,
                "status": "unknown",
                "created_at": "2026-11-15T12:30:00",
                "order_items": [],
            }
        )


def test_created_order_schema() -> None:
    schema = OrderForCreatedResponseSchema(
        id=1,
        status=StatusEnum.PENDING,
        total_amount=Decimal("19.99"),
    )

    assert schema.id == 1
    assert schema.status == StatusEnum.PENDING
    assert schema.total_amount == Decimal("19.99")


def test_created_response_schema_with_excluded_movies() -> None:
    schema = CreatedResponseSchema.model_validate(
        {
            "order": {
                "id": 1,
                "status": "pending",
                "total_amount": "19.99",
            },
            "excluded_movie_ids": [3, 7],
        }
    )

    assert schema.order.id == 1
    assert schema.order.total_amount == Decimal("19.99")
    assert schema.excluded_movie_ids == [3, 7]


def test_created_response_schema_missing_order() -> None:
    with pytest.raises(ValidationError):
        CreatedResponseSchema.model_validate(
            {"excluded_movie_ids": []}
        )
