from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite needs this one extra setting. PostgreSQL doesn't know it and would refuse to connect.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    pool_pre_ping=True,  # check a connection still works before using it
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
