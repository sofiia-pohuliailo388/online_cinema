from unittest.mock import AsyncMock, patch

import pytest

from src.interactions.service import get_movie_interaction_stats


@pytest.mark.asyncio
async def test_get_movie_interaction_stats():
    db = AsyncMock()

    with (
        patch(
            "src.interactions.service.get_average_rating",
            new_callable=AsyncMock,
            return_value=8.5,
        ) as mock_average,
        patch(
            "src.interactions.service.get_movie_likes_count",
            new_callable=AsyncMock,
            return_value=12,
        ) as mock_likes,
    ):
        stats = await get_movie_interaction_stats(db=db, movie_id=10)

    assert stats == {
        "movie_id": 10,
        "average_rating": 8.5,
        "likes_count": 12,
    }

    mock_average.assert_awaited_once_with(db, 10)
    mock_likes.assert_awaited_once_with(db, 10)
