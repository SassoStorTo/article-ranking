from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from news_ranker.decompose import DecompositionConfig, decompose
from news_ranker.mistral import DEFAULT_MISTRAL_MODEL, MistralDecompositionClient


@dataclass
class Chunk:
    text: str


@dataclass
class Message:
    content: Any


@dataclass
class Choice:
    message: Message


@dataclass
class Response:
    choices: list[Choice]


class FakeChat:
    def __init__(self, responses: Response | list[Response]) -> None:
        if isinstance(responses, Response):
            self.responses = [responses]
        else:
            self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> Response:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("Mistral client called too many times")
        return self.responses.pop(0)


class FakeMistralClient:
    def __init__(self, responses: Response | list[Response]) -> None:
        self.chat = FakeChat(responses)


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


def response(content: Any) -> Response:
    return Response(choices=[Choice(message=Message(content=content))])


def article(**overrides: Any) -> Mapping[str, Any]:
    base: dict[str, Any] = {
        "id": "raw-article-1",
        "title": "Event report",
        "body": "Jane Doe described the event.",
    }
    base.update(overrides)
    return base


def decomposition_response() -> Response:
    return response(json.dumps(VALID_DECOMPOSITION))


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    with pytest.raises(ValueError, match="MISTRAL_API_KEY is required"):
        MistralDecompositionClient()


def test_client_receives_model_and_prompt_messages() -> None:
    fake_client = FakeMistralClient(response("model output"))
    client = MistralDecompositionClient(client=fake_client)

    result = client.complete(
        model=DEFAULT_MISTRAL_MODEL,
        system_prompt="system instructions",
        user_prompt="article payload",
    )

    assert result == "model output"
    assert fake_client.chat.calls == [
        {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": "system instructions"},
                {"role": "user", "content": "article payload"},
            ],
        }
    ]


def test_string_response_content_returns_text() -> None:
    fake_client = FakeMistralClient(response("plain text"))
    client = MistralDecompositionClient(client=fake_client)

    result = client.complete(model="m", system_prompt="s", user_prompt="u")

    assert result == "plain text"


def test_chunk_list_response_content_returns_joined_text() -> None:
    fake_client = FakeMistralClient(response([Chunk("part one"), Chunk(" part two")]))
    client = MistralDecompositionClient(client=fake_client)

    result = client.complete(model="m", system_prompt="s", user_prompt="u")

    assert result == "part one part two"


def test_explicit_api_key_constructs_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[str | None] = []

    class FakeMistral:
        def __init__(self, api_key: str | None) -> None:
            constructed.append(api_key)
            self.chat = FakeChat(response("ok"))

    monkeypatch.setattr("news_ranker.mistral.Mistral", FakeMistral)

    client = MistralDecompositionClient(api_key="secret")

    assert client.complete(model="m", system_prompt="s", user_prompt="u") == "ok"
    assert constructed == ["secret"]


def test_env_api_key_constructs_sdk_client(monkeypatch: pytest.MonkeyPatch) -> None:
    constructed: list[str | None] = []

    class FakeMistral:
        def __init__(self, api_key: str | None) -> None:
            constructed.append(api_key)
            self.chat = FakeChat(response("ok"))

    monkeypatch.setenv("MISTRAL_API_KEY", "env-secret")
    monkeypatch.setattr("news_ranker.mistral.Mistral", FakeMistral)

    client = MistralDecompositionClient()

    assert client.complete(model="m", system_prompt="s", user_prompt="u") == "ok"
    assert constructed == ["env-secret"]


def test_mistral_client_composes_with_decompose_default_model() -> None:
    fake_client = FakeMistralClient(decomposition_response())
    client = MistralDecompositionClient(client=fake_client)

    result = decompose(article(), client)

    assert result.article_id == "raw-article-1"
    assert result.headline_neutral == "Officials describe reported event"
    assert result.claims[0].statement == "Jane Doe said the event happened quickly"
    assert len(fake_client.chat.calls) == 1
    assert fake_client.chat.calls[0]["model"] == DEFAULT_MISTRAL_MODEL
    assert fake_client.chat.calls[0]["messages"][0]["role"] == "system"
    assert fake_client.chat.calls[0]["messages"][1]["role"] == "user"


def test_mistral_client_composes_with_explicit_config_and_cache(
    tmp_path,
) -> None:
    fake_client = FakeMistralClient([decomposition_response()])
    client = MistralDecompositionClient(client=fake_client)
    config = DecompositionConfig(model="mistral-large-latest")

    first = decompose(article(), client, config=config, cache_dir=tmp_path)
    second = decompose(article(), client, config=config, cache_dir=tmp_path)

    assert first.article_id == "raw-article-1"
    assert second.article_id == "raw-article-1"
    assert first.topic == "reported event"
    assert second.topic == "reported event"
    assert len(fake_client.chat.calls) == 1
    assert fake_client.chat.calls[0]["model"] == "mistral-large-latest"
