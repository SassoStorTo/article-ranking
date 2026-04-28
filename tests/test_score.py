from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.cluster import build_fact_universe, flatten_fact_items
from news_ranker.embed import embed_article_from_clusters
from news_ranker.schemas import (
    Claim,
    Entities,
    Entity,
    StructuredArticle,
    load_structured_article,
)
from news_ranker.score import (
    ScoreVector,
    centrality,
    combine,
    coverage,
    density,
    entity_coverage,
    minmax_normalize,
)

ARTICLE_DIR = Path(__file__).resolve().parents[1] / "articles" / "trump-shooting"
ARTICLE_PATHS = sorted(ARTICLE_DIR.glob("*.json"))


def test_minmax_normalize_scales_values_to_unit_interval() -> None:
    scores = minmax_normalize(np.asarray([2.0, 4.0, 6.0], dtype=np.float32))

    np.testing.assert_allclose(scores.raw, [2.0, 4.0, 6.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.5, 1.0])
    assert scores.defined is True


def test_tied_defined_components_normalize_to_ones() -> None:
    scores = minmax_normalize(np.asarray([3.0, 3.0, 3.0], dtype=np.float32))

    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_undefined_components_normalize_to_zeros() -> None:
    scores = minmax_normalize(
        np.asarray([3.0, 3.0, 3.0], dtype=np.float32), defined=False
    )

    np.testing.assert_allclose(scores.normalized, [0.0, 0.0, 0.0])
    assert scores.defined is False


def test_minmax_rejects_values_that_overflow_float32_conversion() -> None:
    with pytest.raises(ValueError, match="float32"):
        minmax_normalize(np.asarray([1e100, 2e100], dtype=np.float64))


