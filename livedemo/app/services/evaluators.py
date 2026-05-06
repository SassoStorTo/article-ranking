from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from livedemo.app.db.models import (
    EvaluationArtifact,
    EvaluationHelper,
    Execution,
    ExecutionResult,
    ExecutionStatus,
)
from livedemo.app.serialize import from_jsonable, to_jsonable
from news_ranker.evaluate import (
    CorrelationMethod,
    anonymized_user_study_bundle,
    cluster_inspection_rows,
    component_score_table,
    rank_correlation,
    top_m_overlap,
)
from news_ranker.results import ProfileComparison, RankResult, SelectionResult


class EvaluationError(ValueError):
    """Raised when persisted results cannot satisfy an evaluation helper."""


class ExecutionNotFoundError(EvaluationError):
    """Raised when an evaluation references an unknown execution."""


ArticleMaterials = dict[str, dict[str, str]]


def list_artifacts(db: Session, *, execution_id: str) -> list[EvaluationArtifact]:
    _get_execution(db, execution_id=execution_id)
    return list(
        db.scalars(
            select(EvaluationArtifact)
            .where(EvaluationArtifact.execution_id == execution_id)
            .order_by(EvaluationArtifact.created_at, EvaluationArtifact.id)
        )
    )


def evaluate_top_m_overlap(
    db: Session,
    *,
    execution_id: str,
    other_execution_id: str,
    m: int,
) -> EvaluationArtifact:
    left = _rank_like_result(db, execution_id=execution_id)
    right = _rank_like_result(db, execution_id=other_execution_id)
    payload = _json_payload(top_m_overlap(left, right, m))
    return _persist_artifact(
        db,
        execution_id=execution_id,
        helper=EvaluationHelper.TOP_M_OVERLAP,
        params={"other_execution_id": other_execution_id, "m": m},
        payload=payload,
    )


def evaluate_rank_correlation(
    db: Session,
    *,
    execution_id: str,
    other_execution_id: str,
    method: CorrelationMethod,
) -> EvaluationArtifact:
    left = _rank_like_result(db, execution_id=execution_id)
    right = _rank_like_result(db, execution_id=other_execution_id)
    payload = _json_payload(rank_correlation(left, right, method))
    return _persist_artifact(
        db,
        execution_id=execution_id,
        helper=EvaluationHelper.RANK_CORRELATION,
        params={"other_execution_id": other_execution_id, "method": method},
        payload=payload,
    )


def evaluate_component_table(
    db: Session,
    *,
    execution_id: str,
) -> EvaluationArtifact:
    result = _component_table_result(db, execution_id=execution_id)
    payload = {"rows": to_jsonable(component_score_table(result))}
    return _persist_artifact(
        db,
        execution_id=execution_id,
        helper=EvaluationHelper.COMPONENT_SCORE_TABLE,
        params={},
        payload=payload,
    )


def evaluate_cluster_inspection(
    db: Session,
    *,
    execution_id: str,
    rare_threshold: int,
) -> EvaluationArtifact:
    result = _rank_like_result(db, execution_id=execution_id)
    payload = {"rows": to_jsonable(cluster_inspection_rows(result, rare_threshold))}
    return _persist_artifact(
        db,
        execution_id=execution_id,
        helper=EvaluationHelper.CLUSTER_INSPECTION_ROWS,
        params={"rare_threshold": rare_threshold},
        payload=payload,
    )


def evaluate_user_study_bundle(
    db: Session,
    *,
    execution_id: str,
    materials: ArticleMaterials,
    include_scores: bool,
) -> EvaluationArtifact:
    result = _selection_result(db, execution_id=execution_id)
    payload = _json_payload(
        anonymized_user_study_bundle(
            result,
            materials,
            include_scores=include_scores,
        )
    )
    return _persist_artifact(
        db,
        execution_id=execution_id,
        helper=EvaluationHelper.ANONYMIZED_USER_STUDY_BUNDLE,
        params={"materials": materials, "include_scores": include_scores},
        payload=payload,
    )


def run_full_suite(
    db: Session,
    *,
    execution_id: str,
    baseline_execution_id: str,
    m: int,
    method: CorrelationMethod,
    rare_threshold: int,
    materials: ArticleMaterials,
    include_scores: bool,
) -> list[EvaluationArtifact]:
    artifacts = [
        evaluate_top_m_overlap(
            db,
            execution_id=execution_id,
            other_execution_id=baseline_execution_id,
            m=m,
        ),
        evaluate_rank_correlation(
            db,
            execution_id=execution_id,
            other_execution_id=baseline_execution_id,
            method=method,
        ),
        evaluate_component_table(db, execution_id=execution_id),
        evaluate_cluster_inspection(
            db,
            execution_id=execution_id,
            rare_threshold=rare_threshold,
        ),
    ]
    if materials:
        artifacts.append(
            evaluate_user_study_bundle(
                db,
                execution_id=execution_id,
                materials=materials,
                include_scores=include_scores,
            )
        )
    return artifacts


def _persist_artifact(
    db: Session,
    *,
    execution_id: str,
    helper: EvaluationHelper,
    params: dict[str, object],
    payload: dict[str, object],
) -> EvaluationArtifact:
    artifact = EvaluationArtifact(
        execution_id=execution_id,
        helper=helper,
        params_json=params,
        payload_json=payload,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _rank_like_result(db: Session, *, execution_id: str) -> RankResult:
    result = _single_result(db, execution_id=execution_id)
    if isinstance(result, RankResult):
        return result
    if isinstance(result, SelectionResult):
        return result.ranking
    msg = "Evaluation helper requires a rank or select execution result."
    raise EvaluationError(msg)


def _selection_result(db: Session, *, execution_id: str) -> SelectionResult:
    result = _single_result(db, execution_id=execution_id)
    if isinstance(result, SelectionResult):
        return result
    msg = "User-study bundle requires a select execution result."
    raise EvaluationError(msg)


def _component_table_result(
    db: Session,
    *,
    execution_id: str,
) -> RankResult | tuple[RankResult, ...] | ProfileComparison:
    result = _single_result(db, execution_id=execution_id)
    if isinstance(result, SelectionResult):
        return result.ranking
    if isinstance(result, RankResult | ProfileComparison):
        return result
    msg = "Component table requires a rank, select, or compare result."
    raise EvaluationError(msg)


def _single_result(
    db: Session,
    *,
    execution_id: str,
) -> RankResult | SelectionResult | ProfileComparison:
    execution = _get_execution(db, execution_id=execution_id)
    if execution.status != ExecutionStatus.SUCCEEDED:
        msg = "Evaluation requires a succeeded execution."
        raise EvaluationError(msg)

    results = list(
        db.scalars(
            select(ExecutionResult)
            .where(ExecutionResult.execution_id == execution_id)
            .order_by(ExecutionResult.created_at, ExecutionResult.id)
        )
    )
    if len(results) != 1:
        msg = "Evaluation requires exactly one persisted execution result."
        raise EvaluationError(msg)
    return from_jsonable(results[0].result_json)


def _get_execution(db: Session, *, execution_id: str) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None:
        msg = f"Execution {execution_id} was not found."
        raise ExecutionNotFoundError(msg)
    return execution


def _json_payload(value: Any) -> dict[str, object]:
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    payload = to_jsonable(value)
    if not isinstance(payload, dict):
        return {"value": payload}
    return payload
