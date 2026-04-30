import warnings
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.cluster import FactUniverse, flatten_fact_items
from news_ranker.config import RankerConfig
from news_ranker.pipeline import NewsRanker
from news_ranker.results import RankDiagnostics, RankingEntry, RankResult
from news_ranker.schemas import (
    Claim,
    Entities,
    StructuredArticle,
    load_structured_article,
)

ARTICLE_DIR = Path(__file__).resolve().parents[1] / "articles" / "trump-shooting"
ARTICLE_PATHS = sorted(ARTICLE_DIR.glob("*.json"))

EXPECTED_COMPONENT_KEYS = {"centrality", "coverage", "density", "entity_coverage"}


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        self.calls += 1
        self.texts = list(texts)
        return np.ones((len(texts), 2), dtype=np.float32)


class FakeDecomposer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, article: dict[str, object]) -> StructuredArticle:
        self.calls.append(article)
        return _article(str(article["id"]), 1)


class StubRanker(NewsRanker):
    def __init__(
        self,
        *,
        config: RankerConfig,
        scores: NDArray[np.float32],
        embeddings: NDArray[np.float32],
    ) -> None:
        super().__init__(FakeEmbedder(), config=config)
        self._scores = scores
        self._embeddings = embeddings

    def rank(self, articles: object, profile: str = "representative") -> RankResult:
        del articles
        return _rank_result(profile, self._scores, self._embeddings)


def test_pipeline_result_imports_resolve_to_results_module() -> None:
    from news_ranker.pipeline import RankDiagnostics as LegacyRankDiagnostics
    from news_ranker.pipeline import RankingEntry as LegacyRankingEntry
    from news_ranker.pipeline import RankResult as LegacyRankResult

    assert RankingEntry.__module__ == "news_ranker.results"
    assert RankDiagnostics.__module__ == "news_ranker.results"
    assert RankResult.__module__ == "news_ranker.results"
    assert LegacyRankingEntry is RankingEntry
    assert LegacyRankDiagnostics is RankDiagnostics
    assert LegacyRankResult is RankResult


def test_default_config_profiles_have_expected_component_keys() -> None:
    config = RankerConfig()

    assert set(config.profiles) == {"representative", "comprehensive", "concise"}
    for weights in config.profiles.values():
        assert set(weights) == EXPECTED_COMPONENT_KEYS
        assert sum(weights.values()) == pytest.approx(1.0)


def test_empty_profile_name_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="profile name"):
        RankerConfig(profiles={"": _profile_weights()})


def test_negative_profile_weight_fails_config_validation() -> None:
    weights = _profile_weights(coverage=-0.1, density=0.6)

    with pytest.raises(ValueError, match="nonnegative"):
        RankerConfig(profiles={"broken": weights})


def test_profile_weights_must_sum_to_one() -> None:
    weights = _profile_weights(coverage=0.4)

    with pytest.raises(ValueError, match="sum to 1.0"):
        RankerConfig(profiles={"broken": weights})


def test_profile_weights_must_include_required_component_keys() -> None:
    weights = _profile_weights()
    del weights["entity_coverage"]

    with pytest.raises(ValueError, match="component keys"):
        RankerConfig(profiles={"broken": weights})


def test_invalid_linkage_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="linkage"):
        RankerConfig(linkage="complete")


def test_invalid_coverage_weighting_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="coverage_weighting"):
        RankerConfig(coverage_weighting="tfidf")


def test_ranker_constructor_requires_explicit_embedder() -> None:
    with pytest.raises(TypeError, match="explicit FactEmbedder"):
        NewsRanker()


def test_directory_input_loads_sorted_fixture_articles() -> None:
    ranker = NewsRanker(FakeEmbedder())

    articles = ranker._load_structured_articles(ARTICLE_DIR)

    assert len(articles) == 5
    assert [article.article_id for article in articles] == [
        "trump-shooting/bbc",
        "trump-shooting/doj",
        "trump-shooting/new-york-post",
        "trump-shooting/the-guardian",
        "trump-shooting/wikipedia",
    ]


def test_single_file_input_loads_one_article() -> None:
    ranker = NewsRanker(FakeEmbedder())

    articles = ranker._load_structured_articles(ARTICLE_DIR / "bbc.json")

    assert [article.article_id for article in articles] == ["trump-shooting/bbc"]


def test_explicit_path_sequence_preserves_order() -> None:
    ranker = NewsRanker(FakeEmbedder())
    reversed_paths = list(reversed(ARTICLE_PATHS))

    articles = ranker._load_structured_articles(reversed_paths)

    assert [article.article_id for article in articles] == [
        load_structured_article(path).article_id for path in reversed_paths
    ]


