
import pytest

from src.cart.service import add_movie_in_cart


@pytest.mark.asyncio
async def test_add_movie_endpoint(client, login_as, movie, test_user):
    login_as(user_id=test_user.id)

    response = await client.post(
        "/api/v1/cart/items",
        json={"movie_id": movie.id},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_cart_endpoint(client, login_as, db_session, movie, test_user):
    login_as(user_id=test_user.id)
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    response = await client.get("/api/v1/cart/")

    assert response.status_code == 200
    assert len(response.json()["cart_items"]) == 1
    assert response.json()["cart_items"][0]["movie_id"] == movie.id


@pytest.mark.asyncio
async def test_delete_movie_endpoint(
    client, login_as, db_session, movie, test_user
):
    login_as(user_id=test_user.id)
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    response = await client.delete(
        f"/api/v1/cart/items/{movie.id}/"
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_clear_cart_endpoint(
    client, login_as, db_session, movie, test_user
):
    login_as(user_id=test_user.id)
    await add_movie_in_cart(db_session, movie.id, test_user.id)

    response = await client.delete("/api/v1/cart/")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_add_nonexistent_movie_endpoint(client, login_as, test_user):
    login_as(user_id=test_user.id)

    response = await client.post(
        "/api/v1/cart/items",
        json={"movie_id": 999999},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_duplicate_movie_endpoint(
    client, login_as, movie, test_user
):
    login_as(user_id=test_user.id)

    await client.post(
        "/api/v1/cart/items",
        json={"movie_id": movie.id},
    )

    response = await client.post(
        "/api/v1/cart/items",
        json={"movie_id": movie.id},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_movie_invalid_body(client, login_as, test_user):
    login_as(user_id=test_user.id)

    response = await client.post(
        "/api/v1/cart/items",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_cart_endpoint(client, login_as, test_user):
    login_as(user_id=test_user.id)

    response = await client.get("/api/v1/cart/")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_movie_endpoint(
    client, login_as, movie, test_user
):
    login_as(user_id=test_user.id)

    response = await client.delete(
        f"/api/v1/cart/items/{movie.id}/"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_clear_nonexistent_cart_endpoint(client, login_as, test_user):
    login_as(user_id=test_user.id)

    response = await client.delete("/api/v1/cart/")

    assert response.status_code == 404
