# Online Cinema API

FastAPI-бекенд онлайн-кінотеатру: акаунти й JWT, каталог фільмів, кошик, замовлення, оплата через Stripe.

> **Перед тим як писати код — прочитай [CONTRIBUTING.md](CONTRIBUTING.md).**
> Еталонний приклад, як писати модуль: `src/movies/` (жанри) + `tests/movies/test_genres.py`.

## Запуск у Docker
```bash
cp .env.example .env
docker compose up --build
```
- API і Swagger: http://localhost:8000/docs
- MailHog (листи): http://localhost:8025
- MinIO консоль: http://localhost:9001

## Локально
```bash
poetry install
poetry run pytest          # тести (без Docker, на SQLite)
poetry run flake8 .        # лінтер
poetry run black .         # форматування
docker compose up -d db    # тільки Postgres, для запуску самого API
poetry run alembic upgrade head
poetry run uvicorn src.main:app --reload
```

## Хто за що відповідає
| Домен | Папка | 
|---|---|
| Інфраструктура, CI/CD, тестові фікстури | `src/core`, `.github`, `tests/conftest.py` | 
| Авторизація, JWT | `src/accounts` |
| Профіль, адмінка юзерів, email, Celery, MinIO | `src/accounts`, `src/notifications`, `src/tasks`, `src/storage` |
| Каталог фільмів | `src/movies` |
| Лайки, коментарі, рейтинг, обране | `src/interactions` |
| Кошик і замовлення | `src/cart`, `src/orders` |
| Оплата | `src/payments` |
