from fastapi import APIRouter

from src.core.exceptions import ErrorResponse
from src.accounts.dependencies import CurrentUser, AdminUser
from src.cart.schemas import CartItemCreateSchema, CartReadSchema
from src.cart.service import (
    add_movie_in_cart,
    get_cart_with_items,
    remove_movie_from_cart,
    clear_cart
)
from src.core.database import DbSession

router = APIRouter(tags=["Cart"])


@router.post(
    "/cart/items",
    status_code=201,
    summary="Add movie to cart",
    description=(
            "Add a movie to the authenticated user's shopping cart. "
            "Movies already purchased or already in the cart cannot be added."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Movie not found"},
        409: {"model": ErrorResponse, "description": "Movie already purchased or already in cart"},
    },
)
async def add_movie_to_cart(
        db: DbSession,
        user: CurrentUser,
        movie_data: CartItemCreateSchema,
) -> None:
    await add_movie_in_cart(db, user_id=user.id, movie_id=movie_data.movie_id)


@router.get(
    "/cart",
    status_code=200,
    response_model=CartReadSchema,
    summary="Get my cart",
    description="Retrieve the authenticated user's shopping cart with its movies.",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Cart not found"},
    },
)
async def get_cart(db: DbSession, user: CurrentUser) -> CartReadSchema:
    cart = await get_cart_with_items(db, user_id=user.id)
    return CartReadSchema.model_validate(cart)


@router.delete(
    "/cart/items/{movie_id}",
    status_code=204,
    summary="Remove movie from cart",
    description="Remove a specific movie from the authenticated user's shopping cart.",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Cart or cart item not found"},
    },
)
async def delete_movie_from_cart(db: DbSession, user: CurrentUser, movie_id: int) -> None:
    await remove_movie_from_cart(db, user_id=user.id, movie_id=movie_id)


@router.delete(
    "/cart",
    status_code=204,
    summary="Clear cart",
    description="Remove all movies from the authenticated user's shopping cart.",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Cart not found"},
    },
)
async def delete_all_movies_from_cart(db: DbSession, user: CurrentUser) -> None:
    await clear_cart(db, user_id=user.id)


@router.get(
    "/cart/{user_id}",
    status_code=200,
    response_model=CartReadSchema,
    summary="Get user's cart",
    description=(
            "Retrieve a specific user's shopping cart with its movies. "
            "Accessible to administrators only."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Administrator privileges required"},
        404: {"model": ErrorResponse, "description": "Cart not found"},
    },
)
async def get_cart_for_admin(db: DbSession, admin: AdminUser, user_id: int) -> CartReadSchema:
    cart = await get_cart_with_items(db, user_id=user_id)
    return CartReadSchema.model_validate(cart)
