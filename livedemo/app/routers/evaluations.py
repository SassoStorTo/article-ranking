from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from livedemo.app.db.models import EvaluationArtifact
from livedemo.app.deps import get_db
from livedemo.app.schemas import (
    ClusterInspectionRequest,
    ComponentTableRequest,
    EvaluationArtifactRecord,
    FullEvaluationSuiteRequest,
    RankCorrelationRequest,
    TopMOverlapRequest,
    UserStudyBundleRequest,
)
from livedemo.app.services.evaluators import (
    EvaluationError,
    ExecutionNotFoundError,
    evaluate_cluster_inspection,
    evaluate_component_table,
    evaluate_rank_correlation,
    evaluate_top_m_overlap,
    evaluate_user_study_bundle,
    list_artifacts,
    run_full_suite,
)

router = APIRouter(prefix="/executions/{execution_id}", tags=["evaluations"])
DbSession = Annotated[Session, Depends(get_db)]


def artifact_record(artifact: EvaluationArtifact) -> EvaluationArtifactRecord:
    return EvaluationArtifactRecord(
        id=UUID(artifact.id),
        execution_id=UUID(artifact.execution_id),
        helper=artifact.helper.value,
        params_json=artifact.params_json,
        payload_json=artifact.payload_json,
        created_at=artifact.created_at,
    )


def evaluation_http_error(exc: EvaluationError) -> HTTPException:
    if isinstance(exc, ExecutionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.get("/eval", response_model=list[EvaluationArtifactRecord])
def get_evaluation_artifacts(
    execution_id: UUID,
    db: DbSession,
) -> list[EvaluationArtifactRecord]:
    try:
        artifacts = list_artifacts(db, execution_id=str(execution_id))
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return [artifact_record(artifact) for artifact in artifacts]


@router.post("/eval/top-m-overlap", response_model=EvaluationArtifactRecord)
def post_top_m_overlap(
    execution_id: UUID,
    payload: TopMOverlapRequest,
    db: DbSession,
) -> EvaluationArtifactRecord:
    try:
        artifact = evaluate_top_m_overlap(
            db,
            execution_id=str(execution_id),
            other_execution_id=str(payload.other_execution_id),
            m=payload.m,
        )
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return artifact_record(artifact)


@router.post("/eval/rank-correlation", response_model=EvaluationArtifactRecord)
def post_rank_correlation(
    execution_id: UUID,
    payload: RankCorrelationRequest,
    db: DbSession,
) -> EvaluationArtifactRecord:
    try:
        artifact = evaluate_rank_correlation(
            db,
            execution_id=str(execution_id),
            other_execution_id=str(payload.other_execution_id),
            method=payload.method,
        )
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return artifact_record(artifact)


@router.post("/eval/component-table", response_model=EvaluationArtifactRecord)
def post_component_table(
    execution_id: UUID,
    _payload: ComponentTableRequest,
    db: DbSession,
) -> EvaluationArtifactRecord:
    try:
        artifact = evaluate_component_table(db, execution_id=str(execution_id))
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return artifact_record(artifact)


@router.post("/eval/cluster-inspection", response_model=EvaluationArtifactRecord)
def post_cluster_inspection(
    execution_id: UUID,
    payload: ClusterInspectionRequest,
    db: DbSession,
) -> EvaluationArtifactRecord:
    try:
        artifact = evaluate_cluster_inspection(
            db,
            execution_id=str(execution_id),
            rare_threshold=payload.rare_threshold,
        )
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return artifact_record(artifact)


@router.post("/eval/user-study-bundle", response_model=EvaluationArtifactRecord)
def post_user_study_bundle(
    execution_id: UUID,
    payload: UserStudyBundleRequest,
    db: DbSession,
) -> EvaluationArtifactRecord:
    try:
        artifact = evaluate_user_study_bundle(
            db,
            execution_id=str(execution_id),
            materials={
                article_id: material.model_dump(exclude_none=True)
                for article_id, material in payload.materials.items()
            },
            include_scores=payload.include_scores,
        )
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return artifact_record(artifact)


@router.post("/test-suite", response_model=list[EvaluationArtifactRecord])
def post_full_evaluation_suite(
    execution_id: UUID,
    payload: FullEvaluationSuiteRequest,
    db: DbSession,
) -> list[EvaluationArtifactRecord]:
    try:
        artifacts = run_full_suite(
            db,
            execution_id=str(execution_id),
            baseline_execution_id=str(payload.baseline_execution_id),
            m=payload.m,
            method=payload.method,
            rare_threshold=payload.rare_threshold,
            materials={
                article_id: material.model_dump(exclude_none=True)
                for article_id, material in payload.materials.items()
            },
            include_scores=payload.include_scores,
        )
    except EvaluationError as exc:
        raise evaluation_http_error(exc) from exc
    return [artifact_record(artifact) for artifact in artifacts]
