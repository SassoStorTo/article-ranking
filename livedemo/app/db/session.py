from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from livedemo.app.config import get_settings


class Base(DeclarativeBase):
    """Base class for live demo SQLAlchemy models."""


def create_db_engine(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


engine = create_db_engine(get_settings().livedemo_db_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


def init_db(db_engine: Engine = engine) -> None:
    Base.metadata.create_all(bind=db_engine)


def iter_db(
    session_factory: sessionmaker[Session] = SessionLocal,
) -> Generator[Session]:
    with session_factory() as session:
        yield session
