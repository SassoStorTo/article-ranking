"""Fixture-backed public ranking pipeline."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

from news_ranker.cluster import FactUniverse, build_fact_universe, flatten_fact_items
from news_ranker.config import RankerConfig
from news_ranker.embed import FactEmbedder, embed_article_from_clusters, embed_facts
from news_ranker.schemas import StructuredArticle, load_structured_article
from news_ranker.score import (
    ScoreVector,
    centrality,
    combine,
    coverage,
    density,
    entity_coverage,
)

ArticleInput: TypeAlias = (
    str | Path | Sequence[str | Path] | Sequence[StructuredArticle]
)


@dataclass(frozen=True)
class RankingEntry:
    """Ranked article score and normalized component values."""

    article_id: str
    rank: int
    score: float
    components: Mapping[str, float]


@dataclass(frozen=True)
class RankDiagnostics:
    """Intermediate ranking artifacts for inspection."""

    fact_universe: FactUniverse
    components: Mapping[str, ScoreVector]
    article_embeddings: NDArray[np.float32]


@dataclass(frozen=True)
class RankResult:
    """Ranked article result for one scoring profile."""

    profile: str
    entries: tuple[RankingEntry, ...]
    diagnostics: RankDiagnostics


class NewsRanker:
    """Public orchestrator for fixture-backed article ranking."""

    def __init__(
        self, embedder: FactEmbedder | None = None, config: RankerConfig | None = None
    ) -> None:
        """Create ranker with explicit fact embedder dependency."""

        if embedder is None:
            msg = (
                "NewsRanker requires an explicit FactEmbedder; "
                "no default embedder is used"
            )
            raise TypeError(msg)
        self._embedder = embedder
        self._config = config or RankerConfig()

    def rank(
        self, articles: ArticleInput, profile: str = "representative"
    ) -> RankResult:
        """Rank structured articles with configured profile weights."""

        if profile not in self._config.profiles:
            msg = f"unknown ranking profile: {profile}"
            raise ValueError(msg)

        loaded_articles = self._load_structured_articles(articles)
        raw_facts = flatten_fact_items(loaded_articles)
        fact_texts = [fact.text for fact in raw_facts]
        if fact_texts:
            fact_embeddings = embed_facts(fact_texts, self._embedder)
        else:
            fact_embeddings = np.empty((0, 0), dtype=np.float32)
        fact_universe = build_fact_universe(
            loaded_articles,
            fact_embeddings,
            similarity_threshold=self._config.similarity_threshold,
            linkage=self._config.linkage,
        )
        article_embeddings = self._embed_articles(fact_universe)
        components = self._score_components(
            loaded_articles, fact_universe, article_embeddings
        )
        scores = combine(components, self._config.profiles[profile])
        entries = self._rank_entries(fact_universe.article_ids, scores, components)

        return RankResult(
            profile=profile,
            entries=entries,
            diagnostics=RankDiagnostics(
                fact_universe=fact_universe,
                components=components,
                article_embeddings=article_embeddings,
            ),
        )

    def _load_structured_articles(
        self, articles: ArticleInput
    ) -> list[StructuredArticle]:
        """Normalize supported structured inputs to loaded articles."""

        if isinstance(articles, str | Path):
            return self._load_from_path(Path(articles))

        if not isinstance(articles, Sequence):
            msg = (
                "articles must be a path or sequence of paths/StructuredArticle objects"
            )
            raise TypeError(msg)
        if not articles:
            msg = "articles input must not be empty"
            raise ValueError(msg)

        loaded: list[StructuredArticle] = []
        for item in articles:
            if isinstance(item, StructuredArticle):
                loaded.append(item)
            elif isinstance(item, str | Path):
                loaded.extend(self._load_from_path(Path(item)))
            elif isinstance(item, dict):
                msg = (
                    "raw article dictionaries require decomposition, "
                    "which is not implemented yet"
                )
                raise NotImplementedError(msg)
            else:
                msg = (
                    "articles sequence items must be paths or "
                    f"StructuredArticle objects; got {type(item).__name__}"
                )
                raise TypeError(msg)

        if not loaded:
            msg = "articles input must not be empty"
            raise ValueError(msg)
        return loaded

    def _load_from_path(self, path: Path) -> list[StructuredArticle]:
        if path.is_dir():
            article_paths = sorted(path.glob("*.json"))
            if not article_paths:
                msg = f"article directory contains no JSON files: {path}"
                raise ValueError(msg)
            return [
                load_structured_article(article_path) for article_path in article_paths
            ]

        if path.is_file():
            return [load_structured_article(path)]

        msg = f"article path does not exist: {path}"
        raise FileNotFoundError(msg)

    def _embed_articles(self, fact_universe: FactUniverse) -> NDArray[np.float32]:
        article_count = len(fact_universe.article_ids)
        cluster_dim = fact_universe.cluster_vectors.shape[1]
        if fact_universe.coverage_matrix.shape[1] == 0:
            return np.zeros((article_count, cluster_dim), dtype=np.float32)

        covered_counts = fact_universe.coverage_matrix.sum(axis=1)
        article_embeddings = np.zeros((article_count, cluster_dim), dtype=np.float32)
        for index, article_id in enumerate(fact_universe.article_ids):
            if covered_counts[index] == 0:
                continue
            article_embeddings[index] = embed_article_from_clusters(
                article_id,
                fact_universe.article_ids,
                fact_universe.coverage_matrix,
                fact_universe.cluster_vectors,
            )
        return article_embeddings

    def _score_components(
        self,
        articles: Sequence[StructuredArticle],
        fact_universe: FactUniverse,
        article_embeddings: NDArray[np.float32],
    ) -> dict[str, ScoreVector]:
        if (
            fact_universe.coverage_matrix.shape[1] == 0
            or (fact_universe.coverage_matrix.sum(axis=1) == 0).any()
        ):
            centrality_scores = ScoreVector(
                raw=np.zeros((len(articles),), dtype=np.float32),
                normalized=np.zeros((len(articles),), dtype=np.float32),
                defined=False,
            )
        else:
            centrality_scores = centrality(article_embeddings)

        return {
            "centrality": centrality_scores,
            "coverage": coverage(
                fact_universe.coverage_matrix,
                mode=self._config.coverage_weighting,
            ),
            "density": density(articles, fact_universe.coverage_matrix),
            "entity_coverage": entity_coverage(articles),
        }

    def _rank_entries(
        self,
        article_ids: Sequence[str],
        scores: NDArray[np.float32],
        components: Mapping[str, ScoreVector],
    ) -> tuple[RankingEntry, ...]:
        ranked_indices = sorted(
            range(len(article_ids)), key=lambda index: (-float(scores[index]), index)
        )
        return tuple(
            RankingEntry(
                article_id=article_ids[index],
                rank=rank,
                score=float(scores[index]),
                components={
                    name: float(component.normalized[index])
                    for name, component in components.items()
                },
            )
            for rank, index in enumerate(ranked_indices, start=1)
        )
