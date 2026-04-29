from news_ranker.prompts import (
    DECOMPOSITION_PROMPT_VERSION,
    DECOMPOSITION_SYSTEM_PROMPT,
    build_decomposition_user_prompt,
)


def test_decomposition_prompt_declares_current_schema_keys_and_shapes() -> None:
    prompt = DECOMPOSITION_SYSTEM_PROMPT

    assert DECOMPOSITION_PROMPT_VERSION
    for key in [
        "headline_neutral",
        "topic",
        "entities",
        "events",
        "claims",
        "context",
    ]:
        assert key in prompt
    for key in ["people", "organizations", "locations"]:
        assert key in prompt
    for key in ["name", "role"]:
        assert key in prompt
    for key in ["id", "when", "who", "what", "where", "why", "how", "depends_on"]:
        assert key in prompt
    for key in ["statement", "type", "attributed_to"]:
        assert key in prompt


def test_decomposition_prompt_uses_current_entity_schema_not_brief_schema() -> None:
    prompt = DECOMPOSITION_SYSTEM_PROMPT

    assert "canonical_name" not in prompt
    assert "canonical names" in prompt or "canonical entity name" in prompt


def test_decomposition_prompt_forbids_non_json_and_extra_keys() -> None:
    prompt = DECOMPOSITION_SYSTEM_PROMPT.lower()

    assert "json only" in prompt
    assert "prose" in prompt
    assert "markdown" in prompt
    assert "extra keys" in prompt
    assert "forbid extra keys" in prompt


def test_decomposition_prompt_contains_extraction_rules() -> None:
    prompt = DECOMPOSITION_SYSTEM_PROMPT.lower()

    for phrase in [
        "atomic facts",
        "neutral wording",
        "preserve chronology",
        "attribute claims",
        "do not infer",
        "empty or missing article body",
    ]:
        assert phrase in prompt


def test_user_prompt_includes_article_fields_and_metadata() -> None:
    prompt = build_decomposition_user_prompt(
        {
            "id": "article-1",
            "title": "Dinner shooting",
            "body": "Body text",
            "source": "Example News",
            "published_at": "2026-04-26T20:35:00Z",
            "url": "https://example.test/article",
        }
    )

    assert "article-1" in prompt
    assert "Dinner shooting" in prompt
    assert "Body text" in prompt
    assert "Example News" in prompt
    assert "2026-04-26T20:35:00Z" in prompt
    assert "https://example.test/article" in prompt
    assert "Do not fetch URLs" in prompt


def test_user_prompt_accepts_alternate_article_field_names() -> None:
    prompt = build_decomposition_user_prompt(
        {
            "article_id": "article-2",
            "headline": "Alternate headline",
            "content": "Alternate body",
        }
    )

    assert "article-2" in prompt
    assert "Alternate headline" in prompt
    assert "Alternate body" in prompt
