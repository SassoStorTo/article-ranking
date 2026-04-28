"""Embedding helpers for structured article facts."""

from collections.abc import Sequence
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray


class FactEmbedder(Protocol):
    """Protocol for injected local fact embedders."""

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed fact texts."""


class SentenceTransformerEmbedder:
    """Local SentenceTransformer-backed embedder."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Create local SentenceTransformer model."""

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed texts as a two-dimensional float32 array."""

        embeddings = cast(
            Any,
            self._model.encode(texts, convert_to_numpy=True),
        )
        return np.asarray(embeddings, dtype=np.float32)


def embed_facts(facts: list[str], embedder: FactEmbedder) -> NDArray[np.float32]:
    """Embed non-empty fact texts and validate numeric output."""

    if not facts:
        msg = "facts must not be empty"
        raise ValueError(msg)

    embeddings = np.asarray(embedder.embed(facts))
    if embeddings.ndim != 2:
        msg = "fact embeddings must be a 2-D array"
        raise ValueError(msg)
    if embeddings.dtype != np.float32:
        msg = "fact embeddings must have dtype float32"
        raise TypeError(msg)
    if not np.isfinite(embeddings).all():
        msg = "fact embeddings must contain only finite values"
        raise ValueError(msg)
    return embeddings


def embed_article_from_clusters(
    article_id: str,
    article_ids: Sequence[str],
    coverage_matrix: NDArray[Any],
    cluster_vectors: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Mean unique cluster vectors covered by one article."""

    ids = list(article_ids)
    if len(ids) != len(set(ids)):
        msg = "article_ids must be unique"
        raise ValueError(msg)
    if article_id not in ids:
        msg = f"unknown article_id: {article_id}"
        raise ValueError(msg)

    coverage = np.asarray(coverage_matrix)
    vectors = np.asarray(cluster_vectors)
    if coverage.ndim != 2:
        msg = "coverage_matrix must be a 2-D array"
        raise ValueError(msg)
    if vectors.ndim != 2:
        msg = "cluster_vectors must be a 2-D array"
        raise ValueError(msg)
    if coverage.shape[0] != len(ids):
        msg = "coverage_matrix row count must match article_ids"
        raise ValueError(msg)
    if coverage.shape[1] != vectors.shape[0]:
        msg = "coverage_matrix column count must match cluster_vectors row count"
        raise ValueError(msg)
    if not np.issubdtype(coverage.dtype, np.number) and not np.issubdtype(
        coverage.dtype,
        np.bool_,
    ):
        msg = "coverage_matrix must be numeric or boolean"
        raise TypeError(msg)
    if not np.issubdtype(vectors.dtype, np.number):
        msg = "cluster_vectors must be numeric"
        raise TypeError(msg)

    article_index = ids.index(article_id)
    covered_mask = coverage[article_index] != 0
    if not covered_mask.any():
        msg = f"article_id {article_id!r} covers no clusters"
        raise ValueError(msg)

    covered_vectors = np.asarray(vectors[covered_mask], dtype=np.float32)
    article_vector = np.mean(covered_vectors, axis=0)
    return np.asarray(article_vector, dtype=np.float32)
