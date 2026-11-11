# Як ми пишемо код у цьому проєкті

> **Еталон — домен `movies`, жанри (`Genre`).** Перш ніж писати свій модуль, відкрий ці файли і зроби так само:
> `src/movies/models.py` → `schemas.py` → `service.py` → `router.py` → `tests/movies/test_genres.py`.


---

## 1. Структура: по доменах

Кожен домен — окрема папка, і в ній завжди ті самі файли. Твій код живе **тільки у твоїй папці**, тому ми майже не конфліктуємо в git.

```
src/
├── main.py              # створення app, підключення роутерів (1 рядок на домен)
├── models.py            # реєстр моделей для Alembic (1 рядок на домен)
├── core/                # спільна інфраструктура (P1) — не залежить від доменів
│   ├── config.py        #   settings з .env
│   ├── database.py      #   engine, get_db, DbSession
│   ├── models.py        #   Base, TimestampMixin
│   ├── exceptions.py    #   NotFoundError, ConflictError, ... → HTTP
│   └── pagination.py    #   PaginationParams, Page[T], paginate()
├── accounts/            # юзери, JWT, групи, профіль
├── movies/              # каталог  ← ЕТАЛОН
├── interactions/        # лайки, коментарі, рейтинг, обране
├── cart/                # кошик
├── orders/              # замовлення
├── payments/            # Stripe, платежі
├── notifications/       # email, сповіщення
├── storage/             # MinIO (S3)
└── tasks/               # Celery, celery-beat
tests/
├── conftest.py          # фікстури: client, db_session, login_as
└── <domain>/test_*.py   # тести дзеркалять структуру src/
alembic/                 # міграції
```

### Файли всередині домену

| Файл | Що в ньому | Чого в ньому **НЕ** може бути |
|---|---|---|
| `models.py` | SQLAlchemy-моделі | логіки, запитів |
| `schemas.py` | Pydantic-схеми запитів і відповідей | звернень до БД |
| `service.py` | бізнес-логіка, **усі** запити до БД, `commit()`, кидання помилок | `Request`, `HTTPException`, Pydantic-відповідей |
| `router.py` | ендпоінти: прийняти → перевірити доступ → викликати сервіс → повернути схему | SQL, `commit()`, `if`-логіки бізнесу |
| `enums.py` | Enum-и домену (за потреби) | |
| `dependencies.py` | FastAPI-залежності домену (за потреби) | |
| `filters.py`, `stripe_client.py`, ... | допоміжне, якщо файл сервісу роздувається | |

Великий домен можна розбити: `service.py` → `services/genres.py`, `services/movies.py`. Але шари лишаються ті самі.

### Потік запиту

```
HTTP → router.py → service.py → models.py → БД
         │             │
   схеми (schemas)   помилки (core.exceptions) → автоматично стають {"detail": "..."} з потрібним статусом
```

---

## 2. Правила по шарах

### Моделі (`models.py`)
- Наслідуємось від `src.core.models.Base`; для `created_at/updated_at` — `TimestampMixin`.
- Стиль SQLAlchemy 2.0: `Mapped[...]` + `mapped_column(...)`.
- `__tablename__` — множина, snake_case: `genres`, `cart_items`.
- **Між доменами нічого не імпортуємо.** FK — рядком: `ForeignKey("users.id")`; relationship — назвою класу рядком: `relationship("Movie")`.
- Створив `models.py` → додай рядок у `src/models.py`.

### Схеми (`schemas.py`)
Для кожної сутності `X`:

| Схема | Навіщо |
|---|---|
| `XBase` | спільні поля |
| `XCreate` | тіло `POST` |
| `XUpdate` | тіло `PATCH`, усі поля `Optional` |
| `XRead` | відповідь, `model_config = ConfigDict(from_attributes=True)` |
| `XDetail` | розширена відповідь (за потреби, напр. фільм з жанрами й акторами) |

Валідацію полів робимо через `Field(min_length=..., ge=..., le=...)`, а не руками в сервісі.

### Сервіси (`service.py`)
- Перший аргумент завжди `db: AsyncSession`.
- Повертають ORM-обʼєкти (не схеми).
- Помилки — тільки через `src.core.exceptions`:

| Ситуація | Виняток | HTTP |
|---|---|---|
| Невалідна бізнес-дія (порожній кошик, фільм уже куплено) | `BadRequestError` | 400 |
| Не залогінений | `UnauthorizedError` | 401 |
| Немає прав | `PermissionDeniedError` | 403 |
| Не знайдено | `NotFoundError` | 404 |
| Дублікат / конфлікт стану | `ConflictError` | 409 |
| Невалідне тіло запиту | (Pydantic сам) | 422 |

- `commit()` робить сервіс, один раз у кінці операції.

### Роутери (`router.py`)
- `router = APIRouter(tags=["<domain>"])`, підключається в `main.py` з префіксом `/api/v1`.
- Тип відповіді — через анотацію: `-> GenreRead`, `-> Page[GenreRead]`.
- Залежності: `db: DbSession`, `user: CurrentUser`, `_: ModeratorUser`, `_: AdminUser`.
- Можливі помилки описуємо в `responses=` (див. еталон) — так вони видно в Swagger.

### Імена ендпоінтів і URL

