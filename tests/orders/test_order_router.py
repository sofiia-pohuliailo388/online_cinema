
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.cart.models import CartItem
from src.orders.models import Order, OrderItem, StatusEnum


ORDERS_URL = "/api/v1/orders"
USER_ORDERS_URL = "/api/v1/users/me/orders"


async def create_test_order(
    db_session: AsyncSession,
    user_id: int,
    movie_id: int,
    status: StatusEnum = StatusEnum.PENDING,
) -> Order:
    order = Order(
        user_id=user_id,
        status=status,
        total_amount=Decimal("12.50"),
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            movie_id=movie_id,
            price_at_order=Decimal("12.50"),
        )
    )
    await db_session.commit()

    return order


async def test_create_order_success(
    client: AsyncClient,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.post(ORDERS_URL)

    body = response.json()
    assert response.status_code == 201
    assert body["order"]["status"] == "pending"
    assert body["order"]["total_amount"] == "12.50"
    assert body["excluded_movie_ids"] == []


async def test_create_order_unauthenticated(
    client: AsyncClient,
) -> None:
    response = await client.post(ORDERS_URL)

    assert response.status_code == 401


async def test_create_order_empty_cart(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    await db_session.execute(
        delete(CartItem).where(
            CartItem.cart_id == order_data["cart"].id
        )
    )
    await db_session.commit()

    response = await client.post(ORDERS_URL)

    assert response.status_code == 409


async def test_create_order_duplicate_pending(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
    )

    response = await client.post(ORDERS_URL)

    assert response.status_code == 409


async def test_list_own_orders_empty(
    client: AsyncClient,
    login_as: Callable[..., Any],
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.get(USER_ORDERS_URL)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
        "pages": 0,
    }


async def test_list_own_orders_success(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
    )

    response = await client.get(USER_ORDERS_URL)

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1


async def test_list_own_orders_unauthenticated(
    client: AsyncClient,
) -> None:
    response = await client.get(USER_ORDERS_URL)

    assert response.status_code == 401


async def test_get_own_order_success(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    order = await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
    )

    response = await client.get(f"{ORDERS_URL}/{order.id}")

    assert response.status_code == 200
    assert response.json()["id"] == order.id
    assert len(response.json()["order_items"]) == 1


async def test_get_own_order_not_found(
    client: AsyncClient,
    login_as: Callable[..., Any],
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.get(f"{ORDERS_URL}/999")

    assert response.status_code == 404


async def test_get_own_order_unauthenticated(
    client: AsyncClient,
) -> None:
    response = await client.get(f"{ORDERS_URL}/999")

    assert response.status_code == 401


async def test_cancel_pending_order(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    order = await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
    )

    response = await client.post(
        f"{ORDERS_URL}/{order.id}/cancel"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


async def test_cancel_paid_order(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.USER)

    order = await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
        status=StatusEnum.PAID,
    )

    response = await client.post(
        f"{ORDERS_URL}/{order.id}/cancel"
    )

    assert response.status_code == 409


async def test_cancel_order_not_found(
    client: AsyncClient,
    login_as: Callable[..., Any],
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.post(
        f"{ORDERS_URL}/999/cancel"
    )

    assert response.status_code == 404


async def test_cancel_order_unauthenticated(
    client: AsyncClient,
) -> None:
    response = await client.post(
        f"{ORDERS_URL}/999/cancel"
    )

    assert response.status_code == 401


async def test_admin_list_orders_success(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.ADMIN)

    await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
    )

    response = await client.get(ORDERS_URL)

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_admin_list_orders_filter_status(
    client: AsyncClient,
    db_session: AsyncSession,
    login_as: Callable[..., Any],
    order_data: dict,
) -> None:
    login_as(UserGroupEnum.ADMIN)

    await create_test_order(
        db_session,
        order_data["user"].id,
        order_data["movie"].id,
        status=StatusEnum.PAID,
    )

    response = await client.get(
        ORDERS_URL,
        params={"status": "paid"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "paid"


async def test_admin_list_orders_forbidden_for_user(
    client: AsyncClient,
    login_as: Callable[..., Any],
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.get(ORDERS_URL)

    assert response.status_code == 403


async def test_admin_list_orders_unauthenticated(
    client: AsyncClient,
) -> None:
    response = await client.get(ORDERS_URL)

    assert response.status_code == 401
