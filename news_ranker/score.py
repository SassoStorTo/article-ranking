"""Article scoring helpers."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from news_ranker.schemas import Entity, StructuredArticle

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


def entity_coverage(structured_articles: Sequence[StructuredArticle]) -> ScoreVector:
    """Score weighted recall of normalized entities by group."""

    article_count = len(structured_articles)
    if article_count == 0:
        return minmax_normalize(np.empty((0,), dtype=np.float32), defined=False)

    article_entity_keys = [_entity_keys(article) for article in structured_articles]
    entity_keys = sorted(set().union(*article_entity_keys))
    if not entity_keys:
        return minmax_normalize(
            np.zeros((article_count,), dtype=np.float32), defined=False
        )

    key_to_index = {key: index for index, key in enumerate(entity_keys)}
    entity_matrix = np.zeros((article_count, len(entity_keys)), dtype=np.float32)
    for article_index, keys in enumerate(article_entity_keys):
        for key in keys:
            entity_matrix[article_index, key_to_index[key]] = 1.0

    document_frequencies = entity_matrix.sum(axis=0, dtype=np.float32)
    weights = document_frequencies / np.float32(article_count)
    weight_sum = float(weights.sum())
    if weight_sum <= float(_EPSILON):
        return minmax_normalize(
            np.zeros((article_count,), dtype=np.float32), defined=False
        )

    raw = ((entity_matrix @ weights) / weight_sum).astype(np.float32)
    return minmax_normalize(raw)


def combine(
    components: Mapping[str, ScoreVector],
    weights: Mapping[str, float],
    *,
    renormalize_undefined: bool = True,
) -> NDArray[np.float32]:
    """Combine normalized component vectors with nonnegative weights."""

    if not components:
        msg = "components must not be empty"
        raise ValueError(msg)
    if not weights:
        msg = "weights must not be empty"
        raise ValueError(msg)

    unknown_weights = set(weights) - set(components)
    if unknown_weights:
        msg = "weights must only reference components"
        raise ValueError(msg)

    normalized_components = {
        name: _validate_component(component, name=name)
        for name, component in components.items()
    }
    component_lengths = {values.shape[0] for values in normalized_components.values()}
    if len(component_lengths) != 1:
        msg = "component normalized lengths must match"
        raise ValueError(msg)
    article_count = component_lengths.pop()

    scores = np.zeros((article_count,), dtype=np.float32)
    total_weight = 0.0
    effective_weight = 0.0
    for name, weight in weights.items():
        scalar = _validate_weight(weight, name=name)
        total_weight += scalar
        if renormalize_undefined and not components[name].defined:
            continue
        effective_weight += scalar
        scores += normalized_components[name] * np.float32(scalar)

    if total_weight <= float(_EPSILON):
        msg = "weights must include at least one positive value"
        raise ValueError(msg)
    denominator = effective_weight if renormalize_undefined else total_weight
    if denominator <= float(_EPSILON):
        return scores
    return (scores / np.float32(denominator)).astype(np.float32)


def _validate_component(component: ScoreVector, *, name: str) -> NDArray[np.float32]:
    raw = _validate_score_values(component.raw, name=f"{name}.raw")
    normalized = _validate_score_values(component.normalized, name=f"{name}.normalized")
    if raw.shape != normalized.shape:
        msg = f"{name} raw and normalized lengths must match"
        raise ValueError(msg)
    return normalized


def _validate_weight(weight: float, *, name: str) -> float:
    scalar = float(weight)
    if not np.isfinite(scalar):
        msg = f"{name} weight must be finite"
        raise ValueError(msg)
    if scalar < 0.0:
        msg = f"{name} weight must be nonnegative"
        raise ValueError(msg)
    return scalar


def _entity_keys(article: StructuredArticle) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    _add_entity_keys(keys, "people", article.entities.people)
    _add_entity_keys(keys, "organizations", article.entities.organizations)
    _add_entity_keys(keys, "locations", article.entities.locations)
    return keys


def _add_entity_keys(
    keys: set[tuple[str, str]], group_name: str, entities: Sequence[Entity]
) -> None:
    for entity in entities:
        normalized_name = _normalize_entity_name(entity.name)
        if normalized_name:
            keys.add((group_name, normalized_name))


def _normalize_entity_name(name: str) -> str:
    return " ".join(name.casefold().split())


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
