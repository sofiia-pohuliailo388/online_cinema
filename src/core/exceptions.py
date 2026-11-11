"""Domain exceptions and their mapping to HTTP responses.

Services raise these exceptions; routers never build ``HTTPException`` themselves.
Every error response has the same shape: ``{"detail": "<message>"}``.

Usage in a service::

    from src.core.exceptions import NotFoundError

    if genre is None:
        raise NotFoundError(f"Genre {genre_id} not found")
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error body, used in ``responses=`` of routers for Swagger docs."""

    detail: str


class AppError(Exception):
    """Base class for all expected (business) errors."""

    status_code: int = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class PermissionDeniedError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
