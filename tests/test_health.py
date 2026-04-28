from news_ranker import health


def test_health() -> None:
    assert health() == {"ok": True}