def test_central_article_receives_highest_normalized_centrality() -> None:
    article_embeddings = np.asarray(
        [
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    scores = centrality(article_embeddings)

    assert scores.defined is True
    assert int(np.argmax(scores.normalized)) == 1
    assert scores.normalized[1] == pytest.approx(1.0)
    assert scores.raw[1] > scores.raw[0]
    assert scores.raw[1] > scores.raw[2]


def test_identical_embeddings_tie_at_one() -> None:
    scores = centrality(np.ones((3, 2), dtype=np.float32))

    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_full_fact_coverage_raw_score_equals_one() -> None:
    scores = coverage(np.ones((3, 4), dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [1.0, 1.0, 1.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_consensus_weights_reward_high_support_facts() -> None:
    coverage_matrix = np.asarray(
        [
            [1, 0],
            [1, 0],
            [0, 1],
        ],
        dtype=np.int_,
    )

    scores = coverage(coverage_matrix, mode="consensus")

    assert scores.raw[0] == pytest.approx(2.0 / 3.0)
    assert scores.raw[1] == pytest.approx(2.0 / 3.0)
    assert scores.raw[2] == pytest.approx(1.0 / 3.0)
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 0.0])


def test_rarity_weights_remain_positive_when_all_articles_cover_fact() -> None:
    scores = coverage(np.ones((3, 1), dtype=np.int_), mode="rarity")

    np.testing.assert_allclose(scores.raw, [1.0, 1.0, 1.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_empty_fact_universe_returns_undefined_coverage_zeros() -> None:
    scores = coverage(np.zeros((3, 0), dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [0.0, 0.0, 0.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0, 0.0])
    assert scores.defined is False


def test_density_computes_unique_clusters_per_extracted_entry() -> None:
    articles = [_article("a", 2), _article("b", 4), _article("c", 0)]
    coverage_matrix = np.asarray(
        [
            [1, 1, 0],
            [1, 1, 1],
            [0, 0, 0],
        ],
        dtype=np.int_,
    )

    scores = density(articles, coverage_matrix)

    np.testing.assert_allclose(scores.raw, [1.0, 0.75, 0.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 0.75, 0.0])
    assert scores.defined is True


def test_repeated_coverage_values_do_not_inflate_density() -> None:
    scores = density([_article("a", 2)], np.asarray([[2, 0, 3]], dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [1.0])
    np.testing.assert_allclose(scores.normalized, [1.0])
    assert scores.defined is True


def test_all_empty_extractions_return_undefined_density_zeros() -> None:
    scores = density(
        [_article("a", 0), _article("b", 0)], np.zeros((2, 0), dtype=np.int_)
    )

    np.testing.assert_allclose(scores.raw, [0.0, 0.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0])
    assert scores.defined is False


def test_density_row_count_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="row count"):
        density([_article("a", 1), _article("b", 1)], np.ones((1, 1), dtype=np.int_))


def test_entity_coverage_handles_shared_and_missing_entities() -> None:
    articles = [
        _article("a", 0, people=[" Alice Smith "], organizations=["ACME"]),
        _article("b", 0, people=["alice smith"], locations=["Paris"]),
        _article("c", 0),
    ]

    scores = entity_coverage(articles)

    np.testing.assert_allclose(scores.raw, [0.75, 0.75, 0.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 0.0])
    assert scores.defined is True


def test_no_entity_corpora_return_undefined_entity_coverage_zeros() -> None:
    scores = entity_coverage([_article("a", 0), _article("b", 0)])

    np.testing.assert_allclose(scores.raw, [0.0, 0.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0])
    assert scores.defined is False


def test_grouped_entity_keys_avoid_cross_type_collisions() -> None:
    articles = [
        _article("person", 0, people=["Jordan"]),
        _article("location", 0, locations=["Jordan"]),
        _article("both", 0, people=["Jordan"], locations=["Jordan"]),
    ]

    scores = entity_coverage(articles)

    np.testing.assert_allclose(scores.raw, [0.5, 0.5, 1.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0, 1.0])
    assert scores.defined is True


def test_composite_scoring_uses_normalized_component_values() -> None:
    components = {
        "coverage": ScoreVector(
            raw=np.asarray([100.0, 200.0], dtype=np.float32),
            normalized=np.asarray([0.0, 1.0], dtype=np.float32),
            defined=True,
        ),
        "density": ScoreVector(
            raw=np.asarray([0.1, 0.2], dtype=np.float32),
            normalized=np.asarray([1.0, 0.0], dtype=np.float32),
            defined=True,
        ),
    }

    scores = combine(components, {"coverage": 0.75, "density": 0.25})

    np.testing.assert_allclose(scores, [0.25, 0.75])


def test_undefined_weighted_components_are_renormalized_by_default() -> None:
    components = {
        "coverage": ScoreVector(
            raw=np.asarray([0.0, 1.0], dtype=np.float32),
            normalized=np.asarray([0.0, 1.0], dtype=np.float32),
            defined=True,
        ),
        "entities": ScoreVector(
            raw=np.asarray([0.0, 0.0], dtype=np.float32),
            normalized=np.asarray([0.0, 0.0], dtype=np.float32),
            defined=False,
        ),
    }

    scores = combine(components, {"coverage": 0.5, "entities": 0.5})

    np.testing.assert_allclose(scores, [0.0, 1.0])


def test_invalid_combine_weights_raise() -> None:
    components = {"coverage": _score_vector([0.0, 1.0])}

    with pytest.raises(ValueError, match="nonnegative"):
        combine(components, {"coverage": -1.0})


def test_mismatched_component_lengths_raise() -> None:
    components = {
        "coverage": _score_vector([0.0, 1.0]),
        "density": _score_vector([1.0]),
    }

    with pytest.raises(ValueError, match="lengths"):
        combine(components, {"coverage": 0.5, "density": 0.5})


@pytest.mark.parametrize(
    ("article_embeddings", "error_type", "match"),
    [
        (np.ones((2,), dtype=np.float32), ValueError, "2-D"),
        (np.array([[np.nan, 1.0]], dtype=np.float32), ValueError, "finite"),
        (np.array([[1e100, 0.0]], dtype=np.float64), ValueError, "float32"),
        (np.array([[object()]], dtype=object), TypeError, "numeric"),
    ],
)
def test_invalid_centrality_embeddings_raise(
    article_embeddings: NDArray[Any], error_type: type[Exception], match: str
) -> None:
    with pytest.raises(error_type, match=match):
        centrality(article_embeddings)


def test_coverage_rejects_values_that_overflow_float32_conversion() -> None:
    with pytest.raises(ValueError, match="float32"):
        coverage(np.asarray([[1e100]], dtype=np.float64))


def test_fixture_clustering_to_scoring_smoke_path() -> None:
    articles = _fixture_articles()
    raw_facts = flatten_fact_items(articles)
    fact_embeddings = np.eye(len(raw_facts), dtype=np.float32)

    universe = build_fact_universe(articles, fact_embeddings)
    article_vectors = np.asarray(
        [
            embed_article_from_clusters(
                article.article_id or "",
                universe.article_ids,
                universe.coverage_matrix,
                universe.cluster_vectors,
            )
            for article in articles
        ],
        dtype=np.float32,
    )

    centrality_scores = centrality(article_vectors)
    coverage_scores = coverage(universe.coverage_matrix)
    density_scores = density(articles, universe.coverage_matrix)
    entity_scores = entity_coverage(articles)
    combined_scores = combine(
        {
            "centrality": centrality_scores,
            "coverage": coverage_scores,
            "density": density_scores,
            "entities": entity_scores,
        },
        {
            "centrality": 0.25,
            "coverage": 0.25,
            "density": 0.25,
            "entities": 0.25,
        },
    )

    assert len(articles) == 5
    assert universe.coverage_matrix.shape[0] == 5
    assert article_vectors.shape == (5, universe.cluster_vectors.shape[1])
    for scores in (centrality_scores, coverage_scores, density_scores, entity_scores):
        assert scores.raw.shape == (5,)
        assert scores.normalized.shape == (5,)
    assert combined_scores.shape == (5,)
    assert np.isfinite(combined_scores).all()


def _fixture_articles() -> list[StructuredArticle]:
    return [load_structured_article(path) for path in ARTICLE_PATHS]


def _article(
    article_id: str,
    entry_count: int,
    *,
    people: list[str] | None = None,
    organizations: list[str] | None = None,
    locations: list[str] | None = None,
) -> StructuredArticle:
    return StructuredArticle(
        article_id=article_id,
        headline_neutral="Neutral headline",
        topic="test",
        entities=Entities(
            people=_entities(people),
            organizations=_entities(organizations),
            locations=_entities(locations),
        ),
        events=[],
        claims=[
            Claim(
                id=f"c{index}",
                statement=f"claim {index}",
                type="fact",
                attributed_to="fixture",
            )
            for index in range(entry_count)
        ],
        context=[],
    )


def _entities(names: list[str] | None) -> list[Entity]:
    return [Entity(name=name, role="fixture") for name in names or []]


def _score_vector(values: list[float]) -> ScoreVector:
    array = np.asarray(values, dtype=np.float32)
    return ScoreVector(raw=array, normalized=array, defined=True)
