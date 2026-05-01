from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

metadata = Base.metadata


def _enable_sqlite_foreign_keys(
    dbapi_connection: Any,
    connection_record: Any,  # noqa: ARG001
) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(db_url: str, *, echo: bool = False) -> Engine:
    engine = create_engine(db_url, echo=echo)
    if engine.url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def init_db(engine: Engine, db_metadata: MetaData = metadata) -> None:
    db_metadata.create_all(bind=engine)
