"""Helpers for comparing ranking results."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import sqrt
from typing import Literal, TypeAlias

from news_ranker.results import (
    ProfileComparison,
    RankingEntry,
    RankResult,
    SelectionResult,
)

CorrelationMethod = Literal["kendall", "spearman"]
ComponentScoreValue: TypeAlias = str | int | float | None
ComponentScoreRow: TypeAlias = dict[str, ComponentScoreValue]
ClusterInspectionValue: TypeAlias = str | int | bool | tuple[int, ...] | tuple[str, ...]
ClusterInspectionRow: TypeAlias = dict[str, ClusterInspectionValue]
ArticleMaterial: TypeAlias = Mapping[str, str]
UserStudyBundle: TypeAlias = dict[str, object]
_ALLOWED_MATERIAL_KEYS = frozenset({"title", "snippet", "summary"})


@dataclass(frozen=True)
class TopMOverlap:
    """Top-m overlap metrics for two ranking results."""

    overlap_count: int
    left_top_count: int
    right_top_count: int
    jaccard: float
    left_overlap_fraction: float
    right_overlap_fraction: float
    overlap_article_ids: tuple[str, ...]


@dataclass(frozen=True)
class RankCorrelation:
    """Rank-correlation metrics over common article IDs."""

    method: CorrelationMethod
    coefficient: float
    common_count: int
    common_article_ids: tuple[str, ...]
    left_only_article_ids: tuple[str, ...]
    right_only_article_ids: tuple[str, ...]


def top_m_overlap(left: RankResult, right: RankResult, m: int) -> TopMOverlap:
    """Compare top-m article-ID sets from two ranking results."""

    _validate_unique_article_ids(left)
    _validate_unique_article_ids(right)
    _validate_m(m, left, right)

    left_top_ids = tuple(entry.article_id for entry in left.entries[:m])
    right_top_ids = tuple(entry.article_id for entry in right.entries[:m])
    left_top_set = set(left_top_ids)
    right_top_set = set(right_top_ids)
    overlap_set = left_top_set & right_top_set
    union_count = len(left_top_set | right_top_set)
    overlap_count = len(overlap_set)

    return TopMOverlap(
        overlap_count=overlap_count,
        left_top_count=len(left_top_ids),
        right_top_count=len(right_top_ids),
        jaccard=overlap_count / union_count,
        left_overlap_fraction=overlap_count / len(left_top_ids),
        right_overlap_fraction=overlap_count / len(right_top_ids),
        overlap_article_ids=tuple(
            article_id for article_id in left_top_ids if article_id in overlap_set
        ),
    )


def rank_correlation(
    left: RankResult,
    right: RankResult,
    method: CorrelationMethod = "kendall",
) -> RankCorrelation:
    """Compute Kendall tau-a or Spearman rho over common article IDs."""

    if method not in {"kendall", "spearman"}:
        msg = "method must be 'kendall' or 'spearman'"
        raise ValueError(msg)

    _validate_unique_article_ids(left)
    _validate_unique_article_ids(right)

    left_ranks = _rank_by_article_id(left.entries)
    right_ranks = _rank_by_article_id(right.entries)
    right_ids = set(right_ranks)
    left_ids = set(left_ranks)
    common_article_ids = tuple(
        entry.article_id for entry in left.entries if entry.article_id in right_ids
    )
    if len(common_article_ids) < 2:
        msg = "rank correlation requires at least two common article IDs"
        raise ValueError(msg)

    left_only_article_ids = tuple(
        entry.article_id for entry in left.entries if entry.article_id not in right_ids
    )
    right_only_article_ids = tuple(
        entry.article_id for entry in right.entries if entry.article_id not in left_ids
    )

    if method == "kendall":
        coefficient = _kendall_tau_a(common_article_ids, left_ranks, right_ranks)
    else:
        coefficient = _spearman_rho(common_article_ids, left_ranks, right_ranks)

    return RankCorrelation(
        method=method,
        coefficient=coefficient,
        common_count=len(common_article_ids),
        common_article_ids=common_article_ids,
        left_only_article_ids=left_only_article_ids,
        right_only_article_ids=right_only_article_ids,
    )


def component_score_table(
    results: RankResult | Sequence[RankResult] | ProfileComparison,
) -> list[ComponentScoreRow]:
    """Flatten ranking scores and component values into deterministic rows."""

    rankings = _coerce_rank_results(results)
    component_names = _component_names(rankings)
    rows: list[ComponentScoreRow] = []

    for ranking in rankings:
        for entry in sorted(ranking.entries, key=lambda entry: entry.rank):
            row: ComponentScoreRow = {
                "profile": ranking.profile,
                "article_id": entry.article_id,
                "rank": entry.rank,
                "score": entry.score,
            }
            for component_name in component_names:
                row[component_name] = entry.components.get(component_name)
            rows.append(row)

    return rows


def cluster_inspection_rows(
    rank_result: RankResult, rare_threshold: int = 1
) -> list[ClusterInspectionRow]:
    """Export deterministic fact-cluster inspection rows."""

    _validate_rare_threshold(rare_threshold)
    fact_universe = rank_result.diagnostics.fact_universe
    rows: list[ClusterInspectionRow] = []

    for cluster_index, member_indices in enumerate(fact_universe.cluster_members):
        support_article_ids = tuple(
            article_id
            for article_id, covered in zip(
                fact_universe.article_ids,
                fact_universe.coverage_matrix[:, cluster_index],
                strict=True,
            )
            if int(covered) > 0
        )
        support_count = len(support_article_ids)
        rows.append({
            "cluster_index": cluster_index,
            "canonical_fact_text": fact_universe.canonical_fact_texts[cluster_index],
            "support_article_ids": support_article_ids,
            "support_count": support_count,
            "member_raw_indices": member_indices,
            "member_fact_ids": tuple(
                fact_universe.raw_fact_ids[index] for index in member_indices
            ),
            "member_texts": tuple(
                fact_universe.raw_fact_texts[index] for index in member_indices
            ),
            "is_rare": support_count <= rare_threshold,
        })

    return rows


def anonymized_user_study_bundle(
    selection: SelectionResult,
    article_materials: Mapping[str, ArticleMaterial],
    *,
    include_scores: bool = False,
) -> UserStudyBundle:
    """Build anonymized review materials for selected articles."""

    _validate_article_materials(article_materials)
    label_by_article_id = _selected_label_by_article_id(selection)
    selected_article_labels = tuple(
        label_by_article_id[entry.article_id] for entry in selection.selected
    )
    missing_article_ids = tuple(
        entry.article_id
        for entry in selection.selected
        if entry.article_id not in article_materials
    )
    if missing_article_ids:
        msg = f"missing article material for selected articles: {missing_article_ids}"
        raise ValueError(msg)

    bundle: UserStudyBundle = {
        "profile": selection.profile,
        "m": selection.m,
        "selected_article_labels": selected_article_labels,
        "article_materials": {
            label_by_article_id[entry.article_id]: dict(
                article_materials[entry.article_id]
            )
            for entry in selection.selected
        },
    }

    if include_scores:
        bundle["scores"] = tuple(
            {
                "label": label_by_article_id[entry.article_id],
                "rank": entry.rank,
                "score": entry.score,
                "components": dict(entry.components),
            }
            for entry in selection.selected
        )

    return bundle


def _validate_article_materials(
    article_materials: Mapping[str, ArticleMaterial],
) -> None:
    for article_id, material in article_materials.items():
        unexpected_keys = tuple(
            key for key in material if key not in _ALLOWED_MATERIAL_KEYS
        )
        if unexpected_keys:
            msg = (
                f"unexpected material fields for article {article_id}: "
                f"{unexpected_keys}"
            )
            raise ValueError(msg)


def _selected_label_by_article_id(selection: SelectionResult) -> dict[str, str]:
    selected_article_ids = {entry.article_id for entry in selection.selected}
    return {
        entry.article_id: f"article_{index}"
        for index, entry in enumerate(selection.ranking.entries, start=1)
        if entry.article_id in selected_article_ids
    }


def _validate_m(m: int, left: RankResult, right: RankResult) -> None:
    if not isinstance(m, int) or isinstance(m, bool):
        msg = "m must be an integer"
        raise TypeError(msg)
    max_m = min(len(left.entries), len(right.entries))
    if not 1 <= m <= max_m:
        msg = f"m must satisfy 1 <= m <= min article_count ({max_m})"
        raise ValueError(msg)


def _validate_unique_article_ids(result: RankResult) -> None:
    seen: set[str] = set()
    for entry in result.entries:
        if entry.article_id in seen:
            msg = f"duplicate article_id in ranking: {entry.article_id}"
            raise ValueError(msg)
        seen.add(entry.article_id)


def _validate_rare_threshold(rare_threshold: int) -> None:
    if not isinstance(rare_threshold, int) or isinstance(rare_threshold, bool):
        msg = "rare_threshold must be an integer"
        raise TypeError(msg)
    if rare_threshold < 1:
        msg = "rare_threshold must be at least 1"
        raise ValueError(msg)


def _rank_by_article_id(entries: tuple[RankingEntry, ...]) -> dict[str, int]:
    return {entry.article_id: entry.rank for entry in entries}


def _coerce_rank_results(
    results: RankResult | Sequence[RankResult] | ProfileComparison,
) -> tuple[RankResult, ...]:
    if isinstance(results, RankResult):
        return (results,)
    if isinstance(results, ProfileComparison):
        return tuple(results.rankings.values())
    return tuple(results)


def _component_names(rankings: tuple[RankResult, ...]) -> tuple[str, ...]:
    names: dict[str, None] = {}
    for ranking in rankings:
        for entry in sorted(ranking.entries, key=lambda entry: entry.rank):
            for component_name in entry.components:
                names.setdefault(component_name, None)
    return tuple(names)


def _kendall_tau_a(
    article_ids: tuple[str, ...],
    left_ranks: dict[str, int],
    right_ranks: dict[str, int],
) -> float:
    concordant = 0
    discordant = 0
    for left_index, left_article_id in enumerate(article_ids[:-1]):
        for right_article_id in article_ids[left_index + 1 :]:
            left_delta = left_ranks[left_article_id] - left_ranks[right_article_id]
            right_delta = right_ranks[left_article_id] - right_ranks[right_article_id]
            if left_delta * right_delta > 0:
                concordant += 1
            else:
                discordant += 1

    pair_count = len(article_ids) * (len(article_ids) - 1) // 2
    return (concordant - discordant) / pair_count


def _spearman_rho(
    article_ids: tuple[str, ...],
    left_ranks: dict[str, int],
    right_ranks: dict[str, int],
) -> float:
    left_values = [float(left_ranks[article_id]) for article_id in article_ids]
    right_values = [float(right_ranks[article_id]) for article_id in article_ids]
    count = float(len(article_ids))
    left_mean = sum(left_values) / count
    right_mean = sum(right_values) / count
    covariance = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_values, right_values, strict=True)
    )
    left_variance = sum((left_value - left_mean) ** 2 for left_value in left_values)
    right_variance = sum(
        (right_value - right_mean) ** 2 for right_value in right_values
    )
    return covariance / sqrt(left_variance * right_variance)
