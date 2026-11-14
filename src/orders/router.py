"""API endpoints for order management (owner: P6)."""
from datetime import datetime

from fastapi import APIRouter, Depends

from accounts.dependencies import CurrentUser, AdminUser
from core.database import DbSession
from core.pagination import PaginationParams, Page
from orders.models import StatusEnum
from orders.schemas import CreatedResponseSchema, OrderReadSchema
from orders.service import (
    create_order,
    get_user_orders,
    get_order_by_id,
    cancel_order,
    get_all_orders
)

router = APIRouter(tags=["Order"])


@router.post("/orders/", status_code=201, response_model=CreatedResponseSchema)
async def create_order_endpoint(
        db: DbSession,
        user: CurrentUser,
) -> CreatedResponseSchema:
    """Create an order from the authenticated user's cart."""
    order = await create_order(db, user_id=user.id)
    return CreatedResponseSchema.model_validate(order)


@router.get("/users/me/orders/", status_code=200, response_model=Page[OrderReadSchema])
async def get_list_own_orders(
        db: DbSession,
        user: CurrentUser,
        pagination: PaginationParams = Depends()
) -> Page[OrderReadSchema]:
    """List orders belonging to the authenticated user."""
    orders, total = await get_user_orders(db, user_id=user.id, pagination=pagination)

    items = [
        OrderReadSchema.model_validate(order)
        for order in orders
    ]

    return Page.create(items=items, total=total, params=pagination)


@router.get("/orders/{order_id}/", status_code=200, response_model=OrderReadSchema)
async def get_own_order_by_id(db: DbSession, user: CurrentUser, order_id: int) -> OrderReadSchema:
    """Retrieve an order belonging to the authenticated user."""
    order = await get_order_by_id(db, user_id=user.id, order_id=order_id)
    return OrderReadSchema.model_validate(order)


@router.post("/orders/{order_id}/cancel/", status_code=200, response_model=OrderReadSchema)
async def cancel_own_order(db: DbSession, user: CurrentUser, order_id: int) -> OrderReadSchema:
    """Cancel a pending order belonging to the authenticated user."""
    order = await cancel_order(db, user_id=user.id, order_id=order_id)
    return OrderReadSchema.model_validate(order)


@router.get("/orders/", status_code=200, response_model=Page[OrderReadSchema])
async def get_all_orders_for_admin(
        db: DbSession,
        admin: AdminUser,
        pagination: PaginationParams = Depends(),
        user_id: int | None = None,
        status: StatusEnum | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
) -> Page[OrderReadSchema]:
    """List and filter all orders. Accessible to administrators only."""
    orders, total = await get_all_orders(
        db,
        pagination=pagination,
        user_id=user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    items = [
        OrderReadSchema.model_validate(order)
        for order in orders
    ]

    return Page.create(items=items, total=total, params=pagination)
