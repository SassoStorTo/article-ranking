import pytest

from news_ranker.config import RankerConfig

EXPECTED_COMPONENT_KEYS = {"centrality", "coverage", "density", "entity_coverage"}


def test_default_config_profiles_have_expected_component_keys() -> None:
    config = RankerConfig()

    assert set(config.profiles) == {"representative", "comprehensive", "concise"}
    for weights in config.profiles.values():
        assert set(weights) == EXPECTED_COMPONENT_KEYS
        assert sum(weights.values()) == pytest.approx(1.0)


def test_empty_profile_name_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="profile name"):
        RankerConfig(profiles={"": _profile_weights()})


def test_negative_profile_weight_fails_config_validation() -> None:
    weights = _profile_weights(coverage=-0.1, density=0.6)

    with pytest.raises(ValueError, match="nonnegative"):
        RankerConfig(profiles={"broken": weights})


def test_profile_weights_must_sum_to_one() -> None:
    weights = _profile_weights(coverage=0.4)

    with pytest.raises(ValueError, match="sum to 1.0"):
        RankerConfig(profiles={"broken": weights})


def test_profile_weights_must_include_required_component_keys() -> None:
    weights = _profile_weights()
    del weights["entity_coverage"]

    with pytest.raises(ValueError, match="component keys"):
        RankerConfig(profiles={"broken": weights})


def test_invalid_linkage_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="linkage"):
        RankerConfig(linkage="complete")


def test_invalid_coverage_weighting_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="coverage_weighting"):
        RankerConfig(coverage_weighting="tfidf")


def _profile_weights(
    *,
    centrality: float = 0.4,
    coverage: float = 0.5,
    density: float = 0.1,
    entity_coverage: float = 0.0,
) -> dict[str, float]:
    return {
        "centrality": centrality,
        "coverage": coverage,
        "density": density,
        "entity_coverage": entity_coverage,
    }
