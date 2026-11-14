
"""FastAPI application factory."""

from fastapi import FastAPI

import src.models  # noqa: F401
from src.accounts.router import router as accounts_router
from src.cart.router import router as cart_router
from src.core.docs import setup_protected_docs
from src.core.exceptions import register_exception_handlers
from src.interactions.router import router as interactions_router
from src.movies.router import router as movies_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Online Cinema API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    register_exception_handlers(app)
    setup_protected_docs(app)

    app.include_router(movies_router, prefix=API_PREFIX)
    app.include_router(accounts_router, prefix=API_PREFIX)
    app.include_router(interactions_router, prefix=API_PREFIX)
    app.include_router(cart_router, prefix=API_PREFIX)  # P6
    # app.include_router(orders_router, prefix=API_PREFIX)  # P6
    # app.include_router(payments_router, prefix=API_PREFIX)  # P7

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness check for Docker / deploy."""
        return {"status": "ok"}

    return app


app = create_app()
