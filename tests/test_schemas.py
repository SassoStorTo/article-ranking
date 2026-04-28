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


def test_unknown_top_level_fields_are_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)


def test_brief_style_canonical_name_entities_are_rejected() -> None:
    data = json.loads((ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8"))
    data["entities"]["people"] = [
        {"canonical_name": "Donald Trump", "role": "US President"}
    ]

    with pytest.raises(ValidationError):
        StructuredArticle.model_validate(data)
