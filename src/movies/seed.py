"""Database seeding script for the movies domain.

Populates initial genres, certifications, and movies for testing and development.
"""

import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import SessionLocal
from src.movies.models import Genre, Certification, Movie, Director, Star


async def seed_database(db: AsyncSession) -> None:
    """Seed initial movie data into the database."""
    print("Seeding database with initial movie data...")

    cert_pg13 = Certification(name="PG-13")
    cert_r = Certification(name="R")
    cert_pg = Certification(name="PG")

    db.add_all([cert_pg13, cert_r, cert_pg])
    await db.flush()

    genre_action = Genre(name="Action")
    genre_scifi = Genre(name="Sci-Fi")
    genre_drama = Genre(name="Drama")
    genre_crime = Genre(name="Crime")

    db.add_all([genre_action, genre_scifi, genre_drama, genre_crime])
    await db.flush()

    director_nolan = Director(name="Christopher Nolan")
    director_ff_coppola = Director(name="Francis Ford Coppola")

    star_mckellen = Star(name="Ian McKellen")
    star_brando = Star(name="Marlon Brando")
    star_dicaprio = Star(name="Leonardo DiCaprio")

    db.add_all([director_nolan, director_ff_coppola, star_mckellen, star_brando, star_dicaprio])
    await db.flush()

    movie1 = Movie(
        name="Inception",
        description=(
            "A thief who steals corporate secrets through the use of dream-sharing technology..."
        ),
        year=2010,
        time=148,
        imdb=8.8,
        votes=2400000,
        price=Decimal("19.99"),
        gross=Decimal("836.8"),
        certification=cert_pg13,
        genres=[genre_action, genre_scifi, genre_drama],
        directors=[director_nolan],
        stars=[star_dicaprio],
    )

    movie2 = Movie(
        name="The Godfather",
        description=(
            "The aging patriarch of an organized crime dynasty transfers control of his empire..."
        ),
        year=1972,
        time=175,
        imdb=9.2,
        votes=1900000,
        price=Decimal("14.99"),
        gross=Decimal("250.4"),
        certification=cert_r,
        genres=[genre_drama, genre_crime],
        directors=[director_ff_coppola],
        stars=[star_brando],
    )

    db.add_all([movie1, movie2])
    await db.commit()
    print("Database seeding completed successfully!")


async def run_seed() -> None:
    async with SessionLocal() as session:
        try:
            await seed_database(session)
        except Exception as e:
            await session.rollback()
            print(f"Error during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())
