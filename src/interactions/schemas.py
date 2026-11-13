"""Pydantic schemas of the movie interactions domain."""

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class MovieReactionCreate(BaseModel):
    """Schema for creating or changing a movie reaction."""

    movie_id: int
    is_like: bool


class MovieReactionRead(BaseModel):
    """Schema for reading a movie reaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    is_like: bool


class RatingCreate(BaseModel):
    """Schema for creating or changing a movie rating."""

    movie_id: int
    score: int = Field(ge=1, le=10, examples=[8])


class RatingRead(BaseModel):
    """Schema for reading a movie rating."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    score: int


class CommentCreate(BaseModel):
    """Schema for creating a comment or reply."""

    movie_id: int
    text: str = Field(min_length=1, max_length=5000)
    parent_id: int | None = None


class CommentRead(BaseModel):
    """Schema for reading a comment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    parent_id: int | None
    text: str
    created_at: datetime


class CommentLikeRead(BaseModel):
    """Schema for reading a comment like."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    comment_id: int


class FavoriteRead(BaseModel):
    """Schema for reading a user's favorite movie."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int


class MovieInteractionStats(BaseModel):
    """Statistics of user interactions with a movie."""

    movie_id: int
    average_rating: float | None
    likes_count: int
