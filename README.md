# Book Store API

A FastAPI backend for a book store: users sign up and log in with JWTs, staff
manage a relational catalogue of books, authors and genres, and customers place
orders. Access is controlled by role (`customer` / `staff` / `admin`) and, for
orders, by ownership.

Built on **FastAPI + SQLModel + PostgreSQL**, with a full **pytest** suite and
a **Ruff / MyPy / Pylint** quality gate wired into a pre-commit hook.

---

## Features

- **Auth** — sign-up, login (OAuth2 password flow), JWT access tokens, `/auth/me`
- **Roles** — `customer`, `staff`, `admin`, enforced on every write route
- **Users** — admins can list users, change roles, enable/disable accounts
- **Catalogue** — books, authors and genres as real relational tables:
  - author ↔ book: one-to-many
  - book ↔ genre: many-to-many, through a `book_genre` junction table
  - author ↔ profile: one-to-one (optional bio/website)
- **Orders** — stock-aware purchasing, ownership-based access (a customer only
  ever sees their own orders), status transitions (`pending` → `shipped` /
  `cancelled`)
- **Security** — Argon2 password hashing, timing-safe login, JWTs signed with
  a required `SECRET_KEY`, no client-controlled `id`/`role`/`user_id` anywhere
- **Tests** — unit tests for validators/security helpers, integration tests
  for every route, permission and ownership rule, run against an isolated
  in-memory database
- **Code quality** — Ruff (lint + format), MyPy (type checking), Pylint,
  wired into `pre-commit` so every commit is checked automatically

---

## Tech stack

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| ORM / models | SQLModel (SQLAlchemy) |
| Database | PostgreSQL (SQLite fallback for local/dev use) |
| Auth | OAuth2 password flow + JWT (`pyjwt`) |
| Password hashing | Argon2 (`pwdlib`) |
| Settings | `pydantic-settings` (`.env`) |
| Testing | `pytest` + `httpx`/`TestClient` |
| Quality | Ruff, MyPy, Pylint, `pre-commit` |

---

## Project structure

```
project-2/
├── main.py                 # creates the app, plugs in the routers
├── create_admin.py         # creates the first admin account (CLI script)
├── pyproject.toml          # Ruff / MyPy / Pylint / pytest configuration
├── .pre-commit-config.yaml # runs Ruff + MyPy on every commit
├── requirements.txt
├── .env                    # SECRET_KEY, DATABASE_URL, etc. (never committed)
├── app/
│   ├── config.py            # Settings, read from .env
│   ├── database.py          # engine + session
│   ├── enums.py             # Role, OrderStatus
│   ├── models.py            # User, Author, AuthorProfile, Genre, Book,
│   │                        # BookGenreLink, Order — the real tables
│   ├── security.py          # password hashing + JWTs
│   ├── dependencies.py      # get_current_user, require_roles
│   ├── dtos/
│   │   ├── requests.py       # what a client is allowed to send
│   │   └── responses.py      # what a client is allowed to see
│   └── routers/
│       ├── auth.py           # register, login, /auth/me
│       ├── users.py          # admin: roles, enable/disable
│       ├── authors.py        # authors + their profile
│       ├── genres.py         # genres
│       ├── books.py          # the catalogue
│       └── orders.py         # placing and managing orders
└── tests/
    ├── test_dtos.py           # validator unit tests
    ├── test_security.py       # hashing + token unit tests
    ├── test_auth.py           # sign-up / login integration tests
    ├── test_books.py          # catalogue + role integration tests
    ├── test_orders.py         # orders + ownership integration tests
    └── test_relationships.py  # authors/genres relational behaviour
```

---

## Getting started

### 1. Clone and set up a virtual environment

```bash
git clone <your-repo-url>
cd project-2
python -m venv venv
```