def test_loaded_structured_articles_pass_through() -> None:
    ranker = NewsRanker(FakeEmbedder())
    loaded = [load_structured_article(path) for path in ARTICLE_PATHS[:2]]

    articles = ranker._load_structured_articles(loaded)

    assert articles == loaded
    assert all(isinstance(article, StructuredArticle) for article in articles)


def test_empty_directory_input_fails(tmp_path: Path) -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(ValueError, match="no JSON files"):
        ranker._load_structured_articles(tmp_path)


def test_empty_sequence_input_fails() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(ValueError, match="must not be empty"):
        ranker._load_structured_articles([])


def test_raw_article_dict_input_reports_decomposition_not_implemented() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(NotImplementedError, match="decomposition.*not implemented"):
        ranker._load_structured_articles([{"id": "raw-1", "body": "text"}])


def test_raw_article_dicts_decompose_through_injected_decomposer() -> None:
    decomposer = FakeDecomposer()
    ranker = NewsRanker(FakeEmbedder(), decomposer=decomposer)
    raw_articles = [
        {"id": "raw-1", "title": "one", "body": "body one"},
        {"id": "raw-2", "title": "two", "body": "body two"},
    ]

    articles = ranker._load_structured_articles(raw_articles)

    assert [article.article_id for article in articles] == ["raw-1", "raw-2"]
    assert decomposer.calls == raw_articles


def test_mixed_raw_path_and_structured_inputs_preserve_order() -> None:
    decomposer = FakeDecomposer()
    ranker = NewsRanker(FakeEmbedder(), decomposer=decomposer)
    structured = _article("structured-1", 1)
    raw = {"id": "raw-1", "title": "raw", "body": "raw body"}
    path = ARTICLE_DIR / "bbc.json"

    articles = ranker._load_structured_articles([raw, path, structured])

    assert [article.article_id for article in articles] == [
        "raw-1",
        "trump-shooting/bbc",
        "structured-1",
    ]
    assert decomposer.calls == [raw]


def test_rank_uses_decomposed_article_ids() -> None:
    ranker = NewsRanker(FakeEmbedder(), decomposer=FakeDecomposer())

    result = ranker.rank([
        {"id": "raw-1", "title": "one", "body": "body one"},
        {"id": "raw-2", "title": "two", "body": "body two"},
    ])

    assert [entry.article_id for entry in result.entries] == ["raw-1", "raw-2"]


def test_decomposer_exceptions_propagate() -> None:
    def broken_decomposer(article: dict[str, object]) -> StructuredArticle:
        del article
        raise RuntimeError("decomposer failed")

    ranker = NewsRanker(FakeEmbedder(), decomposer=broken_decomposer)

    with pytest.raises(RuntimeError, match="decomposer failed"):
        ranker._load_structured_articles([
            {"id": "raw-1", "title": "one", "body": "body one"}
        ])


def test_rank_folder_returns_ranked_fixture_articles() -> None:
    embedder = FakeEmbedder()
    ranker = NewsRanker(embedder)
    loaded_articles = [load_structured_article(path) for path in ARTICLE_PATHS]

    result = ranker.rank(ARTICLE_DIR)

    assert result.profile == "representative"
    assert len(result.entries) == 5
    assert [entry.rank for entry in result.entries] == [1, 2, 3, 4, 5]
    assert {entry.article_id for entry in result.entries} == {
        article.article_id for article in loaded_articles
    }
    assert all(np.isfinite(entry.score) for entry in result.entries)
    for entry in result.entries:
        assert set(entry.components) == EXPECTED_COMPONENT_KEYS
        assert all(np.isfinite(score) for score in entry.components.values())
    assert embedder.texts == [fact.text for fact in flatten_fact_items(loaded_articles)]
    assert result.diagnostics.fact_universe.article_ids == tuple(
        article.article_id for article in loaded_articles
    )
    assert set(result.diagnostics.components) == EXPECTED_COMPONENT_KEYS
    assert result.diagnostics.article_embeddings.shape[0] == len(loaded_articles)


def test_rank_unknown_profile_fails() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(ValueError, match="unknown ranking profile"):
        ranker.rank(ARTICLE_DIR, profile="missing")


def test_rank_all_empty_articles_skips_embedder_and_returns_finite_scores() -> None:
    embedder = FakeEmbedder()
    ranker = NewsRanker(embedder)
    articles = [_article("empty-1", 0), _article("empty-2", 0)]

    result = ranker.rank(articles)

    assert embedder.calls == 0
    assert [entry.article_id for entry in result.entries] == ["empty-1", "empty-2"]
    assert all(np.isfinite(entry.score) for entry in result.entries)
    assert result.diagnostics.fact_universe.coverage_matrix.shape == (2, 0)
    assert result.diagnostics.fact_universe.coverage_matrix.sum() == 0
    assert result.diagnostics.fact_universe.cluster_vectors.shape == (0, 0)
    assert not result.diagnostics.components["centrality"].defined
    assert not result.diagnostics.components["coverage"].defined
    assert not result.diagnostics.components["density"].defined


