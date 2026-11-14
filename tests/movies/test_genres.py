"""Reference API tests: copy this structure for your own endpoints.

Pattern: arrange (login / create data) -> act (one request) -> assert (status + body).
One test = one behaviour; the test name says what is expected.
"""

from collections.abc import Callable
from typing import Any

from httpx import AsyncClient

from src.accounts.enums import UserGroupEnum

URL = "/api/v1/genres"


async def test_list_genres_empty(client: AsyncClient) -> None:
    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "per_page": 20, "pages": 0}


async def test_list_genres_paginated(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)
    for name in ["Drama", "Action", "Comedy"]:
        await client.post(URL, json={"name": name})

    response = await client.get(URL, params={"page": 1, "per_page": 2})

    body = response.json()
    assert response.status_code == 200
    assert [g["name"] for g in body["items"]] == ["Action", "Comedy"]
    assert body["total"] == 3
    assert body["pages"] == 2


async def test_create_genre_as_moderator(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)

    response = await client.post(URL, json={"name": "Action"})

    assert response.status_code == 201
    assert response.json()["name"] == "Action"


async def test_create_genre_as_admin(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.ADMIN)

    response = await client.post(URL, json={"name": "Action"})

    assert response.status_code == 201


async def test_create_genre_unauthenticated(client: AsyncClient) -> None:
    response = await client.post(URL, json={"name": "Action"})

    assert response.status_code == 401


async def test_create_genre_forbidden_for_user(
    client: AsyncClient, login_as: Callable[..., Any]
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.post(URL, json={"name": "Action"})

    assert response.status_code == 403


async def test_create_duplicate_genre(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)
    await client.post(URL, json={"name": "Action"})

    response = await client.post(URL, json={"name": "Action"})

    assert response.status_code == 409


async def test_create_genre_empty_name(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)

    response = await client.post(URL, json={"name": ""})

    assert response.status_code == 422


async def test_get_genre_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{URL}/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Genre with id=999 not found"}


async def test_update_genre(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)
    genre_id = (await client.post(URL, json={"name": "Actoin"})).json()["id"]

    response = await client.patch(f"{URL}/{genre_id}", json={"name": "Action"})

    assert response.status_code == 200
    assert response.json() == {"id": genre_id, "name": "Action", "movies_count": 0}


async def test_delete_genre(client: AsyncClient, login_as: Callable[..., Any]) -> None:
    login_as(UserGroupEnum.MODERATOR)
    genre_id = (await client.post(URL, json={"name": "Action"})).json()["id"]

    response = await client.delete(f"{URL}/{genre_id}")

    assert response.status_code == 204
    assert (await client.get(f"{URL}/{genre_id}")).status_code == 404
