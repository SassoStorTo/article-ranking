from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_DB_URL = "sqlite:////var/livedemo/db.sqlite"
DB_URL_ENV_VAR = "LIVEDEMO_DB_URL"


@dataclass(frozen=True)
class Settings:
    db_url: str = DEFAULT_DB_URL


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if environ is None else environ
    return Settings(db_url=values.get(DB_URL_ENV_VAR, DEFAULT_DB_URL))
