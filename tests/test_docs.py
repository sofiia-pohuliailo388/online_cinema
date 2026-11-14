"""Swagger and OpenAPI schema are available only with docs credentials (spec, section 9)."""

from httpx import AsyncClient

from src.core.config import settings

VALID_AUTH = (settings.DOCS_USERNAME, settings.DOCS_PASSWORD)


async def test_docs_without_credentials(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


async def test_docs_with_wrong_credentials(client: AsyncClient) -> None:
    response = await client.get("/docs", auth=("admin", "wrong-password"))

    assert response.status_code == 401


async def test_docs_with_valid_credentials(client: AsyncClient) -> None:
    response = await client.get("/docs", auth=VALID_AUTH)

    assert response.status_code == 200
    assert "swagger-ui" in response.text


async def test_openapi_without_credentials(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 401


async def test_openapi_with_valid_credentials(client: AsyncClient) -> None:
    response = await client.get("/openapi.json", auth=VALID_AUTH)

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Online Cinema API"


async def test_redoc_is_disabled(client: AsyncClient) -> None:
    response = await client.get("/redoc")

    assert response.status_code == 404


async def test_health_stays_public(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
