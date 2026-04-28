"""News article ranking and selection library."""

from news_ranker.config import RankerConfig
from news_ranker.pipeline import NewsRanker

__all__ = ["NewsRanker", "RankerConfig", "health"]


def health() -> dict[str, bool]:
    """Return package health status."""
    return {"ok": True}
