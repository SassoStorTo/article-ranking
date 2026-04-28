from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.cluster import build_fact_universe, flatten_fact_items
from news_ranker.schemas import StructuredArticle, load_structured_article

ARTICLE_DIR = Path(__file__).resolve().parents[1] / "articles" / "trump-shooting"
ARTICLE_PATHS = sorted(ARTICLE_DIR.glob("*.json"))


def _fixture_articles() -> list[StructuredArticle]:
    return [load_structured_article(path) for path in ARTICLE_PATHS]


def _fact_embeddings(row_count: int) -> NDArray[np.float32]:
    return np.ones((row_count, 2), dtype=np.float32)


def test_fixture_backed_articles_flatten_in_article_order() -> None:
    articles = _fixture_articles()
    expected_facts = [
        (article.article_id, fact_id, text)
        for article in articles
        for fact_id, text in article.fact_items
    ]

    raw_facts = flatten_fact_items(articles)
    universe = build_fact_universe(articles, _fact_embeddings(len(raw_facts)))

    assert [(fact.article_id, fact.fact_id, fact.text) for fact in raw_facts] == (
        expected_facts
    )
    assert universe.article_ids == tuple(article.article_id for article in articles)
    assert universe.raw_fact_article_ids == tuple(
        article_id for article_id, _, _ in expected_facts
    )
    assert universe.raw_fact_ids == tuple(fact_id for _, fact_id, _ in expected_facts)
    assert universe.raw_fact_texts == tuple(text for _, _, text in expected_facts)
    assert universe.coverage_matrix.shape == (len(articles), len(raw_facts))


def test_missing_article_id_fails() -> None:
    article = StructuredArticle.model_validate_json(
        (ARTICLE_DIR / "bbc.json").read_text(encoding="utf-8")
    )

    with pytest.raises(ValueError, match="article_id"):
        build_fact_universe([article], _fact_embeddings(len(article.fact_items)))


def test_duplicate_article_ids_fail() -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")

    with pytest.raises(ValueError, match="unique"):
        build_fact_universe(
            [article, article], _fact_embeddings(len(article.fact_items) * 2)
        )


def test_embedding_row_count_mismatch_fails() -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")

    with pytest.raises(ValueError, match="row count"):
        build_fact_universe([article], _fact_embeddings(len(article.fact_items) + 1))


@pytest.mark.parametrize(
    ("embeddings", "error_type", "match"),
    [
        (np.ones((1,), dtype=np.float32), ValueError, "2-D"),
        (np.array([[np.nan, 1.0]], dtype=np.float32), ValueError, "finite"),
        (np.array([[0.0, 0.0]], dtype=np.float32), ValueError, "nonzero"),
        (np.array([[object()]], dtype=object), TypeError, "numeric"),
    ],
)
def test_invalid_embeddings_fail(
    embeddings: NDArray[Any], error_type: type[Exception], match: str
) -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")
    one_fact_article = article.model_copy(
        update={"events": article.events[:1], "claims": []}
    )

    with pytest.raises(error_type, match=match):
        build_fact_universe([one_fact_article], embeddings)


def test_invalid_similarity_threshold_fails() -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")

    with pytest.raises(ValueError, match="similarity_threshold"):
        build_fact_universe(
            [article],
            _fact_embeddings(len(article.fact_items)),
            similarity_threshold=1.1,
        )


def test_invalid_linkage_fails() -> None:
    article = load_structured_article(ARTICLE_DIR / "bbc.json")

    with pytest.raises(ValueError, match="linkage"):
        build_fact_universe(
            [article],
            _fact_embeddings(len(article.fact_items)),
            linkage="complete",  # type: ignore[arg-type]
        )


def test_empty_facts_return_empty_coverage_with_known_article_ids() -> None:
    base_article = load_structured_article(ARTICLE_DIR / "bbc.json")
    articles = [
        base_article.model_copy(
            update={"article_id": "article-a", "events": [], "claims": []}
        ),
        base_article.model_copy(
            update={"article_id": "article-b", "events": [], "claims": []}
        ),
    ]

    universe = build_fact_universe(articles, np.empty((0, 3), dtype=np.float32))

    assert universe.article_ids == ("article-a", "article-b")
    assert universe.raw_fact_article_ids == ()
    assert universe.raw_fact_ids == ()
    assert universe.raw_fact_texts == ()
    assert universe.canonical_fact_texts == ()
    assert universe.cluster_vectors.shape == (0, 3)
    assert universe.cluster_vectors.dtype == np.float32
    assert universe.cluster_assignments.shape == (0,)
    assert universe.cluster_members == ()
    assert universe.coverage_matrix.shape == (2, 0)
