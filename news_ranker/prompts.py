"""Prompts for structured article decomposition."""

import json
from collections.abc import Mapping
from typing import Any

DECOMPOSITION_PROMPT_VERSION = "2026-04-29-current-schema-v1"

DECOMPOSITION_SYSTEM_PROMPT = """You decompose one news article into structured JSON.

Return JSON only. Do not return prose, markdown, code fences, comments, or explanations.
Use exactly these top-level keys and no extra keys:
- headline_neutral
- topic
- entities
- events
- claims
- context

The entities object must contain exactly these keys:
- people
- organizations
- locations

Each entity object must contain exactly:
- name: string, using one consistent canonical entity name
- role: string or null when unknown

Each event object must contain exactly:
- id: string such as "e1"
- when: ISO-like string when known, or null when unknown
- who: array of entity name strings
- what: neutral atomic event description
- where: string or null when unknown
- why: string or null when unknown
- how: string or null when unknown
- depends_on: array of prior event id strings

Each claim object must contain exactly:
- id: string such as "c1"
- statement: neutral atomic claim text
- type: one of "fact", "quote", "estimate", "prediction"
- attributed_to: entity name string or null when unavailable

Rules:
- Use atomic facts: one event or claim per item.
- Use neutral wording; do not add judgmental language.
- Preserve chronology in events.
- Attribute claims to source, speaker, or organization when available.
- Use consistent canonical names across entities, events, claims, and context.
- Do not infer facts not supported by article text.
- Use null for unknown scalar values, not empty strings.
- Use empty arrays when no items exist.
- For empty or missing article body, return the same schema with empty entities,
  events, claims, and context arrays.
- Forbid extra keys at every object level.
"""


def build_decomposition_user_prompt(article: Mapping[str, Any]) -> str:
    """Build user prompt containing raw article fields and metadata."""

    article_id = article.get("id") or article.get("article_id")
    title = (
        article.get("title")
        or article.get("headline")
        or article.get("headline_neutral")
    )
    body = article.get("body") or article.get("text") or article.get("content") or ""
    metadata = {
        key: value
        for key, value in article.items()
        if key
        not in {
            "id",
            "article_id",
            "title",
            "headline",
            "headline_neutral",
            "body",
            "text",
            "content",
        }
    }
    payload = {
        "id": article_id,
        "title": title,
        "body": body,
        "metadata": metadata,
    }

    return (
        "Decompose this article into the required structured JSON schema. "
        "Do not fetch URLs or use external sources; use only provided fields.\n\n"
        f"Article input:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    )
