from dataclasses import asdict, is_dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from livedemo.app.db.models import Execution, ExecutionStatus
from livedemo.app.schemas import (
    ExecutionComparisonMetadata,
    ExecutionComparisonMetrics,
    ExecutionComparisonResponse,
    ExecutionComparisonSection,
    ExecutionComparisonSectionPair,
    ExecutionComparisonWarning,
)
from livedemo.app.serialize import from_jsonable, to_jsonable
from news_ranker.evaluate import (
    cluster_inspection_rows,
    rank_correlation,
    top_m_overlap,
)
from news_ranker.results import ProfileComparison, RankResult, SelectionResult


class ExecutionComparisonError(ValueError):
    """Raised when execution comparison cannot be built."""


class ExecutionComparisonNotFoundError(ExecutionComparisonError):
    """Raised when execution comparison references unknown execution."""


def build_execution_comparison(
    db: Session,
    *,
    left_execution_id: str,
    right_execution_id: str,
) -> ExecutionComparisonResponse:
    left = _get_execution(db, execution_id=left_execution_id)
    right = _get_execution(db, execution_id=right_execution_id)
    _validate_execution_ready(left)
    _validate_execution_ready(right)

    left_sections, left_warnings = _sections(left)
    right_sections, right_warnings = _sections(right)
    if not left_sections:
        msg = f"Execution {left.id} has no comparable result sections."
        raise ExecutionComparisonError(msg)
    if not right_sections:
        msg = f"Execution {right.id} has no comparable result sections."
        raise ExecutionComparisonError(msg)

    return ExecutionComparisonResponse(
        left=_metadata(left),
        right=_metadata(right),
        section_pairs=_pair_sections(left_sections, right_sections),
        warnings=[*left_warnings, *right_warnings],
    )


def _get_execution(db: Session, *, execution_id: str) -> Execution:
    execution = db.scalar(
        select(Execution)
        .where(Execution.id == execution_id)
        .options(
            selectinload(Execution.corpus),
            selectinload(Execution.results),
            selectinload(Execution.evaluation_artifacts),
        )
    )
    if execution is None:
        msg = f"Execution {execution_id} was not found."
        raise ExecutionComparisonNotFoundError(msg)
    return execution


def _validate_execution_ready(execution: Execution) -> None:
    if execution.status != ExecutionStatus.SUCCEEDED:
        msg = "Execution comparison requires succeeded executions."
        raise ExecutionComparisonError(msg)


def _metadata(execution: Execution) -> ExecutionComparisonMetadata:
    corpus_name = execution.corpus.name if execution.corpus is not None else ""
    return ExecutionComparisonMetadata(
        id=UUID(execution.id),
        corpus_id=UUID(execution.corpus_id),
        corpus_name=corpus_name,
        kind=execution.kind.value,
        status=execution.status.value,
        profiles=execution.profiles,
        profile_summary=", ".join(execution.profiles) if execution.profiles else "none",
        m=execution.m,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error=execution.error,
        has_evaluation_artifacts=bool(execution.evaluation_artifacts),
        created_at=execution.created_at,
        config_json=execution.config_json,
    )


def _sections(
    execution: Execution,
) -> tuple[list[ExecutionComparisonSection], list[ExecutionComparisonWarning]]:
    sections: list[ExecutionComparisonSection] = []
    warnings: list[ExecutionComparisonWarning] = []
    results = sorted(execution.results, key=lambda item: (item.profile or "", item.id))
    if not results:
        return [], [
            ExecutionComparisonWarning(
                code="missing_results",
                message=f"Execution {execution.id} has no persisted results.",
            )
        ]

    for result in results:
        try:
            parsed = from_jsonable(result.result_json)
        except (TypeError, ValueError) as exc:
            warnings.append(
                ExecutionComparisonWarning(
                    code="invalid_result_payload",
                    message=(
                        f"Execution {execution.id} result {result.id} is invalid: {exc}"
                    ),
                )
            )
            continue
        sections.extend(_sections_for_result(parsed, result.result_json))
    return sections, warnings


def _sections_for_result(
    result: RankResult | SelectionResult | ProfileComparison,
    result_json: dict[str, Any],
) -> list[ExecutionComparisonSection]:
    if isinstance(result, RankResult):
        return [_section_from_rank("result", result.profile, result, result_json)]
    if isinstance(result, SelectionResult):
        return [
            _section_from_rank(
                "result",
                result.profile,
                result.ranking,
                result_json,
                selected_article_ids=[entry.article_id for entry in result.selected],
                result_type="selection_result",
            )
        ]
    return [
        _section_from_rank(
            profile,
            profile,
            ranking,
            result_json,
            result_type="profile_comparison",
        )
        for profile, ranking in sorted(result.rankings.items())
    ]


