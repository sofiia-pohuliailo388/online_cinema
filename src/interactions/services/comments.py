"""Business logic for comments, replies, and comment likes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BadRequestError,
    NotFoundError,
)
from src.interactions.models import Comment, CommentLike
from src.notifications.service import notify_user


async def create_comment(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
    text: str,
    parent_id: int | None = None,
) -> Comment:
    """Create a comment or a reply to an existing comment."""

    parent = None

    if parent_id is not None:
        stmt = select(Comment).where(Comment.id == parent_id)
        result = await db.execute(stmt)
        parent = result.scalar_one_or_none()

        if parent is None:
            raise NotFoundError("Parent comment not found")

        if parent.movie_id != movie_id:
            raise BadRequestError("Parent comment belongs to another movie")

    comment = Comment(
        user_id=user_id,
        movie_id=movie_id,
        text=text,
        parent_id=parent_id,
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    if parent is not None and parent.user_id != user_id:
        await notify_user(
            db,
            parent.user_id,
            "You received a reply to your comment.",
        )

    return comment


async def like_comment(
    db: AsyncSession,
    user_id: int,
    comment_id: int,
) -> CommentLike | None:
    """Toggle a like on a comment and notify its author."""

    stmt = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if comment is None:
        raise NotFoundError("Comment not found")

    like_stmt = select(CommentLike).where(
        CommentLike.user_id == user_id,
        CommentLike.comment_id == comment_id,
    )
    result = await db.execute(like_stmt)
    existing_like = result.scalar_one_or_none()

    if existing_like is not None:
        await db.delete(existing_like)
        await db.commit()
        return None

    comment_like = CommentLike(
        user_id=user_id,
        comment_id=comment_id,
    )

    db.add(comment_like)
    await db.commit()
    await db.refresh(comment_like)

    if comment.user_id != user_id:
        await notify_user(
            db,
            comment.user_id,
            "Your comment received a like.",
        )

    return comment_like


async def list_comments(
    db: AsyncSession,
    movie_id: int,
) -> list[Comment]:
    """Get all comments for a movie, newest first."""

    stmt = select(Comment).where(Comment.movie_id == movie_id).order_by(Comment.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())
