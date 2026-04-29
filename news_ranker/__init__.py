"""News article ranking and selection library."""

from news_ranker.config import RankerConfig
from news_ranker.decompose import (
    DecompositionClient,
    DecompositionConfig,
    DecompositionError,
    decompose,
)
from news_ranker.pipeline import NewsRanker

__all__ = [
    "DecompositionClient",
    "DecompositionConfig",
    "DecompositionError",
    "NewsRanker",
    "RankerConfig",
    "decompose",
    "health",
]


def health() -> dict[str, bool]:
    """Return package health status."""
    return {"ok": True}
