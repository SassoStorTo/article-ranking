"""Public ranking and selection result records."""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from news_ranker.cluster import FactUniverse
from news_ranker.score import ScoreVector


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


@dataclass(frozen=True)
class SelectionResult:
    """Configured article selection result."""

    profile: str
    m: int
    selected: tuple[RankingEntry, ...]
    ranking: RankResult


@dataclass(frozen=True)
class ProfileComparison:
    """Rankings for multiple configured scoring profiles."""

    rankings: Mapping[str, RankResult]
