from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import (
    BadRequestError,
    NotFoundError,
)
from src.interactions.models import Comment, CommentLike
from src.interactions.services.comments import (
    create_comment,
    like_comment,
    list_comments,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    db.execute.return_value = result
    return db, result


async def test_create_comment(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    comment = await create_comment(
        db=db,
        user_id=1,
        movie_id=10,
        text="Great movie!",
    )

    assert isinstance(comment, Comment)
    assert comment.user_id == 1
    assert comment.movie_id == 10
    assert comment.text == "Great movie!"
    assert comment.parent_id is None
    db.add.assert_called_once_with(comment)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(comment)


@patch("src.interactions.services.comments.notify_user", new_callable=AsyncMock)
async def test_create_comment_reply(mock_notify, mock_db):
    db, result = mock_db
    parent = SimpleNamespace(
        id=5,
        user_id=2,
        movie_id=10,
    )
    result.scalar_one_or_none.return_value = parent

    comment = await create_comment(
        db=db,
        user_id=1,
        movie_id=10,
        text="I agree!",
        parent_id=5,
    )

    assert comment.parent_id == 5
    assert comment.text == "I agree!"
    mock_notify.assert_awaited_once_with(
        db,
        2,
        "You received a reply to your comment.",
    )


async def test_create_comment_parent_not_found(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    with pytest.raises(NotFoundError):
        await create_comment(
            db=db,
            user_id=1,
            movie_id=10,
            text="Reply",
            parent_id=999,
        )

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


async def test_create_comment_parent_from_another_movie(mock_db):
    db, result = mock_db
    parent = SimpleNamespace(
        id=5,
        user_id=2,
        movie_id=20,
    )
    result.scalar_one_or_none.return_value = parent

    with pytest.raises(BadRequestError):
        await create_comment(
            db=db,
            user_id=1,
            movie_id=10,
            text="Reply",
            parent_id=5,
        )

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@patch("src.interactions.services.comments.notify_user", new_callable=AsyncMock)
async def test_like_comment(mock_notify, mock_db):
    db, result = mock_db
    comment = SimpleNamespace(
        id=5,
        user_id=2,
        movie_id=10,
    )
    result.scalar_one_or_none.side_effect = [comment, None]

    comment_like = await like_comment(
        db=db,
        user_id=1,
        comment_id=5,
    )

    assert isinstance(comment_like, CommentLike)
    assert comment_like.user_id == 1
    assert comment_like.comment_id == 5

    db.add.assert_called_once_with(comment_like)
    db.commit.assert_awaited_once()
    mock_notify.assert_awaited_once_with(
        db,
        2,
        "Your comment received a like.",
    )


@patch("src.interactions.services.comments.notify_user", new_callable=AsyncMock)
async def test_like_own_comment(mock_notify, mock_db):
    db, result = mock_db
    comment = SimpleNamespace(
        id=5,
        user_id=1,
        movie_id=10,
    )
    result.scalar_one_or_none.side_effect = [comment, None]

    await like_comment(
        db=db,
        user_id=1,
        comment_id=5,
    )

    mock_notify.assert_not_awaited()


async def test_like_comment_twice_removes_like(mock_db):
    db, result = mock_db
    comment = SimpleNamespace(
        id=5,
        user_id=2,
        movie_id=10,
    )
    existing_like = SimpleNamespace(
        user_id=1,
        comment_id=5,
    )
    result.scalar_one_or_none.side_effect = [comment, existing_like]

    response = await like_comment(
        db=db,
        user_id=1,
        comment_id=5,
    )

    assert response is None
    db.delete.assert_awaited_once_with(existing_like)
    db.commit.assert_awaited_once()
    db.add.assert_not_called()


async def test_like_nonexistent_comment(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    with pytest.raises(NotFoundError):
        await like_comment(
            db=db,
            user_id=1,
            comment_id=999,
        )

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


async def test_list_comments(mock_db):
    db, result = mock_db

    comments = [
        SimpleNamespace(id=2, movie_id=10),
        SimpleNamespace(id=1, movie_id=10),
    ]

    result.scalars.return_value.all.return_value = comments

    actual_comments = await list_comments(
        db=db,
        movie_id=10,
    )

    assert actual_comments == comments
    db.execute.assert_awaited_once()
    result.scalars.return_value.all.assert_called_once()


async def test_list_comments_empty(mock_db):
    db, result = mock_db
    result.scalars.return_value.all.return_value = []

    actual_comments = await list_comments(
        db=db,
        movie_id=10,
    )

    assert actual_comments == []
    db.execute.assert_awaited_once()
