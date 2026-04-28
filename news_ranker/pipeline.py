"""Fixture-backed public ranking pipeline."""

from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias

from news_ranker.config import RankerConfig
from news_ranker.embed import FactEmbedder
from news_ranker.schemas import StructuredArticle, load_structured_article

ArticleInput: TypeAlias = (
    str | Path | Sequence[str | Path] | Sequence[StructuredArticle]
)


class NewsRanker:
    """Public orchestrator for fixture-backed article ranking."""

    def __init__(
        self, embedder: FactEmbedder | None = None, config: RankerConfig | None = None
    ) -> None:
        """Create ranker with explicit fact embedder dependency."""

        if embedder is None:
            msg = (
                "NewsRanker requires an explicit FactEmbedder; "
                "no default embedder is used"
            )
            raise TypeError(msg)
        self._embedder = embedder
        self._config = config or RankerConfig()

    def _load_structured_articles(
        self, articles: ArticleInput
    ) -> list[StructuredArticle]:
        """Normalize supported structured inputs to loaded articles."""

        if isinstance(articles, str | Path):
            return self._load_from_path(Path(articles))

        if not isinstance(articles, Sequence):
            msg = (
                "articles must be a path or sequence of paths/StructuredArticle objects"
            )
            raise TypeError(msg)
        if not articles:
            msg = "articles input must not be empty"
            raise ValueError(msg)

        loaded: list[StructuredArticle] = []
        for item in articles:
            if isinstance(item, StructuredArticle):
                loaded.append(item)
            elif isinstance(item, str | Path):
                loaded.extend(self._load_from_path(Path(item)))
            elif isinstance(item, dict):
                msg = (
                    "raw article dictionaries require decomposition, "
                    "which is not implemented yet"
                )
                raise NotImplementedError(msg)
            else:
                msg = (
                    "articles sequence items must be paths or "
                    f"StructuredArticle objects; got {type(item).__name__}"
                )
                raise TypeError(msg)

        if not loaded:
            msg = "articles input must not be empty"
            raise ValueError(msg)
        return loaded

    def _load_from_path(self, path: Path) -> list[StructuredArticle]:
        if path.is_dir():
            article_paths = sorted(path.glob("*.json"))
            if not article_paths:
                msg = f"article directory contains no JSON files: {path}"
                raise ValueError(msg)
            return [
                load_structured_article(article_path) for article_path in article_paths
            ]

        if path.is_file():
            return [load_structured_article(path)]

        msg = f"article path does not exist: {path}"
        raise FileNotFoundError(msg)
