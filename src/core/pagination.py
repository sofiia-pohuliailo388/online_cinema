"""One pagination format for every list endpoint.

Request:  ``?page=1&per_page=20``
Response: ``{"items": [...], "total": 42, "page": 1, "per_page": 20, "pages": 3}``

Usage::

    # service
    items, total = await paginate(db, select(Genre).order_by(Genre.name), pagination)

    # router
    return Page[GenreRead].create([GenreRead.model_validate(i) for i in items], total, pagination)
"""
import math
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams:
    """Query parameters; use as ``Annotated[PaginationParams, Depends()]``."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number, starting from 1"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.per_page = per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PaginationParams) -> "Page[T]":
        pages = math.ceil(total / params.per_page) if total else 0
        return cls(
            items=items, total=total, page=params.page, per_page=params.per_page, pages=pages
        )


async def paginate(
    db: AsyncSession, stmt: Select[Any], params: PaginationParams
) -> tuple[list[Any], int]:
    """Return one page of ``stmt`` results and the total row count."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.scalars(stmt.offset(params.offset).limit(params.per_page))
    return list(result.all()), total
