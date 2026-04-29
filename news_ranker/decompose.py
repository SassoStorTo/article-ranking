"""Provider-agnostic article decomposition flow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from news_ranker.prompts import (
    DECOMPOSITION_PROMPT_VERSION,
    DECOMPOSITION_SYSTEM_PROMPT,
    build_decomposition_user_prompt,
)
from news_ranker.schemas import StructuredArticle

DECOMPOSITION_SCHEMA_VERSION = "current-schema-v1"
DEFAULT_DECOMPOSITION_MODEL = "default"


class DecompositionClient(Protocol):
    """Minimal client protocol for LLM-backed decomposition."""

    def complete(
        self, *, model: str, system_prompt: str, user_prompt: str
    ) -> str:
        """Return model text for the supplied prompts."""


@dataclass(frozen=True)
class DecompositionConfig:
    """Configuration included in provider call and cache key."""

    model: str = DEFAULT_DECOMPOSITION_MODEL
    prompt_version: str = DECOMPOSITION_PROMPT_VERSION
    schema_version: str = DECOMPOSITION_SCHEMA_VERSION


class DecompositionError(ValueError):
    """Raised when model output cannot be parsed into a structured article."""


def decompose(
    article: Mapping[str, Any],
    client: DecompositionClient,
    config: DecompositionConfig | None = None,
    cache_dir: str | Path | None = None,
) -> StructuredArticle:
    """Decompose raw article mapping with injected client, retry, and cache."""

    resolved_config = config or DecompositionConfig()
    article_id = _required_article_text(article, ("id", "article_id"), "id")
    _required_article_text(
        article, ("title", "headline", "headline_neutral"), "title"
    )
    _required_article_text(article, ("body", "text", "content"), "body")

    cache_path = _cache_path(article, resolved_config, cache_dir)
    if cache_path is not None and cache_path.exists():
        cached = StructuredArticle.model_validate_json(
            cache_path.read_text(encoding="utf-8")
        )
        return cached.model_copy(update={"article_id": article_id})

    user_prompt = build_decomposition_user_prompt(article)
    last_error: str | None = None
    for attempt in range(2):
        prompt = user_prompt
        if last_error is not None:
            prompt = _retry_user_prompt(user_prompt, last_error)

        output = client.complete(
            model=resolved_config.model,
            system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
        try:
            payload = json.loads(output)
            structured = StructuredArticle.model_validate(payload)
        except json.JSONDecodeError as error:
            last_error = f"JSON parse error: {error}"
        except ValidationError as error:
            last_error = f"Validation error: {error}"
        else:
            structured = structured.model_copy(update={"article_id": article_id})
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    structured.model_dump_json(), encoding="utf-8"
                )
            return structured

        if attempt == 1:
            raise DecompositionError(
                f"decomposition failed after 2 attempts: {last_error}"
            )

    raise DecompositionError("decomposition failed after 2 attempts")


def _required_article_text(
    article: Mapping[str, Any], keys: tuple[str, ...], label: str
) -> str:
    for key in keys:
        value = article.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(f"article must include non-empty string {label}")


def _cache_path(
    article: Mapping[str, Any],
    config: DecompositionConfig,
    cache_dir: str | Path | None,
) -> Path | None:
    if cache_dir is None:
        return None
    key_payload = {
        "article": _jsonable(article),
        "model": config.model,
        "prompt_version": config.prompt_version,
        "schema_version": config.schema_version,
    }
    key_bytes = json.dumps(
        key_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(key_bytes).hexdigest()
    return Path(cache_dir) / "decompositions" / f"{digest}.json"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return repr(value)


def _retry_user_prompt(base_prompt: str, last_error: str) -> str:
    return (
        f"{base_prompt}\n\nPrevious response was invalid. {last_error}\n"
        "Return corrected JSON only, with the exact required schema."
    )
