"""Article selection helpers."""

from collections.abc import Sequence
from typing import Any, TypeVar

import numpy as np
from numpy.typing import NDArray

T = TypeVar("T")


def select_top_score(ranking: Sequence[T], m: int) -> list[T]:
    """Return first ``m`` ranked objects from an already sorted ranking."""

    _validate_m(m, item_count=len(ranking))
    return list(ranking[:m])


def select_mmr(
    scores: NDArray[Any],
    normalized_article_embeddings: NDArray[Any],
    m: int,
    lambda_: float,
) -> list[int]:
    """Select input indices by maximal marginal relevance."""

    score_values = _validate_scores(scores, name="scores")
    embedding_values = _validate_embeddings(
        normalized_article_embeddings, name="normalized_article_embeddings"
    )
    _validate_m(m, item_count=score_values.shape[0])
    lambda_value = _validate_lambda(lambda_)

    if embedding_values.shape[0] != score_values.shape[0]:
        msg = "normalized_article_embeddings row count must match scores"
        raise ValueError(msg)

    selected: list[int] = []
    available = np.ones(score_values.shape[0], dtype=np.bool_)
    while len(selected) < m:
        best_index = _next_mmr_index(
            score_values,
            embedding_values,
            selected,
            available,
            lambda_value,
        )
        selected.append(best_index)
        available[best_index] = False
    return selected


def _next_mmr_index(
    scores: NDArray[np.float32],
    embeddings: NDArray[np.float32],
    selected: list[int],
    available: NDArray[np.bool_],
    lambda_: float,
) -> int:
    if selected:
        selected_embeddings = embeddings[np.asarray(selected, dtype=np.int_)]
        similarities = embeddings @ selected_embeddings.T
        penalties = np.maximum(np.float32(0.0), similarities.max(axis=1))
    else:
        penalties = np.zeros(scores.shape, dtype=np.float32)

    objectives = np.asarray(
        (np.float32(lambda_) * scores)
        - (np.float32(1.0 - lambda_) * penalties),
        dtype=np.float32,
    )
    objectives = np.where(available, objectives, np.float32(-np.inf))
    return int(np.argmax(objectives))


def _validate_m(m: int, *, item_count: int) -> None:
    if isinstance(m, bool) or not isinstance(m, int):
        msg = "m must be an integer"
        raise TypeError(msg)
    if m < 0:
        msg = "m must be nonnegative"
        raise ValueError(msg)
    if m > item_count:
        msg = "m must be no greater than item count"
        raise ValueError(msg)


def _validate_lambda(lambda_: float) -> float:
    value = float(lambda_)
    if not np.isfinite(value):
        msg = "lambda_ must be finite"
        raise ValueError(msg)
    if value < 0.0 or value > 1.0:
        msg = "lambda_ must be between 0 and 1"
        raise ValueError(msg)
    return value


def _validate_scores(values: NDArray[Any], *, name: str) -> NDArray[np.float32]:
    array = np.asarray(values)
    if array.ndim != 1:
        msg = f"{name} must be a 1-D array"
        raise ValueError(msg)
    return _validate_numeric_finite(array, name=name)


def _validate_embeddings(values: NDArray[Any], *, name: str) -> NDArray[np.float32]:
    array = np.asarray(values)
    if array.ndim != 2:
        msg = f"{name} must be a 2-D array"
        raise ValueError(msg)
    return _validate_numeric_finite(array, name=name)


def _validate_numeric_finite(
    array: NDArray[Any], *, name: str
) -> NDArray[np.float32]:
    if not _is_numeric(array):
        msg = f"{name} must be numeric"
        raise TypeError(msg)
    if not np.isfinite(array).all():
        msg = f"{name} must contain only finite values"
        raise ValueError(msg)
    with np.errstate(over="ignore", invalid="ignore"):
        converted = np.asarray(array, dtype=np.float32)
    if not np.isfinite(converted).all():
        msg = f"{name} must remain finite after float32 conversion"
        raise ValueError(msg)
    return converted


def _is_numeric(array: NDArray[Any]) -> bool:
    return bool(
        np.issubdtype(array.dtype, np.floating)
        or np.issubdtype(array.dtype, np.integer)
    )
