"""Shared test setup: every test gets its own empty database."""

import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.enums import Role
from app.models import User
from app.security import hash_password


@pytest.fixture(name="session")
def session_fixture():
    """Create a database in memory that disappears after each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="client")
def client_fixture(session):
    """Make every API route use the temporary test database."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(session, username, role, password="Password123"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def headers_for(client, username, password="Password123"):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(name="customer")
def customer_fixture(session, client):
    make_user(session, "amina", Role.customer)
    return headers_for(client, "amina")


@pytest.fixture(name="staff")
def staff_fixture(session, client):
    make_user(session, "karim", Role.staff)
    return headers_for(client, "karim")


@pytest.fixture(name="admin")
def admin_fixture(session, client):
    make_user(session, "owner", Role.admin)
    return headers_for(client, "owner")


@pytest.fixture(name="an_author")
def author_fixture(client, staff):
    return client.post(
        "/authors",
        json={"name": "Frank Herbert"},
        headers=staff,
    ).json()


@pytest.fixture(name="a_genre")
def genre_fixture(client, staff):
    return client.post(
        "/genres",
        json={"name": "fiction"},
        headers=staff,
    ).json()


@pytest.fixture(name="book_data")
def book_data_fixture(an_author, a_genre):
    return {
        "title": "Dune",
        "author_id": an_author["id"],
        "genre_ids": [a_genre["id"]],
        "price": 12.5,
        "stock": 3,
    }


@pytest.fixture(name="a_book")
def a_book_fixture(client, staff, book_data):
    """Create one book through the API for tests that need it."""
    response = client.post("/books", json=book_data, headers=staff)
    assert response.status_code == 201
    return response.json()
