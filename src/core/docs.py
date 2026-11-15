import secrets
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.config import settings

docs_security = HTTPBasic()


def verify_docs_access(credentials: HTTPBasicCredentials = Depends(docs_security)) -> None:
    """Allow access only with valid docs credentials.

    Raises:
        HTTPException: 401 with ``WWW-Authenticate`` header, so the browser asks to log in.
    """
    valid_user = secrets.compare_digest(
        credentials.username.encode(), settings.DOCS_USERNAME.encode()
    )
    valid_password = secrets.compare_digest(
        credentials.password.encode(), settings.DOCS_PASSWORD.encode()
    )
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid docs credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def setup_protected_docs(app: FastAPI) -> None:
    """Register ``/docs`` and ``/openapi.json`` behind HTTP Basic auth."""

    @app.get("/docs", include_in_schema=False, dependencies=[Depends(verify_docs_access)])
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Docs")

    @app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(verify_docs_access)])
    async def openapi_schema() -> dict[str, Any]:
        return app.openapi()
