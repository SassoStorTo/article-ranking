"""Pipeline configuration defaults and validation."""

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from news_ranker.cluster import Linkage
from news_ranker.score import CoverageMode

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

    def __post_init__(self) -> None:
        _validate_similarity_threshold(self.similarity_threshold)
        _validate_linkage(self.linkage)
        _validate_coverage_weighting(self.coverage_weighting)
        _validate_profiles(self.profiles)


def _validate_similarity_threshold(similarity_threshold: float) -> None:
    if isinstance(similarity_threshold, bool) or not isinstance(
        similarity_threshold, int | float
    ):
        msg = "similarity_threshold must be numeric"
        raise TypeError(msg)
    if not np.isfinite(float(similarity_threshold)):
        msg = "similarity_threshold must be finite"
        raise ValueError(msg)


def _validate_linkage(linkage: Linkage) -> None:
    if linkage not in ("average", "single"):
        msg = "linkage must be 'average' or 'single'"
        raise ValueError(msg)


def _validate_coverage_weighting(coverage_weighting: CoverageMode) -> None:
    if coverage_weighting not in ("consensus", "rarity"):
        msg = "coverage_weighting must be 'consensus' or 'rarity'"
        raise ValueError(msg)


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
