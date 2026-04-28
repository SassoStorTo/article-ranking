"""Article scoring helpers."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from news_ranker.schemas import StructuredArticle

_EPSILON = np.float32(1e-12)

CoverageMode = Literal["consensus", "rarity"]


@dataclass(frozen=True)
class ScoreVector:
    """Raw and normalized score values for one component."""

    raw: NDArray[np.float32]
    normalized: NDArray[np.float32]
    defined: bool


def minmax_normalize(values: NDArray[Any], *, defined: bool = True) -> ScoreVector:
    """Normalize one component to [0, 1] with tied defined values at one."""

    raw = _validate_score_values(values, name="values")
    if not defined:
        return ScoreVector(
            raw=raw,
            normalized=np.zeros(raw.shape, dtype=np.float32),
            defined=False,
        )
    if raw.size == 0:
        return ScoreVector(
            raw=raw,
            normalized=np.zeros(raw.shape, dtype=np.float32),
            defined=False,
        )

    minimum = float(raw.min())
    maximum = float(raw.max())
    if maximum == minimum:
        normalized = np.ones(raw.shape, dtype=np.float32)
    else:
        normalized = ((raw - minimum) / (maximum - minimum)).astype(np.float32)
    return ScoreVector(raw=raw, normalized=normalized, defined=True)


def centrality(article_embeddings: NDArray[Any]) -> ScoreVector:
    """Score articles by negative distance to L2-normalized corpus centroid."""

    embeddings = _validate_embeddings(article_embeddings, name="article_embeddings")
    article_count = embeddings.shape[0]
    if article_count == 0:
        return minmax_normalize(np.empty((0,), dtype=np.float32), defined=False)

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True).astype(np.float32)
    safe_norms = np.maximum(norms, _EPSILON)
    normalized_embeddings = embeddings / safe_norms
    centroid = normalized_embeddings.mean(axis=0)
    distances = np.linalg.norm(normalized_embeddings - centroid, axis=1)
    raw = (-distances).astype(np.float32)
    return minmax_normalize(raw)


def coverage(
    coverage_matrix: NDArray[Any], mode: CoverageMode = "consensus"
) -> ScoreVector:
    """Score weighted fact recall from article-by-cluster coverage."""

    if mode not in ("consensus", "rarity"):
        msg = "mode must be 'consensus' or 'rarity'"
        raise ValueError(msg)

    matrix = _validate_coverage_matrix(coverage_matrix, name="coverage_matrix")
    article_count, fact_count = matrix.shape
    if article_count == 0 or fact_count == 0:
        return minmax_normalize(
            np.zeros((article_count,), dtype=np.float32), defined=False
        )

    binary_matrix = _binary_coverage_matrix(matrix)
    document_frequencies = binary_matrix.sum(axis=0, dtype=np.float32)
    if mode == "consensus":
        weights = document_frequencies / np.float32(article_count)
    else:
        weights = (
            np.log((np.float32(article_count) + 1.0) / (document_frequencies + 1.0))
            + 1.0
        ).astype(np.float32)

    weight_sum = float(weights.sum())
    if weight_sum <= float(_EPSILON):
        return minmax_normalize(
            np.zeros((article_count,), dtype=np.float32), defined=False
        )

    raw = ((binary_matrix @ weights) / weight_sum).astype(np.float32)
    return minmax_normalize(raw)


def density(
    structured_articles: Sequence[StructuredArticle], coverage_matrix: NDArray[Any]
) -> ScoreVector:
    """Score unique fact clusters per extracted event-plus-claim entry."""

    matrix = _validate_coverage_matrix(coverage_matrix, name="coverage_matrix")
    article_count = len(structured_articles)
    if matrix.shape[0] != article_count:
        msg = "coverage_matrix row count must match structured_articles"
        raise ValueError(msg)
    if article_count == 0:
        return minmax_normalize(np.empty((0,), dtype=np.float32), defined=False)

    binary_matrix = _binary_coverage_matrix(matrix)
    unique_counts = binary_matrix.sum(axis=1, dtype=np.float32)
    entry_counts = np.asarray(
        [len(article.events) + len(article.claims) for article in structured_articles],
        dtype=np.float32,
    )
    raw = np.zeros((article_count,), dtype=np.float32)
    np.divide(unique_counts, entry_counts, out=raw, where=entry_counts > 0)
    return minmax_normalize(raw, defined=bool((entry_counts > 0).any()))


def _validate_score_values(values: NDArray[Any], *, name: str) -> NDArray[np.float32]:
    array = np.asarray(values)
    if array.ndim != 1:
        msg = f"{name} must be a 1-D array"
        raise ValueError(msg)
    if not _is_numeric(array):
        msg = f"{name} must be numeric"
        raise TypeError(msg)
    if not np.isfinite(array).all():
        msg = f"{name} must contain only finite values"
        raise ValueError(msg)
    return np.asarray(array, dtype=np.float32)


def _validate_embeddings(values: NDArray[Any], *, name: str) -> NDArray[np.float32]:
    array = np.asarray(values)
    if array.ndim != 2:
        msg = f"{name} must be a 2-D array"
        raise ValueError(msg)
    if not _is_numeric(array):
        msg = f"{name} must be numeric"
        raise TypeError(msg)
    if not np.isfinite(array).all():
        msg = f"{name} must contain only finite values"
        raise ValueError(msg)
    return np.asarray(array, dtype=np.float32)


def _validate_coverage_matrix(
    values: NDArray[Any], *, name: str
) -> NDArray[np.float32]:
    array = np.asarray(values)
    if array.ndim != 2:
        msg = f"{name} must be a 2-D array"
        raise ValueError(msg)
    if not _is_numeric(array):
        msg = f"{name} must be numeric"
        raise TypeError(msg)
    if not np.isfinite(array).all():
        msg = f"{name} must contain only finite values"
        raise ValueError(msg)
    if (array < 0).any():
        msg = f"{name} must contain only nonnegative values"
        raise ValueError(msg)
    return np.asarray(array, dtype=np.float32)


def _binary_coverage_matrix(matrix: NDArray[np.float32]) -> NDArray[np.float32]:
    return (matrix > 0).astype(np.float32)


def _is_numeric(array: NDArray[Any]) -> bool:
    return bool(
        np.issubdtype(array.dtype, np.floating)
        or np.issubdtype(array.dtype, np.integer)
    )
