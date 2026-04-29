import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from news_ranker.schemas import (
    StructuredArticle,
    derive_article_id,
    load_structured_article,
)

ARTICLE_DIR = Path(__file__).resolve().parents[1] / "articles" / "trump-shooting"
ARTICLE_PATHS = sorted(ARTICLE_DIR.glob("*.json"))


def test_all_trump_shooting_fixtures_validate_as_structured_articles() -> None:
    assert len(ARTICLE_PATHS) == 5

    for article_path in ARTICLE_PATHS:
        article = StructuredArticle.model_validate_json(
            article_path.read_text(encoding="utf-8")
        )

        assert article.article_id is None
        assert article.headline_neutral
        assert article.entities.people
        assert article.events
        assert article.claims


def test_loader_derives_missing_runtime_article_ids_from_paths() -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")

    assert article.article_id == "trump-shooting/bbc"
    assert derive_article_id("trump-shooting/bbc") == "trump-shooting/bbc"


def test_fixture_fact_texts_keep_event_then_claim_order_and_ids() -> None:
    for article_path in ARTICLE_PATHS:
        article = load_structured_article(article_path)

        assert article.article_id == derive_article_id(article_path)
        assert len(article.fact_texts) == len(article.events) + len(article.claims)
        assert [fact_id for fact_id, _ in article.fact_items] == [
            event.id for event in article.events
        ] + [claim.id for claim in article.claims]
        assert article.fact_texts[: len(article.events)] == [
            event.fact_text for event in article.events
        ]
        assert article.fact_texts[len(article.events) :] == [
            claim.statement for claim in article.claims
        ]
        assert all(text for text in article.fact_texts)


def test_loader_preserves_article_id_supplied_in_json(tmp_path: Path) -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["article_id"] = "trump-shooting/json-id"
    article_path = tmp_path / "article.json"
    article_path.write_text(json.dumps(data), encoding="utf-8")

    article = load_structured_article(article_path)

    assert article.article_id == "trump-shooting/json-id"
    assert len(article.fact_texts) == len(article.events) + len(article.claims)


def test_unknown_top_level_fields_are_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)


def test_unknown_nested_fields_are_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["entities"]["people"][0]["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)


def test_brief_style_canonical_name_entities_are_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["entities"]["people"] = [
        {"canonical_name": "Donald Trump", "role": "US President"}
    ]

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)


def test_invalid_claim_type_is_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["claims"][0]["type"] = "rumor"

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)


def test_prompt_compatible_null_scalars_validate() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["entities"]["people"][0]["role"] = None
    data["events"][0]["when"] = None
    data["claims"][0]["attributed_to"] = None

    article = StructuredArticle.model_validate(data)

    assert article.entities.people[0].role is None
    assert article.events[0].when is None
    assert article.claims[0].attributed_to is None
    assert "when: None" not in article.events[0].fact_text
