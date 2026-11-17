"""Helpers for payments tests: data builders and Stripe payloads."""
from decimal import Decimal

from sqlalchemy import select

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.movies.models import Certification, Movie
from src.orders.models import Order, OrderItem, StatusEnum
from src.payments.models import Payment

async def create_user(db_session, email: str) -> User:
    group = await db_session.scalar(
        select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    )
    if group is None:
        group = UserGroup(name=UserGroupEnum.USER)
        db_session.add(group)
        await db_session.flush()
    user = User(email=email, hashed_password="hash", is_active=True, group_id=group.id)
    db_session.add(user)
    await db_session.flush()
    return user


async def create_movie(db_session, name: str, price: str = "9.99") -> Movie:
    certification = await db_session.scalar(
        select(Certification).where(Certification.name == "PG-13")
    )
    if certification is None:
        certification = Certification(name="PG-13")
        db_session.add(certification)
        await db_session.flush()
    movie = Movie(
        name=name,
        year=2024,
        time=120,
        imdb=8.0,
        votes=100,
        description="Description",
        price=Decimal(price),
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.flush()
    return movie


async def create_order(
    db_session, user: User, movies: list[Movie], status: StatusEnum = StatusEnum.PENDING
) -> Order:
    order = Order(
        user_id=user.id,
        status=status,
        total_amount=sum((m.price for m in movies), Decimal("0.00")),
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add_all(
        [OrderItem(order_id=order.id, movie_id=m.id, price_at_order=m.price) for m in movies]
    )
    await db_session.commit()
    return order


def make_stripe_session(
    order: Order,
    intent: str = "pi_1",
    amount_cents: int | None = None,
    payment_status: str = "paid",
) -> dict:
    return {
        "payment_status": payment_status,
        "payment_intent": intent,
        "amount_total": amount_cents if amount_cents is not None else int(order.total_amount * 100),
        "metadata": {"order_id": str(order.id)},
    }


async def get_payment(db_session, intent: str) -> Payment | None:
    return await db_session.scalar(select(Payment).where(Payment.external_payment_id == intent))


async def count_payments(db_session) -> int:
    return len((await db_session.scalars(select(Payment))).all())
