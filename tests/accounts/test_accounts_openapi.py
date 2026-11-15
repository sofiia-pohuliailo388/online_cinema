"""Tests of the Swagger (OpenAPI) description of the accounts endpoints (owner: P2)."""

from typing import Any

import pytest

from src.main import app

PREFIX = "/api/v1/accounts"

# (method, path) -> status codes of the errors that must be described in Swagger.
DOCUMENTED_ERRORS = {
    ("post", "/register"): {"409", "422"},
    ("get", "/activate"): {"400", "422"},
    ("post", "/login"): {"401", "403", "422"},
    ("post", "/refresh"): {"401", "403", "422"},
    ("post", "/logout"): {"422"},
    ("post", "/resend-activation"): {"422"},
    ("post", "/change-password"): {"400", "401", "422"},
    ("post", "/forgot-password"): {"422"},
    ("post", "/reset-password"): {"400", "422"},
}
PROTECTED = {("post", "/change-password")}
ACCOUNTS_SCHEMAS = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserRead",
    "RefreshTokenRequest",
    "AccessTokenResponse",
    "TokenPairResponse",
    "ResendActivationRequest",
    "MessageResponse",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
]


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return app.openapi()


def test_every_accounts_endpoint_is_in_the_spec(spec: dict[str, Any]) -> None:
    documented = {
        (method, path.removeprefix(PREFIX))
        for path, operations in spec["paths"].items()
        if path.startswith(PREFIX)
        for method in operations
    }

    assert documented == set(DOCUMENTED_ERRORS)


@pytest.mark.parametrize(("method", "path"), sorted(DOCUMENTED_ERRORS))
def test_endpoint_has_a_description_and_the_accounts_tag(
    spec: dict[str, Any], method: str, path: str
) -> None:
    operation = spec["paths"][PREFIX + path][method]

    assert operation["description"].strip()
    assert operation["tags"] == ["accounts"]


@pytest.mark.parametrize(("method", "path"), sorted(DOCUMENTED_ERRORS))
def test_endpoint_describes_its_errors(spec: dict[str, Any], method: str, path: str) -> None:
    responses = spec["paths"][PREFIX + path][method]["responses"]

    assert DOCUMENTED_ERRORS[(method, path)] <= set(responses)
    for status_code in DOCUMENTED_ERRORS[(method, path)] - {"422"}:
        error = responses[status_code]
        assert error["description"] != "Successful Response"
        assert error["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")


@pytest.mark.parametrize(("method", "path"), sorted(DOCUMENTED_ERRORS))
def test_only_protected_endpoints_ask_for_a_bearer_token(
    spec: dict[str, Any], method: str, path: str
) -> None:
    operation = spec["paths"][PREFIX + path][method]

    if (method, path) in PROTECTED:
        assert operation["security"] == [{"HTTPBearer": []}]
    else:
        assert "security" not in operation


@pytest.mark.parametrize("schema_name", ACCOUNTS_SCHEMAS)
def test_every_field_of_accounts_schemas_has_a_description(
    spec: dict[str, Any], schema_name: str
) -> None:
    schema = spec["components"]["schemas"][schema_name]

    assert schema["description"].strip()
    for field_name, field in schema["properties"].items():
        assert field.get("description"), f"{schema_name}.{field_name} has no description"
