import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.models import Notification
from src.notifications.service import notify_user


@pytest.mark.asyncio
async def test_notify_user_success(db_session: AsyncSession):
    user_id = 1
    test_message = "New like on your comment!"

    await notify_user(db_session, user_id=user_id, text=test_message)

    result = await db_session.execute(
        select(Notification).where(Notification.user_id == user_id)
    )
    notification = result.scalars().first()

    assert notification is not None
    assert notification.text == test_message
    assert notification.is_read is False
    assert notification.user_id == user_id
    assert notification.created_at is not None


@pytest.mark.asyncio
async def test_notification_default_fields(db_session: AsyncSession):
    notification = Notification(
        user_id=1,
        text="Default status test"
    )
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    assert notification.is_read is False
    assert notification.text == "Default status test"