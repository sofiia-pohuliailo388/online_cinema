# 🎬 Online Cinema API
 
Backend for an online cinema built with **FastAPI**: registration with email activation,
JWT authentication, a movie catalog with search and filters, likes, comments, ratings,
favorites, a shopping cart, orders and payments via **Stripe**.
 
> 👩‍💻 Writing code in this repository? Read **[CONTRIBUTING.md](CONTRIBUTING.md)** first.
 
---
 
## 🌐 Live Demo
 
The project is deployed on AWS EC2 with HTTPS:
 
| What | Link | Credentials |
|---|---|---|
| **Swagger UI** | https://16-171-245-95.sslip.io/docs | `admin` / `MyStrongPass123` |
| ReDoc | https://16-171-245-95.sslip.io/redoc | `admin` / `MyStrongPass123` |
| Health check | https://16-171-245-95.sslip.io/health | — |
| API base URL | https://16-171-245-95.sslip.io/api/v1 | — |
 
**Demo accounts** (already activated, for `POST /api/v1/accounts/login`):
 
| Role | Email | Password |
|---|---|---|
| 👤 User | `user@cinema.com` | `Str0ng!Pass` |
| 👑 Admin | `admin@cinema.com` | `Str0ng!Pass` |
 
> The Swagger credentials only open the `/docs` page. To call protected endpoints, log in
> with a demo account (`POST /api/v1/accounts/login`), copy `access_token` from the response,
> click **Authorize** 🔒 and paste the token. Access tokens live 15 minutes.
 
---
 
## Contents
 
