from collections.abc import Generator

from sqlalchemy.orm import Session

from livedemo.app.config import Settings
from livedemo.app.config import get_settings as load_settings
from livedemo.app.db.session import iter_db


def get_settings() -> Settings:
    return load_settings()


def get_db() -> Generator[Session]:
    yield from iter_db()
