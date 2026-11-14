"""Pydantic schemas of the movie interactions domain."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovieReactionCreate(BaseModel):
    """Schema for creating or changing a movie reaction."""

    movie_id: int = Field(description="ID of the movie to react to", examples=[1])
    is_like: bool = Field(
        description="True for like, false for dislike",
        examples=[True],
    )


class MovieReactionRead(BaseModel):
    """Schema for reading a movie reaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique reaction ID")
    user_id: int = Field(description="ID of the user who reacted")
    movie_id: int = Field(description="ID of the movie")
    is_like: bool = Field(description="True for like, false for dislike")


class RatingCreate(BaseModel):
    """Schema for creating or changing a movie rating."""

    movie_id: int = Field(description="ID of the movie to rate", examples=[1])
    score: int = Field(
        ge=1,
        le=10,
        description="Movie rating on a scale from 1 to 10",
        examples=[8],
    )


class RatingRead(BaseModel):
    """Schema for reading a movie rating."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique rating ID")
    user_id: int = Field(description="ID of the user who rated the movie")
    movie_id: int = Field(description="ID of the rated movie")
    score: int = Field(description="Rating from 1 to 10")


class CommentCreate(BaseModel):
    """Schema for creating a comment or reply."""

    movie_id: int = Field(description="ID of the movie being discussed")
    text: str = Field(
        min_length=1,
        max_length=5000,
        description="Comment text (1–5000 characters)",
        examples=["Great movie!"],
    )
    parent_id: int | None = Field(
        default=None,
        description="Parent comment ID. Leave empty to create a top-level comment",
        examples=[None, 10],
    )


class CommentRead(BaseModel):
    """Schema for reading a comment."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique comment ID")
    user_id: int = Field(description="ID of the comment author")
    movie_id: int = Field(description="ID of the related movie")
    parent_id: int | None = Field(description="Parent comment ID, or null for a top-level comment")
    text: str = Field(description="Comment text")
    created_at: datetime = Field(description="Comment creation timestamp")


class CommentLikeRead(BaseModel):
    """Schema for reading a comment like."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique comment like ID")
    user_id: int = Field(description="ID of the user who liked the comment")
    comment_id: int = Field(description="ID of the liked comment")


class FavoriteRead(BaseModel):
    """Schema for reading a user's favorite movie."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique favorite record ID")
    user_id: int = Field(description="ID of the user")
    movie_id: int = Field(description="ID of the favorite movie")


class MovieInteractionStats(BaseModel):
    """Statistics of user interactions with a movie."""

    movie_id: int = Field(description="ID of the movie")
    average_rating: float | None = Field(description="Average user rating on a scale from 1 to 10")
    likes_count: int = Field(
        description="Total number of likes received by the movie",
        ge=0,
    )
