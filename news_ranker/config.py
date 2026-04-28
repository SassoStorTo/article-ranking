"""Pipeline configuration defaults and validation."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from news_ranker.cluster import Linkage
from news_ranker.score import CoverageMode

SelectionMode = Literal["top_score", "mmr"]

_COMPONENT_KEYS = frozenset({"centrality", "coverage", "density", "entity_coverage"})
_PROFILE_SUM_TOLERANCE = 1e-6


def _default_profiles() -> dict[str, dict[str, float]]:
    return {
        "representative": {
            "centrality": 0.4,
            "coverage": 0.5,
            "density": 0.1,
            "entity_coverage": 0.0,
        },
        "comprehensive": {
            "centrality": 0.2,
            "coverage": 0.7,
            "density": 0.1,
            "entity_coverage": 0.0,
        },
        "concise": {
            "centrality": 0.2,
            "coverage": 0.4,
            "density": 0.4,
            "entity_coverage": 0.0,
        },
    }


@dataclass(frozen=True)
class RankerConfig:
    """Configuration for fixture-backed ranking orchestration."""

    similarity_threshold: float = 0.85
    linkage: Linkage = "average"
    coverage_weighting: CoverageMode = "consensus"
    profiles: Mapping[str, Mapping[str, float]] = field(
        default_factory=_default_profiles
    )
    top_m: int | None = None
    selection_mode: SelectionMode = "top_score"
    selection_lambda: float = 0.8
    embedding_model_name: str = "all-MiniLM-L6-v2"
    llm_model_name: str = "claude-3-haiku"
    prompt_version: str = "v1"
    schema_version: str = "v1"
    cache_dir: str | os.PathLike[str] | None = None

    @property
    def distance_threshold(self) -> float:
        """Cosine distance threshold derived from similarity threshold."""

        return 1.0 - float(self.similarity_threshold)

    def __post_init__(self) -> None:
        _validate_similarity_threshold(self.similarity_threshold)
        _validate_linkage(self.linkage)
        _validate_coverage_weighting(self.coverage_weighting)
        _validate_profiles(self.profiles)
        _validate_top_m(self.top_m)
        _validate_selection_mode(self.selection_mode)
        _validate_selection_lambda(self.selection_lambda)
        _validate_non_empty_string(
            self.embedding_model_name, name="embedding_model_name"
        )
        _validate_non_empty_string(self.llm_model_name, name="llm_model_name")
        _validate_non_empty_string(self.prompt_version, name="prompt_version")
        _validate_non_empty_string(self.schema_version, name="schema_version")
        _validate_cache_dir(self.cache_dir)


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


def _validate_coverage_weighting(coverage_weighting: CoverageMode) -> None:
    if coverage_weighting not in ("consensus", "rarity"):
        msg = "coverage_weighting must be 'consensus' or 'rarity'"
        raise ValueError(msg)


def _validate_top_m(top_m: int | None) -> None:
    if top_m is None:
        return
    if isinstance(top_m, bool) or not isinstance(top_m, int):
        msg = "top_m must be an integer"
        raise TypeError(msg)
    if top_m < 1:
        msg = "top_m must be positive"
        raise ValueError(msg)


def _validate_selection_mode(selection_mode: SelectionMode) -> None:
    if selection_mode not in ("top_score", "mmr"):
        msg = "selection_mode must be 'top_score' or 'mmr'"
        raise ValueError(msg)


def _validate_selection_lambda(selection_lambda: float) -> None:
    if isinstance(selection_lambda, bool) or not isinstance(
        selection_lambda, int | float
    ):
        msg = "selection_lambda must be numeric"
        raise TypeError(msg)
    scalar = float(selection_lambda)
    if not np.isfinite(scalar):
        msg = "selection_lambda must be finite"
        raise ValueError(msg)
    if scalar < 0.0 or scalar > 1.0:
        msg = "selection_lambda must be between 0.0 and 1.0"
        raise ValueError(msg)


def _validate_non_empty_string(value: str, *, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        msg = f"{name} must be a non-empty string"
        raise ValueError(msg)


def _validate_cache_dir(cache_dir: str | os.PathLike[str] | None) -> None:
    if cache_dir is None:
        return
    if not isinstance(cache_dir, str | os.PathLike):
        msg = "cache_dir must be a path-like value"
        raise TypeError(msg)


def _validate_profiles(profiles: Mapping[str, Mapping[str, float]]) -> None:
    if not profiles:
        msg = "profiles must not be empty"
        raise ValueError(msg)

    for profile_name, weights in profiles.items():
        _validate_profile_name(profile_name)
        _validate_profile_weights(profile_name, weights)


def _validate_profile_name(profile_name: str) -> None:
    if not isinstance(profile_name, str) or not profile_name.strip():
        msg = "profile name must be a non-empty string"
        raise ValueError(msg)


def _validate_profile_weights(profile_name: str, weights: Mapping[str, float]) -> None:
    weight_keys = set(weights)
    if weight_keys != _COMPONENT_KEYS:
        missing = sorted(_COMPONENT_KEYS - weight_keys)
        extra = sorted(weight_keys - _COMPONENT_KEYS)
        msg = (
            f"profile {profile_name!r} must define exactly component keys "
            f"{sorted(_COMPONENT_KEYS)}; missing={missing}, extra={extra}"
        )
        raise ValueError(msg)

    total = 0.0
    for component_name, weight in weights.items():
        scalar = float(weight)
        if not np.isfinite(scalar):
            msg = f"profile {profile_name!r} weight {component_name!r} must be finite"
            raise ValueError(msg)
        if scalar < 0.0:
            msg = (
                f"profile {profile_name!r} weight {component_name!r} "
                "must be nonnegative"
            )
            raise ValueError(msg)
        total += scalar

    if abs(total - 1.0) > _PROFILE_SUM_TOLERANCE:
        msg = f"profile {profile_name!r} weights must sum to 1.0"
        raise ValueError(msg)
