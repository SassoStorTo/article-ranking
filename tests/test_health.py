import news_ranker
from news_ranker import NewsRanker, RankerConfig, health
from news_ranker.evaluate import rank_correlation, top_m_overlap


def test_health() -> None:
    assert health() == {"ok": True}


def test_public_imports() -> None:
    assert NewsRanker.__name__ == "NewsRanker"
    assert RankerConfig.__name__ == "RankerConfig"
    assert news_ranker.__all__ == ["NewsRanker", "RankerConfig", "health"]


def test_evaluate_helpers_import_from_submodule_only() -> None:
    assert top_m_overlap.__module__ == "news_ranker.evaluate"
    assert rank_correlation.__module__ == "news_ranker.evaluate"
    assert not hasattr(news_ranker, "top_m_overlap")
    assert not hasattr(news_ranker, "rank_correlation")
    assert news_ranker.__all__ == ["NewsRanker", "RankerConfig", "health"]
