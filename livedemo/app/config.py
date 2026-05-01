from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_DB_URL = "sqlite:////var/livedemo/db.sqlite"
DEFAULT_UPLOADS_DIR = "/var/livedemo/uploads"
DB_URL_ENV_VAR = "LIVEDEMO_DB_URL"
UPLOADS_DIR_ENV_VAR = "LIVEDEMO_UPLOADS_DIR"


@dataclass(frozen=True)
class Settings:
    db_url: str = DEFAULT_DB_URL
    uploads_dir: str = DEFAULT_UPLOADS_DIR


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if environ is None else environ
    return Settings(
        db_url=values.get(DB_URL_ENV_VAR, DEFAULT_DB_URL),
        uploads_dir=values.get(UPLOADS_DIR_ENV_VAR, DEFAULT_UPLOADS_DIR),
    )