def test_rank_mixed_empty_articles_marks_centrality_undefined() -> None:
    ranker = NewsRanker(FakeEmbedder())
    articles = [_article("empty", 0), _article("covered", 1)]

    result = ranker.rank(articles)

    assert all(np.isfinite(entry.score) for entry in result.entries)
    assert result.diagnostics.fact_universe.coverage_matrix.tolist() == [[0], [1]]
    assert result.diagnostics.components["centrality"].defined is False


def test_rank_tie_scores_keep_input_order() -> None:
    config = RankerConfig(
        profiles={
            "coverage_only": _profile_weights(centrality=0.0, coverage=1.0, density=0.0)
        }
    )
    ranker = NewsRanker(FakeEmbedder(), config=config)
    articles = [load_structured_article(path) for path in reversed(ARTICLE_PATHS[:2])]

    result = ranker.rank(articles, profile="coverage_only")

    assert [entry.article_id for entry in result.entries] == [
        article.article_id for article in articles
    ]
    assert [entry.score for entry in result.entries] == [pytest.approx(1.0)] * 2


def test_select_returns_first_m_ranked_entries() -> None:
    ranker = NewsRanker(FakeEmbedder())

    ranking = ranker.rank(ARTICLE_DIR)
    selection = ranker.select(ARTICLE_DIR, m=2)

    assert selection.profile == "representative"
    assert selection.m == 2
    assert [entry.article_id for entry in selection.selected] == [
        entry.article_id for entry in ranking.entries[:2]
    ]
    assert selection.selected == selection.ranking.entries[:2]


def test_top_score_selection_returns_first_m_ranked_entries() -> None:
    ranker = NewsRanker(FakeEmbedder(), config=RankerConfig(selection_mode="top_score"))

    selection = ranker.select(ARTICLE_DIR, m=2)
    expected = selection.ranking.entries[:2]

    assert selection.selected == expected
    assert [entry.rank for entry in selection.selected] == [1, 2]


def test_mmr_selection_emits_no_warning_and_keeps_highest_ranked_first() -> None:
    ranker = NewsRanker(FakeEmbedder(), config=RankerConfig(selection_mode="mmr"))

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        selection = ranker.select(ARTICLE_DIR, m=2)

    assert selection.selected[0] == selection.ranking.entries[0]


def test_mmr_selection_can_differ_from_top_score_for_duplicate_embeddings() -> None:
    ranker = StubRanker(
        config=RankerConfig(selection_mode="mmr", selection_lambda=0.5),
        scores=np.asarray([1.0, 0.95, 0.9], dtype=np.float32),
        embeddings=np.asarray([[2.0, 0.0], [3.0, 0.0], [0.0, 4.0]], dtype=np.float32),
    )

    selection = ranker.select([], m=2)

    assert [entry.article_id for entry in selection.selected] == [
        "article-0",
        "article-2",
    ]
    assert selection.selected != selection.ranking.entries[:2]


def test_mmr_selection_lambda_one_matches_top_score_selection() -> None:
    ranker = StubRanker(
        config=RankerConfig(selection_mode="mmr", selection_lambda=1.0),
        scores=np.asarray([1.0, 0.95, 0.9], dtype=np.float32),
        embeddings=np.asarray([[2.0, 0.0], [3.0, 0.0], [0.0, 4.0]], dtype=np.float32),
    )

    selection = ranker.select([], m=2)

    assert selection.selected == selection.ranking.entries[:2]


def test_mmr_selection_empty_fact_articles_falls_back_to_score_order() -> None:
    ranker = NewsRanker(FakeEmbedder(), config=RankerConfig(selection_mode="mmr"))
    articles = [_article("empty-1", 0), _article("empty-2", 0)]

    selection = ranker.select(articles, m=2)

    assert all(np.isfinite(entry.score) for entry in selection.selected)
    assert selection.selected == selection.ranking.entries[:2]


def test_select_uses_configured_top_m_when_m_omitted() -> None:
    ranker = NewsRanker(FakeEmbedder(), config=RankerConfig(top_m=2))

    ranking = ranker.rank(ARTICLE_DIR)
    selection = ranker.select(ARTICLE_DIR)

    assert selection.m == 2
    assert selection.selected == ranking.entries[:2]


def test_select_explicit_m_overrides_configured_top_m() -> None:
    ranker = NewsRanker(FakeEmbedder(), config=RankerConfig(top_m=3))

    selection = ranker.select(ARTICLE_DIR, m=2)

    assert selection.m == 2
    assert selection.selected == selection.ranking.entries[:2]


def test_select_omitted_m_without_config_fails() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(TypeError, match="m must be an integer"):
        ranker.select(ARTICLE_DIR)


