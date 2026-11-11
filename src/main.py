"""FastAPI application factory: the only place where routers are wired together.

To add your domain: import its ``router`` and add one ``include_router`` line.
"""
from fastapi import FastAPI

from src.core.exceptions import register_exception_handlers
from src.movies.router import router as movies_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title="Online Cinema API", version="0.1.0")
    register_exception_handlers(app)

    app.include_router(movies_router, prefix=API_PREFIX)
    # app.include_router(accounts_router, prefix=API_PREFIX)      # P2, P3
    # app.include_router(interactions_router, prefix=API_PREFIX)  # P5
    # app.include_router(cart_router, prefix=API_PREFIX)          # P6
    # app.include_router(orders_router, prefix=API_PREFIX)        # P6
    # app.include_router(payments_router, prefix=API_PREFIX)      # P7

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness check for Docker / deploy."""
        return {"status": "ok"}

    return app


app = create_app()