**macOS / Linux:** `source venv/bin/activate`
**Windows (PowerShell):** `venv\Scripts\Activate.ps1`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> If `requirements.txt` was ever generated on Windows PowerShell with
> `pip freeze > requirements.txt`, save it as **UTF-8**, not UTF-16 —
> otherwise `pip install -r requirements.txt` can fail for anyone else who
> clones the repo:
> ```powershell
> pip freeze | Out-File -Encoding utf8 requirements.txt
> ```

### 3. Configure environment variables

Create a `.env` file in the project root (never commit this file):

```
SECRET_KEY=<64 random hex characters — generate with the command below>
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=false
DATABASE_URL=postgresql://postgres:devpassword@localhost:5432/bookstore
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Without `DATABASE_URL`, the app falls back to a local SQLite file
(`sqlite:///./bookstore.db`) — handy for quick local testing.

### 4. Start PostgreSQL (Docker)

```bash
docker run --name bookstore-db -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=bookstore -p 5432:5432 -d postgres:16
```

### 5. Create the first admin account

Nobody can register as an admin through the API — the first one is created
from the command line:

```bash
python create_admin.py
```

### 6. Run the server

```bash
uvicorn main:app --reload
```

Interactive docs: **http://127.0.0.1:8000/docs**

---

## API overview

All write routes require a bearer token (`Authorization: Bearer <token>`).
Get one from `POST /auth/login`.

| Resource | Route | Method | Who |
|---|---|---|---|
| Auth | `/auth/register` | POST | anyone |
| | `/auth/login` | POST | anyone |
| | `/auth/me` | GET | logged in |
| Users | `/users` | GET | admin |
| | `/users/{id}/role` | PATCH | admin |
| | `/users/{id}/active` | PATCH | admin |
| Authors | `/authors` | GET | anyone |
| | `/authors/{id}` | GET | anyone |
| | `/authors` | POST | staff/admin |
| | `/authors/{id}/profile` | PUT | staff/admin |
| | `/authors/{id}` | DELETE | admin |
| Genres | `/genres` | GET | anyone |
| | `/genres` | POST | staff/admin |
| | `/genres/{id}` | DELETE | admin |
| Books | `/books` | GET | anyone |
| | `/books/{id}` | GET | anyone |
| | `/books` | POST | staff/admin |
| | `/books/{id}` | PATCH | staff/admin |
| | `/books/{id}` | DELETE | admin |
| Orders | `/orders` | POST | logged in |
| | `/orders` | GET | logged in (own orders, or all for staff/admin) |
| | `/orders/{id}` | GET | owner or staff/admin |
| | `/orders/{id}/status` | PATCH | staff/admin |

Full request/response shapes are in `/docs` (Swagger UI) or `/redoc`.

---

## Running the tests

```bash
pip install pytest httpx
pytest
```

Tests run against an isolated in-memory SQLite database created fresh for
every test (see `conftest.py`) — they never touch your real `bookstore` or
`bookstore.db`.

```bash
pytest -v          # see every test by name
pytest -k books     # run only tests matching "books"
```

---

## Code quality

```bash
ruff format .                       # one consistent style
ruff check .                        # lint
mypy .                               # type checking
pylint app main.py create_admin.py  # deeper design/style pass
```

Or let it run automatically on every commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # run once across the whole repo
```

---

## Security notes

- Passwords are hashed with Argon2 and never stored or logged in plain text.
- JWTs carry only a user id and expiry — no role — so a demoted or disabled
  account loses access on its very next request, without waiting for the
  token to expire.
- Every request DTO is an allow-list: a client can never set an `id`, choose
  its own `role`, or attach an order to someone else's `user_id`.
- `SECRET_KEY` is required (no default) and must never be committed — see
  `.gitignore`.

## Known limitations

- No HTTPS termination (add a reverse proxy such as Nginx/Caddy in production).
- No token revocation / logout — a leaked token stays valid until it expires.
- No rate limiting on login attempts.
- `price` is stored as `float`, not `Decimal` — fine for this project, not for
  a real payment system.
- Simultaneous orders for the last copy of a book are not fully race-safe
  (see `orders.py`).