- [Live Demo](#-live-demo)
- [Tech Stack](#tech-stack)
- [Quick Start (Docker)](#quick-start-docker)
- [Services and URLs](#services-and-urls)
- [Using the API](#using-the-api)
- [Local Development without Docker](#local-development-without-docker)
- [Tests and Quality Checks](#tests-and-quality-checks)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Endpoints](#endpoints)
- [CI/CD](#cicd)
- [Deployment](#deployment)
- [Team](#team)
---
 
## Tech Stack
 
| Area | Tools |
|---|---|
| API | FastAPI, Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| Background jobs | Celery + Celery Beat, Redis |
| Email | SMTP (MailHog in development), Jinja2 templates |
| Files (avatars) | S3-compatible storage — [Silo](https://silo.pigsty.io) (a MinIO fork), boto3 |
| Payments | Stripe Checkout + webhooks |
| Dependencies | Poetry |
| Code quality | pytest + pytest-cov, flake8, mypy |
| Infrastructure | Docker, Docker Compose, GitHub Actions, AWS EC2, Caddy |
 
---
 
## Quick Start (Docker)
 
All you need is [Docker Desktop](https://www.docker.com/products/docker-desktop/).
 
```bash
git clone https://github.com/sofiia-pohuliailo388/online_cinema.git
cd online_cinema
cp .env.example .env
docker compose up --build
```
 
Once the logs show `Uvicorn running on http://0.0.0.0:8000`, everything is ready.
Database migrations are applied automatically on startup.
 
**Fill the catalog with demo movies** (in a separate terminal):
 
```bash
docker compose exec app python -m src.movies.seed
```
 
Stop: `Ctrl + C` or `docker compose down`.
Stop and delete all data: `docker compose down -v`.
 
---
 
## Services and URLs
 
| Service | URL | Credentials |
|---|---|---|
| **Swagger (API docs)** | http://localhost:8000/docs | `admin` / `admin` |
| API | http://localhost:8000/api/v1 | — |
| Health check | http://localhost:8000/health | — |
| **MailHog** (inbox for test emails) | http://localhost:8025 | — |
| **Storage console** (avatars) | http://localhost:9001 | `minioadmin` / `minioadmin` |
| PostgreSQL | `localhost:5432` | `postgres` / `postgres`, database `cinema` |
| Redis | `localhost:6379` | — |
 
> Swagger is protected with HTTP Basic auth (a project requirement). The credentials are set
> in `.env`: `DOCS_USERNAME`, `DOCS_PASSWORD`.
 
---
 
## Using the API
 
### 1. Register and activate an account
 
1. Swagger → `POST /api/v1/accounts/register` → email and password
   (at least 8 characters with an uppercase letter, a lowercase letter, a digit and a special
   character, e.g. `Str0ng!Pass`).
2. Open http://localhost:8025 → the **Activation link** email → **Activate Account**.
> The link works once: opening it again shows `Invalid activation token`, which is expected.
 
### 2. Log in to Swagger
 
1. `POST /api/v1/accounts/login` → copy `access_token` from the response.
2. Click **Authorize** 🔒 at the top of Swagger → paste the token → **Authorize**.
An access token lives 15 minutes. Get a new one with `POST /api/v1/accounts/refresh`
using your `refresh_token`.
 
### 3. Become a moderator or admin
 
New users belong to the `USER` group. Promote the first admin directly in the database:
 
```bash
docker compose exec db psql -U postgres -d cinema -c \
  "update users set group_id = (select id from user_groups where name = 'ADMIN') \
   where email = 'you@example.com';"
```
 
Then log in again. From now on the admin can change other users' groups via
`PATCH /api/v1/admin/users/{user_id}/group`.
 
| Group | Can |
|---|---|
| `USER` | browse the catalog, like, comment, favorite, use the cart, orders, payments, profile |
| `MODERATOR` | everything above + manage movies, genres, stars, directors, certifications |
| `ADMIN` | everything above + manage users (groups, manual activation), view all carts, orders and payments, issue refunds |
 
### 4. Buy a movie
 
1. `POST /api/v1/cart/items` — add a movie to the cart.
2. `POST /api/v1/orders` — create an order from the cart.
3. `POST /api/v1/payments/checkout/{order_id}` — get a Stripe payment link.
4. Pay with the test card `4242 4242 4242 4242` (any future date, any CVC).
5. Stripe sends a webhook → the order becomes `paid` and a confirmation email arrives in MailHog.
> Payments need Stripe test keys in `.env` (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`).
> To receive webhooks locally, use the [Stripe CLI](https://docs.stripe.com/stripe-cli):
> `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`
 
---
 
## Local Development without Docker
 
You need Python 3.12+ and [Poetry](https://python-poetry.org/docs/#installation).
 
```bash
poetry install
```
 
The API itself needs PostgreSQL and Redis. The easiest way is to start them with Docker:
 
```bash
docker compose up -d db redis mailhog
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cinema poetry run alembic upgrade head
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cinema poetry run uvicorn src.main:app --reload
```
 
> Service addresses in `.env` point to Docker hosts (`db`, `redis`, `mailhog`).
> Outside Docker, use `localhost` as in the commands above.
 
---
 
## Tests and Quality Checks
 
Tests run on in-memory SQLite, so **Docker is not needed**. Celery runs tasks immediately,
no real emails are sent, and Stripe and file storage are replaced with mocks.
 
```bash
poetry run pytest                                   # all tests
poetry run pytest tests/movies -v                   # tests of one domain
poetry run pytest --cov=src --cov-report=term       # with coverage
poetry run flake8 .                                 # linter
poetry run mypy src                                 # type checking
poetry run alembic heads                            # must show exactly ONE migration head
```
 
**419 tests**, **77% coverage** (CI requires at least 75%).
 
| Test type | Where |
|---|---|
| Unit: validation, utilities, business rules | `tests/*/test_*_service.py`, `tests/*/test_*schemas.py`, `tests/accounts/test_security.py` |
| Integration: endpoints + database, JWT | `tests/*/test_*_router.py`, `tests/accounts/test_auth_dependencies.py`, `tests/interactions/`, `tests/movies/` |
| Functional (e2e): full authentication flow | `tests/accounts/test_auth_flow.py` |
| Background jobs and email | `tests/tasks/`, `tests/payments/test_payment_email.py` |
 
---
 
## Environment Variables
 
All variables are listed in [`.env.example`](.env.example). Copy it to `.env` and adjust as
needed. **`.env` is never committed to git.**
 
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key. **On a server, use a long random string (32+ characters)** |
| `DATABASE_URL` | PostgreSQL connection |
| `REDIS_URL` | Celery broker |
| `APP_BASE_URL` | public API URL, used to build links in emails |
| `FRONTEND_URL` | where Stripe redirects the user after payment |
| `DOCS_USERNAME`, `DOCS_PASSWORD` | Swagger login |
| `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS` | token lifetimes |
| `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM` | sending emails |
| `MINIO_ENDPOINT` | file storage address for the app (in Docker: `http://minio:9000`) |
| `MINIO_PUBLIC_ENDPOINT` | storage address used in browser links (`http://localhost:9000`) |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | storage access |
| `AVATAR_URL_TTL_SECONDS` | how long an avatar link stays valid |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Stripe test keys |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL container settings |
| `DOMAIN` | production only: the domain Caddy issues an HTTPS certificate for |
 
---
 
## Project Structure
 
The code is split **by domain**: each domain is a separate folder with the same layers
`models → schemas → service → router`. Detailed rules are in [CONTRIBUTING.md](CONTRIBUTING.md).
 
```
src/
├── main.py              # app creation, router registration
├── models.py            # registry of all models (for Alembic and tests)
├── core/                # shared: settings, database, errors, pagination, protected Swagger
├── accounts/            # registration, JWT, passwords, profile and avatar, user admin
├── movies/              # movies, genres, stars, directors, certifications, filters, seed
├── interactions/        # likes, comments, ratings, favorites
├── cart/                # shopping cart
├── orders/              # orders
├── payments/            # Stripe: checkout, webhook, history, refunds
├── notifications/       # emails (via Celery) and in-app notifications
├── storage/             # S3 file storage (avatars)
└── tasks/               # Celery: sending emails, hourly cleanup of expired tokens
tests/                   # tests, mirroring the src/ structure
alembic/                 # database migrations
.github/workflows/       # ci.yml (checks) and deploy.yml (auto-deploy)
docker-compose.prod.yml  # production overrides (Caddy, no reload, restart policies)
Caddyfile                # reverse proxy + automatic HTTPS
```
 
---
 
## Endpoints
 
Full documentation with examples is in Swagger: http://localhost:8000/docs
(or the [live demo](https://16-171-245-95.sslip.io/docs)).
All paths start with `/api/v1`. 🔒 login required, 🛡 moderator, 👑 admin.
 
<details>
<summary><b>Accounts</b> — <code>/accounts</code></summary>
| Method | Path | Description |
|---|---|---|
| POST | `/accounts/register` | register, sends an activation email (valid 24 h) |
| GET | `/accounts/activate?token=...` | activate from the email link |
| POST | `/accounts/resend-activation` | send a new activation email |
| POST | `/accounts/login` | get a token pair: access + refresh |
| POST | `/accounts/refresh` | get a new access token |
| POST | `/accounts/logout` | revoke the refresh token |
| POST | `/accounts/change-password` 🔒 | change password (old password required) |
| POST | `/accounts/forgot-password` | send a password reset email |
| POST | `/accounts/reset-password` | set a new password using the token from the email |
</details>
<details>
<summary><b>Profile</b> — <code>/users/me/profile</code> 🔒</summary>
| Method | Path | Description |
|---|---|---|
| GET | `/users/me/profile` | my profile |
| PATCH | `/users/me/profile` | update first name, last name, gender, date of birth, info |
| PUT | `/users/me/profile/avatar` | upload an avatar (JPEG/PNG/WebP, up to 2 MB) |
| DELETE | `/users/me/profile/avatar` | remove the avatar |
</details>
<details>
<summary><b>User admin</b> — <code>/admin/users</code> 👑</summary>
| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | list with filters `group`, `is_active`, `email` |
| GET | `/admin/users/{user_id}` | one user |
| PATCH | `/admin/users/{user_id}/group` | change group |
| POST | `/admin/users/{user_id}/activate` | activate manually |
</details>
<details>
<summary><b>Catalog</b> — movies, genres, stars, directors, certifications</summary>
| Method | Path | Description |
|---|---|---|
| GET | `/movies` | catalog: pagination, filters, sorting, search by title, description, star, director |
| GET | `/movies/{movie_id}` | movie details with rating and likes |
| POST / PATCH / DELETE | `/movies`, `/movies/{movie_id}` 🛡 | manage movies (a purchased movie cannot be deleted) |
| GET | `/genres` | genres with movie counts |
| GET | `/genres/{genre_id}/movies` | movies of a genre |
| POST / PATCH / DELETE | `/genres`, `/genres/{genre_id}` 🛡 | manage genres |
| GET / POST / PATCH / DELETE | `/stars`, `/directors`, `/certifications` 🛡 | manage stars, directors, certifications |
</details>
<details>
<summary><b>Interactions</b> 🔒</summary>
| Method | Path | Description |
|---|---|---|
| POST | `/reactions` | like / dislike a movie (repeat to remove) |
| POST | `/ratings` | rate from 1 to 10 |
| GET | `/movies/{movie_id}/comments` | movie comments |
| POST | `/comments` | comment or reply (`parent_id`) |
| POST | `/comments/{comment_id}/likes` | like a comment |
| POST / DELETE | `/movies/{movie_id}/favorite` | add to / remove from favorites |
| GET | `/favorites` | my favorites with the same filters and search as the catalog |
| GET | `/movies/{movie_id}/interactions/stats` | average rating and like counts |
</details>
<details>
<summary><b>Notifications</b> — <code>/notifications</code> 🔒</summary>
| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | my notifications (replies and likes on comments), `?unread_only=true` |
| GET | `/notifications/unread-count` | number of unread notifications |
| PATCH | `/notifications/{notification_id}/read` | mark as read |
| POST | `/notifications/read-all` | mark all as read |
</details>
<details>
<summary><b>Cart and orders</b> 🔒</summary>
| Method | Path | Description |
|---|---|---|
| GET | `/cart` | my cart |
| POST | `/cart/items` | add a movie (error if purchased or already in the cart) |
| DELETE | `/cart/items/{movie_id}` | remove a movie |
| DELETE | `/cart` | clear the cart |
| GET | `/cart/{user_id}` 👑 | any user's cart |
| POST | `/orders` | create an order from the cart |
| GET | `/users/me/orders` | my orders |
| GET | `/orders/{order_id}` | one order |
| POST | `/orders/{order_id}/cancel` | cancel an unpaid order |
| GET | `/orders` 👑 | all orders with filters (user, status, dates) |
</details>
<details>
<summary><b>Payments</b> — <code>/payments</code></summary>
| Method | Path | Description |
|---|---|---|
| POST | `/payments/checkout/{order_id}` 🔒 | Stripe payment page link |
| POST | `/payments/webhook` | Stripe webhook (signature verified) |
| GET | `/payments/failed` | hint page after a declined payment |
| GET | `/payments/me` 🔒 | my payment history |
| GET | `/payments` 👑 | all payments with filters |
| POST | `/payments/{payment_id}/refund` 👑 | refund |
</details>
---
 
## CI/CD
 
**CI** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every pull request
and every push to `develop` / `main`:
 
| Check | What it does |
|---|---|
| `lint` | flake8 |
| `typecheck` | mypy |
| `tests` | pytest with a coverage threshold (75%) |
| `migrations` | on real PostgreSQL: one Alembic head, migrations apply, every model has a migration |
 
**CD** — [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) runs on every push to
`main`: GitHub Actions connects to the EC2 server over SSH, pulls `main`, rebuilds and restarts
the containers, and checks `/health`. It can also be started manually
(**Actions → Deploy → Run workflow**).
 
**Branch rules for `develop` and `main`:** changes only via pull request,
**2 approvals** from other team members, all checks green, all conversations resolved,
no force pushes.
 
**Workflow:** branch off a fresh `develop` → `feature/<domain>-<what>` → PR into `develop` →
review → merge. `main` only receives a reviewed `develop` after mentor approval, which triggers
the deploy.
 
---
 
## Deployment
 
Production runs on **AWS EC2** (Ubuntu, `t3.small`) with a static Elastic IP.
**Caddy** sits in front of the app as a reverse proxy and gets HTTPS certificates
from Let's Encrypt automatically.
 
```bash
# on the server, once
git clone https://github.com/sofiia-pohuliailo388/online_cinema.git
cd online_cinema
cp .env.example .env    # set SECRET_KEY, DOCS_PASSWORD, DOMAIN, APP_BASE_URL, MINIO_PUBLIC_ENDPOINT
 
# start / update
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
 
`docker-compose.prod.yml` extends the base file: no `--reload`, two uvicorn workers,
Caddy on ports 80/443, `restart: unless-stopped` for every service.
Only ports 22, 80 and 443 are open in the EC2 security group.
 
GitHub secrets used by the deploy workflow: `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`.
 
---
 
## Team
 
**Team Sweet Caramels** · Mentor: **Vadym Pusiak**
 
| Role | Member | Contribution |
|---|---|---|
| P1 — Team lead / infrastructure | Sofiia Pohuliailo | project skeleton, Docker, CI/CD, AWS deployment, protected Swagger, Celery and email setup, profile, user admin, notifications API, mypy |
| P2 — Authentication | Olexandr Plotnikov | registration, activation, JWT, passwords, e2e auth tests |
| P3 — Services | Artem Gusar | email templates, Celery and Celery Beat, notification model |
| P4 — Catalog | Yelyzaveta Hulchenko | movies, genres, filters and search, moderator CRUD, seed data |
| P5 — Interactions | Andrii Kinash | likes, comments, ratings, favorites, movie stats |
| P6 — Cart and orders | Bohdan Sarai | cart, orders, purchase checks |
| P7 — Payments | Artem Dmytrashko | Stripe Checkout, webhooks, payment history, refunds |