def test_non_integer_configured_top_m_fails_config_validation() -> None:
    with pytest.raises(TypeError, match="top_m must be an integer"):
        RankerConfig(top_m=1.5)  # type: ignore[arg-type]


def test_configured_top_m_greater_than_article_count_fails_at_call_time() -> None:
    ranker = NewsRanker(
        FakeEmbedder(), config=RankerConfig(top_m=len(ARTICLE_PATHS) + 1)
    )

    with pytest.raises(ValueError, match="1 <= m <= article_count"):
        ranker.select(ARTICLE_DIR)


def test_select_invalid_m_values_fail() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(TypeError, match="m must be an integer"):
        ranker.select(ARTICLE_DIR, m=1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="m must be an integer"):
        ranker.select(ARTICLE_DIR, m=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="1 <= m <= article_count"):
        ranker.select(ARTICLE_DIR, m=0)
    with pytest.raises(ValueError, match="1 <= m <= article_count"):
        ranker.select(ARTICLE_DIR, m=len(ARTICLE_PATHS) + 1)


def test_selected_entries_retain_rank_score_and_component_data() -> None:
    ranker = NewsRanker(FakeEmbedder())

    selection = ranker.select(ARTICLE_DIR, m=2)

    for entry in selection.selected:
        assert isinstance(entry.rank, int)
        assert np.isfinite(entry.score)
        assert set(entry.components) == EXPECTED_COMPONENT_KEYS
        assert all(np.isfinite(score) for score in entry.components.values())


def test_compare_profiles_defaults_to_configured_profiles() -> None:
    ranker = NewsRanker(FakeEmbedder())

    comparison = ranker.compare_profiles(ARTICLE_DIR)

    assert set(comparison.rankings) == {"representative", "comprehensive", "concise"}
    assert all(
        ranking.profile == profile for profile, ranking in comparison.rankings.items()
    )


def test_compare_profiles_accepts_explicit_profile_subset() -> None:
    ranker = NewsRanker(FakeEmbedder())

    comparison = ranker.compare_profiles(
        ARTICLE_DIR, profiles=["concise", "representative"]
    )

    assert list(comparison.rankings) == ["concise", "representative"]


def test_compare_profiles_unknown_profile_fails() -> None:
    ranker = NewsRanker(FakeEmbedder())

    with pytest.raises(ValueError, match="unknown ranking profile"):
        ranker.compare_profiles(ARTICLE_DIR, profiles=["missing"])


def test_compare_profiles_rankings_use_same_article_ids() -> None:
    ranker = NewsRanker(FakeEmbedder())

    comparison = ranker.compare_profiles(ARTICLE_DIR)
    ranked_id_sets = {
        tuple(entry.article_id for entry in ranking.entries)
        for ranking in comparison.rankings.values()
    }

    assert len(ranked_id_sets) == 1


def _rank_result(
    profile: str,
    scores: NDArray[np.float32],
    embeddings: NDArray[np.float32],
) -> RankResult:
    article_ids = tuple(f"article-{index}" for index in range(scores.shape[0]))
    ranked_indices = sorted(
        range(scores.shape[0]), key=lambda index: (-float(scores[index]), index)
    )
    entries = tuple(
        RankingEntry(
            article_id=article_ids[index],
            rank=rank,
            score=float(scores[index]),
            components={},
        )
        for rank, index in enumerate(ranked_indices, start=1)
    )
    fact_universe = FactUniverse(
        article_ids=article_ids,
        raw_fact_article_ids=(),
        raw_fact_ids=(),
        raw_fact_texts=(),
        canonical_fact_texts=(),
        cluster_vectors=np.empty((0, embeddings.shape[1]), dtype=np.float32),
        cluster_assignments=np.empty((0,), dtype=np.int_),
        cluster_members=(),
        coverage_matrix=np.zeros((scores.shape[0], 0), dtype=np.int_),
    )
    return RankResult(
        profile=profile,
        entries=entries,
        diagnostics=RankDiagnostics(
            fact_universe=fact_universe,
            components={},
            article_embeddings=embeddings,
        ),
    )


def _article(article_id: str, fact_count: int) -> StructuredArticle:
    return StructuredArticle(
        article_id=article_id,
        headline_neutral="Neutral headline",
        topic="test",
        entities=Entities(people=[], organizations=[], locations=[]),
        events=[],
        claims=[
            Claim(
                id=f"c{index}",
                statement=f"claim {index}",
                type="fact",
                attributed_to="fixture",
            )
            for index in range(fact_count)
        ],
        context=[],
    )


def _profile_weights(
    *,
    centrality: float = 0.4,
    coverage: float = 0.5,
    density: float = 0.1,
    entity_coverage: float = 0.0,
) -> dict[str, float]:
    return {
        "centrality": centrality,
        "coverage": coverage,
        "density": density,
        "entity_coverage": entity_coverage,
    }
