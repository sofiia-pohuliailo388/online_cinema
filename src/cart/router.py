from fastapi import APIRouter

from src.accounts.dependencies import CurrentUser
from src.cart.models import Cart
from src.cart.schemas import CartItemCreateSchema, CartReadSchema
from src.cart.service import (
    add_movie_in_cart,
    get_cart_with_items,
    remove_movie_from_cart,
    clear_cart
)
from src.core.database import DbSession

router = APIRouter(tags=["Cart"])


@router.post("/cart/items", status_code=201)
async def add_movie_to_cart(
        db: DbSession,
        user: CurrentUser,
        movie_data: CartItemCreateSchema,
) -> None:
    await add_movie_in_cart(db, user_id=user.id, movie_id=movie_data.movie_id)


@router.get("/cart/", status_code=200, response_model=CartReadSchema)
async def get_cart(db: DbSession, user: CurrentUser) -> Cart:
    return await get_cart_with_items(db, user_id=user.id)


@router.delete("/cart/items/{movie_id}/", status_code=204)
async def delete_movie_from_cart(db: DbSession, user: CurrentUser, movie_id: int) -> None:
    await remove_movie_from_cart(db, user_id=user.id, movie_id=movie_id)


@router.delete("/cart/", status_code=204)
async def delete_all_movies_from_cart(db: DbSession, user: CurrentUser) -> None:
    await clear_cart(db, user_id=user.id)
