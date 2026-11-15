"""Current user's profile and avatar (spec, section 1: UserProfile)."""

from typing import Any

import pytest
from httpx import AsyncClient

from src.storage import s3

URL = "/api/v1/users/me/profile"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


@pytest.fixture
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Replace the S3 storage: remember uploaded and deleted keys, build fake links."""
    calls: dict[str, list[str]] = {"uploaded": [], "deleted": []}

    async def fake_upload(key: str, data: bytes, content_type: str) -> None:
        calls["uploaded"].append(key)

    async def fake_delete(key: str) -> None:
        calls["deleted"].append(key)

    monkeypatch.setattr(s3, "upload_file", fake_upload)
    monkeypatch.setattr(s3, "delete_file", fake_delete)
    monkeypatch.setattr(s3, "get_file_url", lambda key: f"http://storage/{key}")
    return calls


async def test_get_profile_creates_empty_profile(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == {
        "first_name": None,
        "last_name": None,
        "gender": None,
        "date_of_birth": None,
        "info": None,
        "avatar_url": None,
    }


async def test_get_profile_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(URL)

    assert response.status_code == 401


async def test_update_profile(client: AsyncClient, login_as: Any, create_user: Any) -> None:
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.patch(
        URL,
        json={
            "first_name": "Sofiia",
            "gender": "WOMAN",
            "date_of_birth": "2000-01-31",
            "info": "I love sci-fi.",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["first_name"] == "Sofiia"
    assert body["gender"] == "WOMAN"
    assert body["date_of_birth"] == "2000-01-31"
    assert body["last_name"] is None


async def test_update_profile_changes_only_sent_fields(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    user = await create_user()
    login_as(user_id=user.id)
    await client.patch(URL, json={"first_name": "Sofiia", "last_name": "P"})

    response = await client.patch(URL, json={"last_name": "Pohuliailo"})

    assert response.json()["first_name"] == "Sofiia"
    assert response.json()["last_name"] == "Pohuliailo"


async def test_update_profile_birth_date_in_future(
    client: AsyncClient, login_as: Any, create_user: Any
) -> None:
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.patch(URL, json={"date_of_birth": "2999-01-01"})

    assert response.status_code == 422


async def test_upload_avatar(
    client: AsyncClient, login_as: Any, create_user: Any, fake_storage: dict[str, list[str]]
) -> None:
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.put(
        f"{URL}/avatar", files={"file": ("me.png", PNG, "image/png")}
    )

    assert response.status_code == 200
    [key] = fake_storage["uploaded"]
    assert key.startswith(f"avatars/{user.id}/") and key.endswith(".png")
    assert response.json()["avatar_url"] == f"http://storage/{key}"


async def test_upload_avatar_replaces_old_one(
    client: AsyncClient, login_as: Any, create_user: Any, fake_storage: dict[str, list[str]]
) -> None:
    user = await create_user()
    login_as(user_id=user.id)
    await client.put(f"{URL}/avatar", files={"file": ("a.png", PNG, "image/png")})

    await client.put(f"{URL}/avatar", files={"file": ("b.png", PNG, "image/png")})

    first_key, _second_key = fake_storage["uploaded"]
    assert fake_storage["deleted"] == [first_key]


async def test_upload_avatar_wrong_type(
    client: AsyncClient, login_as: Any, create_user: Any, fake_storage: dict[str, list[str]]
) -> None:
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.put(
        f"{URL}/avatar", files={"file": ("cv.pdf", b"%PDF-1.4", "application/pdf")}
    )

    assert response.status_code == 400
    assert fake_storage["uploaded"] == []


async def test_upload_avatar_too_big(
    client: AsyncClient, login_as: Any, create_user: Any, fake_storage: dict[str, list[str]]
) -> None:
    user = await create_user()
    login_as(user_id=user.id)
    too_big = b"0" * (2 * 1024 * 1024 + 1)

    response = await client.put(
        f"{URL}/avatar", files={"file": ("big.png", too_big, "image/png")}
    )

    assert response.status_code == 400
    assert fake_storage["uploaded"] == []


async def test_delete_avatar(
    client: AsyncClient, login_as: Any, create_user: Any, fake_storage: dict[str, list[str]]
) -> None:
    user = await create_user()
    login_as(user_id=user.id)
    await client.put(f"{URL}/avatar", files={"file": ("a.png", PNG, "image/png")})

    response = await client.delete(f"{URL}/avatar")

    assert response.status_code == 204
    assert fake_storage["deleted"] == fake_storage["uploaded"]
    assert (await client.get(URL)).json()["avatar_url"] is None


async def test_upload_avatar_storage_unavailable(
    client: AsyncClient, login_as: Any, create_user: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken_upload(key: str, data: bytes, content_type: str) -> None:
        raise s3.StorageUnavailableError("File storage is unavailable, try again later")

    monkeypatch.setattr(s3, "upload_file", broken_upload)
    user = await create_user()
    login_as(user_id=user.id)

    response = await client.put(f"{URL}/avatar", files={"file": ("a.png", PNG, "image/png")})

    assert response.status_code == 503
