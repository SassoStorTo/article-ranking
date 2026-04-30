from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

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
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> Response:
        self.calls.append(kwargs)
        return self.response


class FakeMistralClient:
    def __init__(self, response: Response) -> None:
        self.chat = FakeChat(response)


def response(content: Any) -> Response:
    return Response(choices=[Choice(message=Message(content=content))])


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
