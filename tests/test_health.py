from news_ranker import NewsRanker, RankerConfig, health


def test_health() -> None:
    assert health() == {"ok": True}


def test_public_imports() -> None:
    assert NewsRanker.__name__ == "NewsRanker"
    assert RankerConfig.__name__ == "RankerConfig"
