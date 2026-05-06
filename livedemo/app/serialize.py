from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray

from news_ranker.cluster import FactUniverse
from news_ranker.results import (
    ProfileComparison,
    RankDiagnostics,
    RankingEntry,
    RankResult,
    SelectionResult,
)
from news_ranker.score import ScoreVector

ResultType = Literal["rank_result", "selection_result", "profile_comparison"]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, ScoreVector):
        return {
            "__type__": "score_vector",
            "raw": to_jsonable(value.raw),
            "normalized": to_jsonable(value.normalized),
            "defined": value.defined,
        }
    if isinstance(value, FactUniverse):
        return {
            "__type__": "fact_universe",
            "article_ids": list(value.article_ids),
            "raw_fact_article_ids": list(value.raw_fact_article_ids),
            "raw_fact_ids": list(value.raw_fact_ids),
            "raw_fact_texts": list(value.raw_fact_texts),
            "canonical_fact_texts": list(value.canonical_fact_texts),
            "cluster_vectors": to_jsonable(value.cluster_vectors),
            "cluster_assignments": to_jsonable(value.cluster_assignments),
            "cluster_members": [list(members) for members in value.cluster_members],
            "coverage_matrix": to_jsonable(value.coverage_matrix.astype(int)),
        }
    if isinstance(value, RankingEntry):
        return {
            "__type__": "ranking_entry",
            "article_id": value.article_id,
            "rank": value.rank,
            "score": value.score,
            "components": dict(value.components),
        }
    if isinstance(value, RankDiagnostics):
        return {
            "__type__": "rank_diagnostics",
            "fact_universe": to_jsonable(value.fact_universe),
            "components": {
                name: to_jsonable(score)
                for name, score in value.components.items()
            },
            "article_embeddings": to_jsonable(value.article_embeddings),
        }
    if isinstance(value, RankResult):
        return {
            "__type__": "rank_result",
            "profile": value.profile,
            "entries": [to_jsonable(entry) for entry in value.entries],
            "diagnostics": to_jsonable(value.diagnostics),
        }
    if isinstance(value, SelectionResult):
        return {
            "__type__": "selection_result",
            "profile": value.profile,
            "m": value.m,
            "selected": [to_jsonable(entry) for entry in value.selected],
            "ranking": to_jsonable(value.ranking),
        }
    if isinstance(value, ProfileComparison):
        return {
            "__type__": "profile_comparison",
            "rankings": {
                profile: to_jsonable(ranking)
                for profile, ranking in value.rankings.items()
            },
        }
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    msg = f"{type(value).__name__} is not JSON serializable by livedemo"
    raise TypeError(msg)


def from_jsonable(
    payload: dict[str, Any],
) -> RankResult | SelectionResult | ProfileComparison:
    result_type = _require_type(payload)
    if result_type == "rank_result":
        return _rank_result(payload)
    if result_type == "selection_result":
        return _selection_result(payload)
    if result_type == "profile_comparison":
        return _profile_comparison(payload)
    msg = f"Unsupported result payload type: {result_type}"
    raise ValueError(msg)


def _rank_result(payload: dict[str, Any]) -> RankResult:
    return RankResult(
        profile=_string(payload, "profile"),
        entries=tuple(_ranking_entry(item) for item in _list(payload, "entries")),
        diagnostics=_rank_diagnostics(_dict(payload, "diagnostics")),
    )


def _selection_result(payload: dict[str, Any]) -> SelectionResult:
    return SelectionResult(
        profile=_string(payload, "profile"),
        m=_int(payload, "m"),
        selected=tuple(_ranking_entry(item) for item in _list(payload, "selected")),
        ranking=_rank_result(_dict(payload, "ranking")),
    )


def _profile_comparison(payload: dict[str, Any]) -> ProfileComparison:
    rankings = _dict(payload, "rankings")
    return ProfileComparison(
        rankings={
            str(profile): _rank_result(_expect_dict(ranking))
            for profile, ranking in rankings.items()
        }
    )


def _rank_diagnostics(payload: dict[str, Any]) -> RankDiagnostics:
    return RankDiagnostics(
        fact_universe=_fact_universe(_dict(payload, "fact_universe")),
        components={
            name: _score_vector(_expect_dict(score))
            for name, score in _dict(payload, "components").items()
        },
        article_embeddings=_float32_array(payload.get("article_embeddings")),
    )


def _fact_universe(payload: dict[str, Any]) -> FactUniverse:
    return FactUniverse(
        article_ids=tuple(_string_list(payload, "article_ids")),
        raw_fact_article_ids=tuple(_string_list(payload, "raw_fact_article_ids")),
        raw_fact_ids=tuple(_string_list(payload, "raw_fact_ids")),
        raw_fact_texts=tuple(_string_list(payload, "raw_fact_texts")),
        canonical_fact_texts=tuple(_string_list(payload, "canonical_fact_texts")),
        cluster_vectors=_float32_array(payload.get("cluster_vectors")),
        cluster_assignments=_int_array(payload.get("cluster_assignments")),
        cluster_members=tuple(
            tuple(int(index) for index in members)
            for members in _list(payload, "cluster_members")
        ),
        coverage_matrix=_int_array(payload.get("coverage_matrix")),
    )


def _score_vector(payload: dict[str, Any]) -> ScoreVector:
    return ScoreVector(
        raw=_float32_array(payload.get("raw")),
        normalized=_float32_array(payload.get("normalized")),
        defined=_bool(payload, "defined"),
    )


def _ranking_entry(payload: Any) -> RankingEntry:
    entry = _expect_dict(payload)
    return RankingEntry(
        article_id=_string(entry, "article_id"),
        rank=_int(entry, "rank"),
        score=_float(entry, "score"),
        components={
            str(key): _float_value(value)
            for key, value in _dict(entry, "components").items()
        },
    )


def _require_type(payload: dict[str, Any]) -> str:
    result_type = payload.get("__type__")
    if not isinstance(result_type, str):
        msg = "Result payload is missing __type__"
        raise ValueError(msg)
    return result_type


def _dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    return _expect_dict(payload.get(key))


def _expect_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = "Expected object payload"
        raise TypeError(msg)
    return cast(dict[str, Any], value)


def _list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        msg = f"{key} must be a list"
        raise TypeError(msg)
    return value


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string"
        raise TypeError(msg)
    return value


def _string_list(payload: dict[str, Any], key: str) -> list[str]:
    return [str(item) for item in _list(payload, key)]


def _int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer"
        raise TypeError(msg)
    return value


def _float(payload: dict[str, Any], key: str) -> float:
    return _float_value(payload.get(key))


def _float_value(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "Expected numeric value"
        raise TypeError(msg)
    return float(value)


def _bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"{key} must be a bool"
        raise TypeError(msg)
    return value


def _float32_array(value: Any) -> NDArray[np.float32]:
    return np.asarray(value, dtype=np.float32)


def _int_array(value: Any) -> NDArray[np.int_]:
    return np.asarray(value, dtype=np.int_)
