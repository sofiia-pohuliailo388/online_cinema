"""Database engine and the per-request session dependency.

Usage in a router::

    from src.core.database import DbSession

    @router.get("/things")
    async def list_things(db: DbSession) -> ...:
        return await service.list_things(db)

Rule: routers only pass ``db`` to services. Queries and ``commit()`` live in services.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield one session per request; it is closed automatically afterwards."""
    async with SessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