| Дія | Метод і шлях | Функція | Статус |
|---|---|---|---|
| Список | `GET /genres` | `list_genres` | 200 |
| Один | `GET /genres/{genre_id}` | `get_genre` | 200 |
| Створити | `POST /genres` | `create_genre` | 201 |
| Змінити | `PATCH /genres/{genre_id}` | `update_genre` | 200 |
| Видалити | `DELETE /genres/{genre_id}` | `delete_genre` | 204 |
| Дія | `POST /orders/{order_id}/cancel` | `cancel_order` | 200 |

- Ресурси — іменники у множині, `kebab-case`: `/cart/items`, `/password-reset/request`.
- Параметр шляху — `<entity>_id`.
- Ендпоінти «про себе» — через `/me`: `GET /users/me/orders`.
- Списки **завжди** з пагінацією через `PaginationParams` + `Page[T]`.

---

## 3. Як домени користуються один одним

Інший домен можна викликати **тільки через його `service.py`** (або спеціально позначений файл, як `filters.py`). Ніколи не робимо запити до чужих таблиць напряму.

Контракти, які вже лежать у репозиторії як заглушки (сигнатури без узгодження не міняти):

| Функція | Де | Власник | Хто користується |
|---|---|---|---|
| `get_current_user`, `require_roles`, `CurrentUser`, `ModeratorUser`, `AdminUser` | `accounts/dependencies.py` | P2 | усі |
| `send_email`, `notify_user` | `notifications/service.py` | P3 | P2, P5, P7 |
| `apply_movie_filters` | `movies/filters.py` | P4 | P5 |
| `is_movie_in_carts` | `cart/service.py` | P6 | P4 |
| `is_movie_purchased`, `is_movie_purchased_by_anyone`, `mark_order_paid` | `orders/service.py` | P6 | P4, P6, P7 |

Поки контракт не реалізований — просто викликай заглушку, а в тестах підміняй її (`monkeypatch`).

---

## 4. Докстрінги та стиль коду

- Код, імена, докстрінги, коментарі — **англійською**. Документація для команди (як ця) — українською.
- Стиль докстрінгів — **Google style**, коротко.
- **Обовʼязково:**
  - кожен модуль — 1–3 рядки: що в ньому і хто власник;
  - кожна публічна функція сервісу — що робить + секція `Raises:`;
  - кожен ендпоінт — 1 рядок для користувача API (**він стає описом у Swagger**) + хто має доступ.
- Не пишемо докстрінги, що повторюють назву (`"""Get genre."""` для `get_genre` — ок тільки в роутері).
- Типи — скрізь (аргументи й повернення). `Any` — тільки якщо інакше ніяк.
- Довжина рядка — 100. Перед пушем: `poetry run black . && poetry run flake8 .`

Приклад:
```python
async def create_genre(db: AsyncSession, data: GenreCreate) -> Genre:
    """Create a genre.

    Raises:
        ConflictError: a genre with the same name already exists.
    """
```

---

## 5. Тести

- Лежать у `tests/<domain>/test_<що>.py`, дзеркалять `src/`.
- Йдуть на SQLite в памʼяті — Docker не потрібен. Запуск: `poetry run pytest`.
- Фікстури з `tests/conftest.py`:
  - `client` — HTTP-клієнт з чистою БД на кожен тест;
  - `db_session` — та сама сесія, щоб підготувати дані напряму;
  - `login_as(UserGroupEnum.MODERATOR)` — «залогінитись» без справжнього JWT.
- Один тест = одна поведінка. Назва: `test_<дія>_<умова>` (`test_create_genre_forbidden_for_user`).
- Структура тесту: підготовка → **один** запит → перевірки.
- Мінімум на кожен ендпоінт: успішний сценарій + кожна помилка з `responses=` (401/403/404/409).
- Зовнішні сервіси (Stripe, SMTP, MinIO) — тільки моки.

---

## 6. Git і PR

1. Гілка від свіжого `develop`: `feature/<domain>-<що>` (`feature/cart-add-item`), `fix/<що>`.
2. Коміти — коротко англійською в наказовому способі: `Add genre CRUD`, `Fix cart total`.
3. PR — в `develop`, невеликий (одна задача). Заповни шаблон.
4. Мерж — після **2 апрувів** і зеленого CI (`lint` + `tests`).
5. Перед відкриттям свого PR — зроби ревʼю чужого.

### Міграції
1. `git pull origin develop`
2. `poetry run alembic heads` → має бути **одна** голова. Якщо дві — спершу `alembic merge heads`.
3. `poetry run alembic revision --autogenerate -m "add genres"`
4. **Відкрий згенерований файл і перевір** — autogenerate помиляється з Enum і перейменуваннями.

---

## 7. Чекліст ревʼюера

- [ ] Код у правильній папці й правильному шарі (немає SQL у роутері, немає HTTP у сервісі)
- [ ] Немає імпортів чужих моделей; виклики чужих доменів — тільки через їх `service.py`
- [ ] Схеми названі за конвенцією `XCreate / XUpdate / XRead`
- [ ] Помилки — через `core.exceptions`, описані в `responses=`
- [ ] Списки — з пагінацією `Page[T]`
- [ ] Є докстрінги (модуль, сервіс з `Raises:`, ендпоінт)
- [ ] Є тести на успіх і на кожну помилку
- [ ] Нова модель додана в `src/models.py`, міграція перевірена руками
- [ ] CI зелений
