import json
from collections.abc import Mapping
from typing import Any

import pytest

from news_ranker.decompose import (
    DECOMPOSITION_SCHEMA_VERSION,
    DEFAULT_DECOMPOSITION_MODEL,
    DecompositionConfig,
    DecompositionError,
    decompose,
)
from news_ranker.prompts import DECOMPOSITION_PROMPT_VERSION

VALID_DECOMPOSITION = {
    "headline_neutral": "Officials describe reported event",
    "topic": "reported event",
    "entities": {
        "people": [{"name": "Jane Doe", "role": "witness"}],
        "organizations": [],
        "locations": [],
    },
    "events": [
        {
            "id": "e1",
            "when": None,
            "who": ["Jane Doe"],
            "what": "Jane Doe described the reported event",
            "where": None,
            "why": None,
            "how": None,
            "depends_on": [],
        }
    ],
    "claims": [
        {
            "id": "c1",
            "statement": "Jane Doe said the event happened quickly",
            "type": "quote",
            "attributed_to": "Jane Doe",
        }
    ],
    "context": ["Article supplied no external context."],
}


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict[str, str]] = []

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        })
        if not self.responses:
            raise AssertionError("client called too many times")
        return self.responses.pop(0)


def article(**overrides: Any) -> Mapping[str, Any]:
    base: dict[str, Any] = {
        "id": "article-1",
        "title": "Event report",
        "body": "Jane Doe described the event.",
    }
    base.update(overrides)
    return base


def response(payload: Mapping[str, Any] = VALID_DECOMPOSITION) -> str:
    return json.dumps(payload)


def test_decompose_validates_response_and_sets_article_id() -> None:
    client = FakeClient([response()])

    result = decompose(
        article(), client, config=DecompositionConfig(model="fake-model")
    )

    assert result.article_id == "article-1"
    assert result.headline_neutral == "Officials describe reported event"
    assert client.calls[0]["model"] == "fake-model"
    assert len(client.calls) == 1


def test_decompose_uses_mistral_default_model_with_injected_client() -> None:
    client = FakeClient([response()])

    decompose(article(), client)

    assert DEFAULT_DECOMPOSITION_MODEL == "mistral-small-latest"
    assert client.calls[0]["model"] == "mistral-small-latest"


def test_decompose_requires_id_title_and_body() -> None:
    client = FakeClient([response()])

    with pytest.raises(ValueError, match="id"):
        decompose(article(id=""), client)
    with pytest.raises(ValueError, match="title"):
        decompose(article(title=""), client)
    with pytest.raises(ValueError, match="body"):
        decompose(article(body=""), client)

    assert client.calls == []


def test_invalid_json_retries_once_with_error_context() -> None:
    client = FakeClient(["not json", response()])

    result = decompose(article(), client)

    assert result.article_id == "article-1"
    assert len(client.calls) == 2
    assert "JSON parse error" in client.calls[1]["user_prompt"]


def test_schema_validation_retries_once_with_error_context() -> None:
    bad_payload = dict(VALID_DECOMPOSITION)
    bad_payload["claims"] = [
        {
            "id": "c1",
            "statement": "bad claim type",
            "type": "rumor",
            "attributed_to": None,
        }
    ]
    client = FakeClient([response(bad_payload), response()])

    result = decompose(article(), client)

    assert result.article_id == "article-1"
    assert len(client.calls) == 2
    assert "Validation error" in client.calls[1]["user_prompt"]
    assert "rumor" in client.calls[1]["user_prompt"]


def test_final_bad_output_raises_deterministic_exception() -> None:
    client = FakeClient(["not json", "still not json"])

    with pytest.raises(DecompositionError, match="failed after 2 attempts"):
        decompose(article(), client)

    assert len(client.calls) == 2


def test_cache_hit_bypasses_client(tmp_path) -> None:
    first_client = FakeClient([response()])
    cached = decompose(article(), first_client, cache_dir=tmp_path)
    assert cached.article_id == "article-1"

    second_client = FakeClient([])
    result = decompose(article(), second_client, cache_dir=tmp_path)

    assert result.article_id == "article-1"
    assert result.headline_neutral == cached.headline_neutral
    assert second_client.calls == []


def test_cache_key_changes_with_prompt_schema_and_model_versions(tmp_path) -> None:
    decompose(
        article(),
        FakeClient([response()]),
        config=DecompositionConfig(model="model-a"),
        cache_dir=tmp_path,
    )
    decompose(
        article(),
        FakeClient([response()]),
        config=DecompositionConfig(model="model-b"),
        cache_dir=tmp_path,
    )
    decompose(
        article(),
        FakeClient([response()]),
        config=DecompositionConfig(
            model="model-a",
            prompt_version=f"{DECOMPOSITION_PROMPT_VERSION}-next",
        ),
        cache_dir=tmp_path,
    )
    decompose(
        article(),
        FakeClient([response()]),
        config=DecompositionConfig(
            model="model-a",
            schema_version=f"{DECOMPOSITION_SCHEMA_VERSION}-next",
        ),
        cache_dir=tmp_path,
    )

    cache_files = list((tmp_path / "decompositions").glob("*.json"))
    assert len(cache_files) == 4


def test_decompose_uses_only_injected_client() -> None:
    client = FakeClient([response()])

    result = decompose(article(url="https://example.invalid/story"), client)

    assert result.article_id == "article-1"
    assert len(client.calls) == 1
    assert "https://example.invalid/story" in client.calls[0]["user_prompt"]
    assert "Do not fetch URLs or use external sources" in client.calls[0]["user_prompt"]
