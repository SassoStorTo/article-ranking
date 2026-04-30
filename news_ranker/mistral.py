"""Mistral adapter for article decomposition."""

from __future__ import annotations

import os
from typing import Any

from mistralai.client import Mistral

DEFAULT_MISTRAL_MODEL = "mistral-small-latest"


class MistralDecompositionClient:
    """Low-level Mistral chat client for decomposition prompts."""

    def __init__(self, api_key: str | None = None, client: Any | None = None) -> None:
        resolved_api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if client is None and not resolved_api_key:
            raise ValueError("MISTRAL_API_KEY is required")
        self._client = client or Mistral(api_key=resolved_api_key)

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        """Return Mistral chat response text for supplied prompts."""

        response = self._client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return _response_text(response)


def _response_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("Mistral response missing choices")

    message = getattr(choices[0], "message", None)
    if message is None:
        raise ValueError("Mistral response missing message")

    content = getattr(message, "content", None)
    if isinstance(content, str):
        if not content:
            raise ValueError("Mistral response content is empty")
        return content

    if isinstance(content, list):
        text_parts = []
        for chunk in content:
            text = getattr(chunk, "text", None)
            if isinstance(text, str):
                text_parts.append(text)
        text = "".join(text_parts)
        if text:
            return text
        raise ValueError("Mistral response content chunks have no text")

    raise ValueError("Mistral response content is missing or unsupported")
