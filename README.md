# 🎬 Online Cinema API

Бекенд онлайн-кінотеатру на **FastAPI**: реєстрація з активацією через email, JWT-авторизація,
каталог фільмів з пошуком і фільтрами, лайки, коментарі, рейтинги, обране, кошик, замовлення
та оплата через **Stripe**.

> 👩‍💻 Пишеш код у цьому репозиторії? Спершу прочитай **[CONTRIBUTING.md](CONTRIBUTING.md)**.

---

## Зміст

- [Стек](#стек)
- [Швидкий старт (Docker)](#швидкий-старт-docker)
- [Сервіси та адреси](#сервіси-та-адреси)
- [Як користуватись API](#як-користуватись-api)
- [Локальна розробка без Docker](#локальна-розробка-без-docker)
- [Тести та перевірки якості](#тести-та-перевірки-якості)
- [Змінні оточення](#змінні-оточення)
- [Структура проєкту](#структура-проєкту)
- [Ендпоінти](#ендпоінти)
- [CI/CD](#cicd)
- [Команда](#команда)

---

## Стек

| Що | Чим |
|---|---|
| API | FastAPI, Pydantic v2 |
| База даних | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| Фонові задачі | Celery + celery-beat, Redis |
| Пошта | SMTP (MailHog у розробці), шаблони Jinja2 |
| Файли (аватари) | S3-сумісне сховище — [Silo](https://silo.pigsty.io) (форк MinIO), boto3 |
| Оплата | Stripe Checkout + webhooks |
| Залежності | Poetry |
| Якість коду | pytest + pytest-cov, flake8, mypy |
| Інфраструктура | Docker, Docker Compose, GitHub Actions |

---

## Швидкий старт (Docker)

Потрібен лише [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/sofiia-pohuliailo388/online_cinema.git
cd online_cinema
cp .env.example .env
docker compose up --build
```

Коли в логах з'явиться `Uvicorn running on http://0.0.0.0:8000` — все готово.
Міграції бази даних застосовуються автоматично під час старту.

**Заповнити каталог тестовими фільмами** (в окремому терміналі):

```bash
docker compose exec app python -m src.movies.seed
```

Зупинити: `Ctrl + C`, або `docker compose down`.
Видалити разом з даними бази: `docker compose down -v`.

---

## Сервіси та адреси

| Сервіс | Адреса | Логін |
|---|---|---|
| **Swagger (документація API)** | http://localhost:8000/docs | `admin` / `admin` |
| API | http://localhost:8000/api/v1 | — |
| Health-check | http://localhost:8000/health | — |
| **MailHog** (вхідні листи) | http://localhost:8025 | — |
| **Консоль сховища** (аватари) | http://localhost:9001 | `minioadmin` / `minioadmin` |
| PostgreSQL | `localhost:5432` | `postgres` / `postgres`, база `cinema` |
| Redis | `localhost:6379` | — |

> Swagger закритий логіном (вимога ТЗ). Логін і пароль задаються в `.env`:
> `DOCS_USERNAME`, `DOCS_PASSWORD`.

---

## Як користуватись API

### 1. Зареєструватись і активувати акаунт

1. Swagger → `POST /api/v1/accounts/register` → email і пароль
   (мінімум 8 символів: велика й мала літера, цифра, спецсимвол — наприклад `Str0ng!Pass`).
2. Відкрити http://localhost:8025 → лист **Activation link** → кнопка **Activate Account**.

> Посилання одноразове: повторне відкриття покаже `Invalid activation token` — це нормально.

### 2. Залогінитись у Swagger

1. `POST /api/v1/accounts/login` → скопіювати `access_token` з відповіді.
2. Кнопка **Authorize** 🔒 угорі Swagger → вставити токен → **Authorize**.

Access-токен живе 15 хвилин. Новий — через `POST /api/v1/accounts/refresh` з `refresh_token`.

### 3. Стати модератором або адміном

Нові користувачі мають групу `USER`. Першого адміна призначте прямо в базі:

```bash
docker compose exec db psql -U postgres -d cinema -c \
  "update users set group_id = (select id from user_groups where name = 'ADMIN') \
   where email = 'you@example.com';"
```

Після цього залогіньтесь заново. Далі адмін може змінювати групи інших через
`PATCH /api/v1/admin/users/{user_id}/group`.

| Група | Може |
|---|---|
| `USER` | каталог, лайки, коментарі, обране, кошик, замовлення, оплата, профіль |
| `MODERATOR` | + керування фільмами, жанрами, акторами, режисерами, сертифікатами |
| `ADMIN` | + усе модераторське, керування користувачами (групи, ручна активація), кошики й замовлення всіх користувачів, усі платежі, повернення коштів |

### 4. Купити фільм

1. `POST /api/v1/cart/items` — додати фільм у кошик.
2. `POST /api/v1/orders` — створити замовлення з кошика.
3. `POST /api/v1/payments/checkout/{order_id}` — отримати посилання на оплату Stripe.
4. Оплатити тестовою карткою `4242 4242 4242 4242` (будь-яка майбутня дата, будь-який CVC).
5. Stripe надсилає вебхук → замовлення стає `paid`, у MailHog приходить лист-підтвердження.

> Для оплати потрібні тестові ключі Stripe в `.env` (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`).
> Щоб вебхуки доходили до локального сервера, використовуйте
> [Stripe CLI](https://docs.stripe.com/stripe-cli):
> `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`

---

## Локальна розробка без Docker

Потрібні Python 3.12+ і [Poetry](https://python-poetry.org/docs/#installation).

```bash
poetry install
```

Для запуску самого API потрібні PostgreSQL і Redis — найпростіше підняти їх через Docker:

```bash
docker compose up -d db redis mailhog
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cinema poetry run alembic upgrade head
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cinema poetry run uvicorn src.main:app --reload
```

> У `.env` адреси сервісів вказані для Docker (`db`, `redis`, `mailhog`).
> Поза Docker використовуйте `localhost`, як у командах вище.

---

## Тести та перевірки якості

Тести йдуть на SQLite в пам'яті — **Docker для них не потрібен**. Celery виконує задачі одразу,
справжні листи не відправляються, Stripe і сховище файлів замінюються заглушками.

```bash
poetry run pytest                                   # усі тести
poetry run pytest tests/movies -v                   # тести одного домену
poetry run pytest --cov=src --cov-report=term       # з покриттям
poetry run flake8 .                                 # лінтер
poetry run mypy src                                 # перевірка типів
poetry run alembic heads                            # має бути рівно ОДНА голова міграцій
```

| Тип тестів (ТЗ, розділ 10) | Де |
|---|---|
| Unit: валідація, утиліти, бізнес-правила | `tests/*/test_*_service.py`, `tests/*/test_*schemas.py`, `tests/accounts/test_security.py` |
| Інтеграційні: ендпоінти + БД, JWT | `tests/*/test_*_router.py`, `tests/accounts/test_auth_dependencies.py`, `tests/interactions/`, `tests/movies/` |
| Функціональні (e2e): повний сценарій авторизації | `tests/accounts/test_auth_flow.py` |
| Фонові задачі й пошта | `tests/tasks/`, `tests/payments/test_payment_email.py` |

---

## Змінні оточення

Усі змінні — у [`.env.example`](.env.example). Скопіюйте його в `.env` і змініть за потреби.
**`.env` у git не потрапляє.**

| Змінна | Для чого |
|---|---|
| `SECRET_KEY` | підпис JWT. **На сервері — довгий випадковий рядок (32+ символи)** |
| `DATABASE_URL` | підключення до PostgreSQL |
| `REDIS_URL` | брокер Celery |
| `APP_BASE_URL` | адреса API — з неї будуються посилання в листах |
| `FRONTEND_URL` | куди Stripe повертає користувача після оплати |
| `DOCS_USERNAME`, `DOCS_PASSWORD` | логін до Swagger |
| `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS` | час життя токенів |
| `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM` | відправка листів |
| `MINIO_ENDPOINT` | сховище файлів для застосунку (у Docker — `http://minio:9000`) |
| `MINIO_PUBLIC_ENDPOINT` | адреса сховища в посиланнях для браузера (`http://localhost:9000`) |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | доступ до сховища |
| `AVATAR_URL_TTL_SECONDS` | скільки живе посилання на аватар |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | тестові ключі Stripe |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | налаштування контейнера PostgreSQL |

---

## Структура проєкту

Код поділений **по доменах**: кожен домен — окрема папка з однаковими шарами
`models → schemas → service → router`. Детальні правила — у [CONTRIBUTING.md](CONTRIBUTING.md).

```
src/
├── main.py              # створення застосунку, підключення роутерів
├── models.py            # реєстр усіх моделей (для Alembic і тестів)
├── core/                # спільне: налаштування, БД, помилки, пагінація, закритий Swagger
├── accounts/            # реєстрація, JWT, паролі, профіль і аватар, адмінка користувачів
├── movies/              # фільми, жанри, актори, режисери, сертифікати, фільтри, сідування
├── interactions/        # лайки, коментарі, рейтинги, обране
├── cart/                # кошик
├── orders/              # замовлення
├── payments/            # Stripe: оплата, вебхук, історія, повернення коштів
├── notifications/       # листи (через Celery) і сповіщення в застосунку
├── storage/             # S3-сховище файлів (аватари)
└── tasks/               # Celery: відправка листів, щогодинне очищення прострочених токенів
tests/                   # тести, тією ж структурою, що й src/
alembic/                 # міграції бази даних
.github/workflows/ci.yml # CI: lint, typecheck, tests, migrations
```

---

## Ендпоінти

Повний опис з прикладами — у Swagger: http://localhost:8000/docs.
Усі шляхи починаються з `/api/v1`. 🔒 — потрібен логін, 🛡 — модератор, 👑 — адмін.

<details>
<summary><b>Акаунти</b> — <code>/accounts</code></summary>

| Метод | Шлях | Що робить |
|---|---|---|
| POST | `/accounts/register` | реєстрація, лист з активацією (діє 24 год) |
| GET | `/accounts/activate?token=...` | активація з листа |
| POST | `/accounts/resend-activation` | новий лист активації |
| POST | `/accounts/login` | пара токенів: access + refresh |
| POST | `/accounts/refresh` | новий access-токен |
| POST | `/accounts/logout` | відкликати refresh-токен |
| POST | `/accounts/change-password` 🔒 | змінити пароль (потрібен старий) |
| POST | `/accounts/forgot-password` | лист для скидання пароля |
| POST | `/accounts/reset-password` | новий пароль за токеном з листа |
</details>

<details>
<summary><b>Профіль</b> — <code>/users/me/profile</code> 🔒</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/users/me/profile` | мій профіль |
| PATCH | `/users/me/profile` | змінити ім'я, прізвище, стать, дату народження, інфо |
| PUT | `/users/me/profile/avatar` | завантажити аватар (JPEG/PNG/WebP, до 2 МБ) |
| DELETE | `/users/me/profile/avatar` | прибрати аватар |
</details>

<details>
<summary><b>Адмінка користувачів</b> — <code>/admin/users</code> 👑</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/admin/users` | список з фільтрами `group`, `is_active`, `email` |
| GET | `/admin/users/{user_id}` | один користувач |
| PATCH | `/admin/users/{user_id}/group` | змінити групу |
| POST | `/admin/users/{user_id}/activate` | активувати вручну |
</details>

<details>
<summary><b>Каталог</b> — фільми, жанри, актори, режисери, сертифікати</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/movies` | каталог: пагінація, фільтри, сортування, пошук за назвою, описом, актором, режисером |
| GET | `/movies/{movie_id}` | деталі фільму з рейтингом і лайками |
| POST / PATCH / DELETE | `/movies`, `/movies/{movie_id}` 🛡 | керування фільмами (купленого фільму видалити не можна) |
| GET | `/genres` | жанри з кількістю фільмів |
| GET | `/genres/{genre_id}/movies` | фільми жанру |
| POST / PATCH / DELETE | `/genres`, `/genres/{genre_id}` 🛡 | керування жанрами |
| GET / POST / PATCH / DELETE | `/stars`, `/directors`, `/certifications` 🛡 | керування акторами, режисерами, сертифікатами |
</details>

<details>
<summary><b>Взаємодії</b> 🔒</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| POST | `/reactions` | лайк / дизлайк фільму (повторно — прибрати) |
| POST | `/ratings` | оцінка 1–10 |
| GET | `/movies/{movie_id}/comments` | коментарі фільму |
| POST | `/comments` | коментар або відповідь (`parent_id`) |
| POST | `/comments/{comment_id}/likes` | лайк коментаря |
| POST / DELETE | `/movies/{movie_id}/favorite` | додати / прибрати з обраного |
| GET | `/favorites` | моє обране з тими самими фільтрами й пошуком, що й каталог |
| GET | `/movies/{movie_id}/interactions/stats` | середній рейтинг і кількість лайків |
</details>

<details>
<summary><b>Сповіщення</b> — <code>/notifications</code> 🔒</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/notifications` | мої сповіщення (відповіді й лайки на коментарі), `?unread_only=true` |
| GET | `/notifications/unread-count` | кількість непрочитаних |
| PATCH | `/notifications/{notification_id}/read` | позначити прочитаним |
| POST | `/notifications/read-all` | позначити всі прочитаними |
</details>

<details>
<summary><b>Кошик і замовлення</b> 🔒</summary>

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/cart` | мій кошик |
| POST | `/cart/items` | додати фільм (куплений або вже доданий — помилка) |
| DELETE | `/cart/items/{movie_id}` | прибрати фільм |
| DELETE | `/cart` | очистити кошик |
| GET | `/cart/{user_id}` 👑 | кошик будь-якого користувача |
| POST | `/orders` | створити замовлення з кошика |
| GET | `/users/me/orders` | мої замовлення |
| GET | `/orders/{order_id}` | одне замовлення |
| POST | `/orders/{order_id}/cancel` | скасувати неоплачене замовлення |
| GET | `/orders` 👑 | усі замовлення з фільтрами (користувач, статус, дати) |
</details>

<details>
<summary><b>Оплата</b> — <code>/payments</code></summary>

| Метод | Шлях | Що робить |
|---|---|---|
| POST | `/payments/checkout/{order_id}` 🔒 | посилання на сторінку оплати Stripe |
| POST | `/payments/webhook` | вебхук Stripe (підпис перевіряється) |
| GET | `/payments/failed` | підказка після відхиленої оплати |
| GET | `/payments/me` 🔒 | моя історія платежів |
| GET | `/payments` 👑 | усі платежі з фільтрами |
| POST | `/payments/{payment_id}/refund` 👑 | повернення коштів |
</details>

---

## CI/CD

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) запускається на кожен
pull request і пуш у `develop` / `main`:

| Перевірка | Що робить |
|---|---|
| `lint` | flake8 |
| `typecheck` | mypy |
| `tests` | pytest з порогом покриття |
| `migrations` | на справжньому PostgreSQL: одна голова Alembic, міграції застосовуються, кожна модель має міграцію |

**Правила для гілок `develop` і `main`:** зміни — тільки через pull request,
**2 апруви** від інших учасників, усі перевірки зелені, усі коментарі закриті.

**Як працюємо:** гілка від свіжого `develop` → `feature/<домен>-<що>` → PR у `develop` →
ревʼю → мерж. У `main` потрапляє лише перевірений `develop`.

---

## Команда

| Роль | Хто | Що зробив(ла) |
|---|---|---|
| P1 — Lead / інфраструктура | Sofiia Pohuliailo | каркас, Docker, CI/CD, закритий Swagger, Celery і пошта, профіль, адмінка, сповіщення, mypy |
| P2 — Авторизація | CemXokenc | реєстрація, активація, JWT, паролі, e2e-тести авторизації |
| P3 — Сервіси | Artem Gusar | email-шаблони, Celery і celery-beat, модель сповіщень |
| P4 — Каталог | Yelyzaveta Hulchenko | фільми, жанри, фільтри й пошук, CRUD модератора, сідування |
| P5 — Взаємодії | Andrii Kinash | лайки, коментарі, рейтинги, обране, статистика фільму |
| P6 — Кошик і замовлення | Bohdan Sarai | кошик, замовлення, перевірки покупок |
| P7 — Оплата | Artem D | Stripe Checkout, вебхуки, історія платежів, повернення коштів |
