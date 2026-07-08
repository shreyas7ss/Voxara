from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session


def create_all():
    from app.models.listing import Listing  # noqa: F401 — registers the table with SQLModel.metadata
    SQLModel.metadata.create_all(engine)
