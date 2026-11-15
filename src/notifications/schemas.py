"""Pydantic schemas of in-app notifications (owner: P3)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    is_read: bool
    created_at: datetime


class UnreadCountRead(BaseModel):
    unread: int = Field(description="Number of unread notifications.", examples=[3])


class MarkedReadRead(BaseModel):
    updated: int = Field(description="How many notifications were marked as read.", examples=[3])
