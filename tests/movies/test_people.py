"""Moderator CRUD for stars, directors and certifications (spec, section 2)."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.enums import UserGroupEnum
from src.movies.models import Certification, Movie

API = "/api/v1"

RESOURCES = [
    pytest.param("stars", "Keanu Reeves", id="stars"),
    pytest.param("directors", "Christopher Nolan", id="directors"),
    pytest.param("certifications", "PG-13", id="certifications"),
]


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_create_as_moderator(client: AsyncClient, login_as, resource: str, name: str) -> None:
    login_as(UserGroupEnum.MODERATOR)

    response = await client.post(f"{API}/{resource}", json={"name": name})

    assert response.status_code == 201
    assert response.json()["name"] == name


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_create_forbidden_for_user(
    client: AsyncClient, login_as, resource: str, name: str
) -> None:
    login_as(UserGroupEnum.USER)

    response = await client.post(f"{API}/{resource}", json={"name": name})

    assert response.status_code == 403


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_create_unauthenticated(client: AsyncClient, resource: str, name: str) -> None:
    response = await client.post(f"{API}/{resource}", json={"name": name})

    assert response.status_code == 401


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_create_duplicate(client: AsyncClient, login_as, resource: str, name: str) -> None:
    login_as(UserGroupEnum.MODERATOR)
    await client.post(f"{API}/{resource}", json={"name": name})

    response = await client.post(f"{API}/{resource}", json={"name": name})

    assert response.status_code == 409


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_list_and_get(client: AsyncClient, login_as, resource: str, name: str) -> None:
    login_as(UserGroupEnum.MODERATOR)
    item_id = (await client.post(f"{API}/{resource}", json={"name": name})).json()["id"]

    list_response = await client.get(f"{API}/{resource}")
    get_response = await client.get(f"{API}/{resource}/{item_id}")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert get_response.status_code == 200
    assert get_response.json() == {"id": item_id, "name": name}


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_get_not_found(client: AsyncClient, resource: str, name: str) -> None:
    response = await client.get(f"{API}/{resource}/999999")

    assert response.status_code == 404


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_update(client: AsyncClient, login_as, resource: str, name: str) -> None:
    login_as(UserGroupEnum.MODERATOR)
    item_id = (await client.post(f"{API}/{resource}", json={"name": name})).json()["id"]

    response = await client.patch(f"{API}/{resource}/{item_id}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


@pytest.mark.parametrize(("resource", "name"), RESOURCES)
async def test_delete(client: AsyncClient, login_as, resource: str, name: str) -> None:
    login_as(UserGroupEnum.MODERATOR)
    item_id = (await client.post(f"{API}/{resource}", json={"name": name})).json()["id"]

    response = await client.delete(f"{API}/{resource}/{item_id}")

    assert response.status_code == 204
    assert (await client.get(f"{API}/{resource}/{item_id}")).status_code == 404


async def test_delete_certification_used_by_movie(
    client: AsyncClient, login_as, db_session: AsyncSession
) -> None:
    certification = Certification(name="R")
    db_session.add(certification)
    await db_session.flush()
    db_session.add(
        Movie(
            name="Movie",
            year=2020,
            time=100,
            imdb=7.0,
            votes=10,
            description="Description",
            price=Decimal("5.00"),
            certification_id=certification.id,
        )
    )
    await db_session.commit()
    login_as(UserGroupEnum.MODERATOR)

    response = await client.delete(f"{API}/certifications/{certification.id}")

    assert response.status_code == 409
