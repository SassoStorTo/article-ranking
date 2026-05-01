from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import (
    DB_URL_ENV_VAR,
    DEFAULT_DB_URL,
    DEFAULT_UPLOADS_DIR,
    UPLOADS_DIR_ENV_VAR,
    load_settings,
)
from app.db.session import init_db, make_engine, make_session_factory


def test_settings_default_and_override() -> None:
    default_settings = load_settings({})
    assert default_settings.db_url == DEFAULT_DB_URL
    assert default_settings.uploads_dir == DEFAULT_UPLOADS_DIR

    override_url = "sqlite:////tmp/livedemo-test.sqlite"
    override_uploads_dir = "/tmp/livedemo-uploads"

    override_settings = load_settings(
        {
            DB_URL_ENV_VAR: override_url,
            UPLOADS_DIR_ENV_VAR: override_uploads_dir,
        },
    )
    assert override_settings.db_url == override_url
    assert override_settings.uploads_dir == override_uploads_dir


def test_injected_sqlite_db_url_creates_usable_session(tmp_path: Path) -> None:
    db_path = tmp_path / "session.sqlite"
    engine = make_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("select 1")).scalar_one()

    assert result == 1
    assert db_path.exists()


def test_sqlite_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'fk.sqlite'}")
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        foreign_keys_enabled = session.execute(
            text("PRAGMA foreign_keys"),
        ).scalar_one()
        session.execute(text("create table parent (id integer primary key)"))
        session.execute(
            text(
                "create table child ("
                "id integer primary key, "
                "parent_id integer not null references parent(id)"
                ")",
            ),
        )
        session.commit()

    with session_factory() as session:
        with pytest.raises(IntegrityError):
            session.execute(text("insert into child (id, parent_id) values (1, 999)"))
            session.commit()

    assert foreign_keys_enabled == 1
