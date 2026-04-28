"""Article scoring helpers."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

_EPSILON = np.float32(1e-12)


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


def _is_numeric(array: NDArray[Any]) -> bool:
    return bool(
        np.issubdtype(array.dtype, np.floating)
        or np.issubdtype(array.dtype, np.integer)
    )