def _section_from_rank(
    key: str,
    label: str,
    rank_result: RankResult,
    result_json: dict[str, Any],
    *,
    selected_article_ids: list[str] | None = None,
    result_type: Literal[
        "rank_result", "selection_result", "profile_comparison"
    ] = "rank_result",
) -> ExecutionComparisonSection:
    cluster_rows = _cluster_rows(rank_result)
    return ExecutionComparisonSection(
        key=key,
        label=label,
        profile=rank_result.profile,
        result_type=result_type,
        rank_result_json=to_jsonable(rank_result),
        result_json=result_json,
        entry_count=len(rank_result.entries),
        selected_article_ids=selected_article_ids or [],
        cluster_count=len(cluster_rows),
        cluster_inspection_rows=cluster_rows,
    )


def _pair_sections(
    left: list[ExecutionComparisonSection],
    right: list[ExecutionComparisonSection],
) -> list[ExecutionComparisonSectionPair]:
    if len(left) == 1 and len(right) == 1:
        return [_available_pair(left[0], right[0])]
    if len(left) == 1:
        return [_available_pair(left[0], section) for section in right]
    if len(right) == 1:
        return [_available_pair(section, right[0]) for section in left]

    pairs: list[ExecutionComparisonSectionPair] = []
    left_by_key = {section.key: section for section in left}
    right_by_key = {section.key: section for section in right}
    for key in sorted(set(left_by_key) | set(right_by_key)):
        left_section = left_by_key.get(key)
        right_section = right_by_key.get(key)
        if left_section is not None and right_section is not None:
            pairs.append(_available_pair(left_section, right_section))
        else:
            pairs.append(_unmatched_pair(key, left_section, right_section))
    return pairs


def _available_pair(
    left: ExecutionComparisonSection,
    right: ExecutionComparisonSection,
) -> ExecutionComparisonSectionPair:
    label = f"{left.label} ↔ {right.label}"
    metrics, warnings = _metrics(left, right)
    return ExecutionComparisonSectionPair(
        key=f"{left.key}__{right.key}",
        label=label,
        left=left,
        right=right,
        metrics=metrics,
        warnings=warnings,
    )


def _unmatched_pair(
    key: str,
    left: ExecutionComparisonSection | None,
    right: ExecutionComparisonSection | None,
) -> ExecutionComparisonSectionPair:
    warning = ExecutionComparisonWarning(
        code="unmatched_section",
        message=f"Section {key} is only available on one side.",
        left_section_key=left.key if left is not None else None,
        right_section_key=right.key if right is not None else None,
    )
    return ExecutionComparisonSectionPair(
        key=key,
        label=(left or right).label if (left or right) is not None else key,
        left=left,
        right=right,
        metrics=None,
        warnings=[warning],
    )


def _metrics(
    left: ExecutionComparisonSection,
    right: ExecutionComparisonSection,
) -> tuple[ExecutionComparisonMetrics, list[ExecutionComparisonWarning]]:
    warnings: list[ExecutionComparisonWarning] = []
    left_rank = _rank_result(left.rank_result_json)
    right_rank = _rank_result(right.rank_result_json)
    top_m = min(len(left_rank.entries), len(right_rank.entries))
    overlap = None
    if top_m >= 1:
        try:
            overlap = _json_payload(top_m_overlap(left_rank, right_rank, top_m))
        except (TypeError, ValueError) as exc:
            warnings.append(
                ExecutionComparisonWarning(code="top_m_unavailable", message=str(exc))
            )
    correlation = None
    try:
        correlation = _json_payload(rank_correlation(left_rank, right_rank, "kendall"))
    except ValueError as exc:
        warnings.append(
            ExecutionComparisonWarning(
                code="rank_correlation_unavailable",
                message=str(exc),
            )
        )

    left_cluster_texts = _cluster_texts(left.cluster_inspection_rows)
    right_cluster_texts = _cluster_texts(right.cluster_inspection_rows)
    shared_cluster_texts = sorted(set(left_cluster_texts) & set(right_cluster_texts))
    return (
        ExecutionComparisonMetrics(
            top_m=top_m if top_m >= 1 else None,
            top_m_overlap=overlap,
            rank_correlation=correlation,
            left_cluster_count=len(left_cluster_texts),
            right_cluster_count=len(right_cluster_texts),
            shared_cluster_count=len(shared_cluster_texts),
            shared_canonical_cluster_texts=shared_cluster_texts,
        ),
        warnings,
    )


def _rank_result(payload: dict[str, Any]) -> RankResult:
    result = from_jsonable(payload)
    if not isinstance(result, RankResult):
        msg = "Comparison section must contain a rank result."
        raise ExecutionComparisonError(msg)
    return result


def _cluster_rows(rank_result: RankResult) -> list[dict[str, Any]]:
    rows = to_jsonable(cluster_inspection_rows(rank_result, 1))
    if not isinstance(rows, list):
        return []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append({str(key): value for key, value in row.items()})
    return normalized


def _cluster_texts(rows: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for row in rows:
        text = row.get("canonical_fact_text")
        if text is not None:
            texts.append(str(text))
    return texts


def _json_payload(value: Any) -> dict[str, Any]:
    if is_dataclass(value) and not isinstance(value, type):
        payload = to_jsonable(asdict(value))
    else:
        payload = to_jsonable(value)
    if not isinstance(payload, dict):
        return {"value": payload}
    return payload
