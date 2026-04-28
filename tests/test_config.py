from pathlib import Path

import pytest

from news_ranker.config import RankerConfig

EXPECTED_COMPONENT_KEYS = {"centrality", "coverage", "density", "entity_coverage"}


def test_default_config_exposes_ranking_knobs() -> None:
    config = RankerConfig()

    assert config.similarity_threshold == pytest.approx(0.85)
    assert config.distance_threshold == pytest.approx(0.15)
    assert config.linkage == "average"
    assert config.coverage_weighting == "consensus"
    assert config.top_m is None
    assert config.selection_mode == "top_score"
    assert config.selection_lambda == pytest.approx(0.8)
    assert config.embedding_model_name == "all-MiniLM-L6-v2"
    assert config.llm_model_name
    assert config.prompt_version
    assert config.schema_version
    assert config.cache_dir is None
    assert set(config.profiles) == {"representative", "comprehensive", "concise"}
    for weights in config.profiles.values():
        assert set(weights) == EXPECTED_COMPONENT_KEYS
        assert sum(weights.values()) == pytest.approx(1.0)


def test_invalid_similarity_thresholds_fail_config_validation() -> None:
    with pytest.raises(TypeError, match="similarity_threshold must be numeric"):
        RankerConfig(similarity_threshold=True)
    with pytest.raises(ValueError, match="similarity_threshold must be finite"):
        RankerConfig(similarity_threshold=float("nan"))
    with pytest.raises(ValueError, match="between -1.0 and 1.0"):
        RankerConfig(similarity_threshold=1.1)
    with pytest.raises(ValueError, match="between -1.0 and 1.0"):
        RankerConfig(similarity_threshold=-1.1)


def test_invalid_top_m_fails_config_validation() -> None:
    with pytest.raises(TypeError, match="top_m must be an integer"):
        RankerConfig(top_m=1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="top_m must be an integer"):
        RankerConfig(top_m=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="top_m must be positive"):
        RankerConfig(top_m=0)


def test_invalid_selection_mode_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="selection_mode"):
        RankerConfig(selection_mode="weighted")  # type: ignore[arg-type]


def test_invalid_selection_lambda_fails_config_validation() -> None:
    with pytest.raises(TypeError, match="selection_lambda must be numeric"):
        RankerConfig(selection_lambda=False)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="selection_lambda must be finite"):
        RankerConfig(selection_lambda=float("inf"))
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        RankerConfig(selection_lambda=-0.1)
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        RankerConfig(selection_lambda=1.1)


def test_invalid_model_and_version_strings_fail_config_validation() -> None:
    with pytest.raises(ValueError, match="embedding_model_name"):
        RankerConfig(embedding_model_name="")
    with pytest.raises(ValueError, match="llm_model_name"):
        RankerConfig(llm_model_name=" ")
    with pytest.raises(ValueError, match="prompt_version"):
        RankerConfig(prompt_version="")
    with pytest.raises(ValueError, match="schema_version"):
        RankerConfig(schema_version="")


def test_invalid_cache_dir_fails_config_validation() -> None:
    with pytest.raises(TypeError, match="cache_dir"):
        RankerConfig(cache_dir=object())  # type: ignore[arg-type]


def test_cache_dir_accepts_path_like_value(tmp_path: Path) -> None:
    config = RankerConfig(cache_dir=tmp_path)

    assert config.cache_dir == tmp_path


def test_multilingual_embedding_model_can_be_configured() -> None:
    config = RankerConfig(
        embedding_model_name="paraphrase-multilingual-mpnet-base-v2"
    )

    assert config.embedding_model_name == "paraphrase-multilingual-mpnet-base-v2"


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
        RankerConfig(linkage="complete")  # type: ignore[arg-type]


def test_invalid_coverage_weighting_fails_config_validation() -> None:
    with pytest.raises(ValueError, match="coverage_weighting"):
        RankerConfig(coverage_weighting="tfidf")  # type: ignore[arg-type]


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
