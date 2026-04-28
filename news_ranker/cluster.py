"""Fact clustering records and validation helpers."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from news_ranker.schemas import StructuredArticle

Linkage = Literal["average", "single"]


@dataclass(frozen=True)
class RawFact:
    """Flattened fact with owning article metadata."""

    article_id: str
    fact_id: str
    text: str


@dataclass(frozen=True)
class FactUniverse:
    """Cluster-ready fact universe for one event corpus."""

    article_ids: tuple[str, ...]
    raw_fact_article_ids: tuple[str, ...]
    raw_fact_ids: tuple[str, ...]
    raw_fact_texts: tuple[str, ...]
    canonical_fact_texts: tuple[str, ...]
    cluster_vectors: NDArray[np.float32]
    cluster_assignments: NDArray[np.int_]
    cluster_members: tuple[tuple[int, ...], ...]
    coverage_matrix: NDArray[np.int_]


def flatten_fact_items(articles: Sequence[StructuredArticle]) -> list[RawFact]:
    """Flatten article fact items in article order, then event/claim order."""

    article_ids = _validate_article_ids(articles)
    raw_facts: list[RawFact] = []
    for article, article_id in zip(articles, article_ids, strict=True):
        raw_facts.extend(
            RawFact(article_id=article_id, fact_id=fact_id, text=text)
            for fact_id, text in article.fact_items
        )
    return raw_facts


def build_fact_universe(
    articles: Sequence[StructuredArticle],
    fact_embeddings: NDArray[Any],
    *,
    similarity_threshold: float = 0.85,
    linkage: Linkage = "average",
) -> FactUniverse:
    """Validate inputs and build an identity fact universe placeholder."""

    _validate_similarity_threshold(similarity_threshold)
    _validate_linkage(linkage)
    article_ids = tuple(_validate_article_ids(articles))
    raw_facts = flatten_fact_items(articles)
    embeddings = _validate_fact_embeddings(fact_embeddings, row_count=len(raw_facts))

    fact_count = len(raw_facts)
    embedding_dim = embeddings.shape[1]
    if fact_count == 0:
        return FactUniverse(
            article_ids=article_ids,
            raw_fact_article_ids=(),
            raw_fact_ids=(),
            raw_fact_texts=(),
            canonical_fact_texts=(),
            cluster_vectors=np.empty((0, embedding_dim), dtype=np.float32),
            cluster_assignments=np.empty((0,), dtype=np.int_),
            cluster_members=(),
            coverage_matrix=np.zeros((len(article_ids), 0), dtype=np.int_),
        )

    article_index = {article_id: index for index, article_id in enumerate(article_ids)}
    coverage_matrix = np.zeros((len(article_ids), fact_count), dtype=np.int_)
    for fact_index, raw_fact in enumerate(raw_facts):
        coverage_matrix[article_index[raw_fact.article_id], fact_index] = 1

    return FactUniverse(
        article_ids=article_ids,
        raw_fact_article_ids=tuple(fact.article_id for fact in raw_facts),
        raw_fact_ids=tuple(fact.fact_id for fact in raw_facts),
        raw_fact_texts=tuple(fact.text for fact in raw_facts),
        canonical_fact_texts=tuple(fact.text for fact in raw_facts),
        cluster_vectors=np.asarray(embeddings, dtype=np.float32),
        cluster_assignments=np.arange(fact_count, dtype=np.int_),
        cluster_members=tuple((fact_index,) for fact_index in range(fact_count)),
        coverage_matrix=coverage_matrix,
    )


def _validate_article_ids(articles: Sequence[StructuredArticle]) -> list[str]:
    article_ids: list[str] = []
    for article in articles:
        article_id = article.article_id
        if article_id is None or article_id == "":
            msg = "article_id must be set for every structured article"
            raise ValueError(msg)
        article_ids.append(article_id)

    if len(article_ids) != len(set(article_ids)):
        msg = "article_ids must be unique"
        raise ValueError(msg)
    return article_ids


def _validate_fact_embeddings(
    fact_embeddings: NDArray[Any], *, row_count: int
) -> NDArray[np.float32]:
    embeddings = np.asarray(fact_embeddings)
    if embeddings.ndim != 2:
        msg = "fact_embeddings must be a 2-D array"
        raise ValueError(msg)
    if not (
        np.issubdtype(embeddings.dtype, np.floating)
        or np.issubdtype(embeddings.dtype, np.integer)
    ):
        msg = "fact_embeddings must be numeric"
        raise TypeError(msg)
    if not np.isfinite(embeddings).all():
        msg = "fact_embeddings must contain only finite values"
        raise ValueError(msg)
    if embeddings.shape[0] != row_count:
        msg = "fact_embeddings row count must match flattened fact count"
        raise ValueError(msg)

    numeric_embeddings = np.asarray(embeddings, dtype=np.float32)
    if row_count > 0:
        norms = np.linalg.norm(numeric_embeddings, axis=1)
        if (norms == 0).any():
            msg = "fact_embeddings rows must have nonzero vector norms"
            raise ValueError(msg)
    return numeric_embeddings


def _validate_similarity_threshold(similarity_threshold: float) -> None:
    if isinstance(similarity_threshold, bool) or not isinstance(
        similarity_threshold, int | float
    ):
        msg = "similarity_threshold must be numeric"
        raise TypeError(msg)
    threshold = float(similarity_threshold)
    if not np.isfinite(threshold):
        msg = "similarity_threshold must be finite"
        raise ValueError(msg)
    if threshold < -1.0 or threshold > 1.0:
        msg = "similarity_threshold must be between -1.0 and 1.0"
        raise ValueError(msg)


def _validate_linkage(linkage: Linkage) -> None:
    if linkage not in ("average", "single"):
        msg = "linkage must be 'average' or 'single'"
        raise ValueError(msg)
