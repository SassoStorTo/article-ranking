from concurrent.futures import Executor
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from livedemo.app.db.models import Corpus, Execution, ExecutionKind, ExecutionStatus
from livedemo.app.deps import (
    EmbedderProvider,
    get_db,
    get_embedder_provider,
    get_executor,
    get_mistral_client,
    get_session_factory,
)
from livedemo.app.schemas import (
    CompareProfilesExecutionRequest,
    ExecutionAccepted,
    ExecutionDetail,
    ExecutionKindValue,
    ExecutionResultRecord,
    ExecutionStatusValue,
    ExecutionSummary,
    RankExecutionRequest,
    SelectExecutionRequest,
    normalize_ranker_config,
)
from livedemo.app.services.pipeline_runner import create_execution, submit_execution
from news_ranker.decompose import DecompositionClient

router = APIRouter(prefix="/executions", tags=["executions"])
DbSession = Annotated[Session, Depends(get_db)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]
DecompositionClientDep = Annotated[DecompositionClient, Depends(get_mistral_client)]
EmbedderProviderDep = Annotated[EmbedderProvider, Depends(get_embedder_provider)]
ExecutorDep = Annotated[Executor, Depends(get_executor)]


def _not_found(entity: str, entity_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} {entity_id} was not found.",
    )


def _execution_summary(execution: Execution) -> ExecutionSummary:
    return ExecutionSummary(
        id=UUID(execution.id),
        corpus_id=UUID(execution.corpus_id),
        kind=execution.kind.value,
        status=execution.status.value,
        profiles=execution.profiles,
        m=execution.m,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error=execution.error,
        created_at=execution.created_at,
    )


def _execution_detail(execution: Execution) -> ExecutionDetail:
    return ExecutionDetail(
        **_execution_summary(execution).model_dump(),
        config_json=execution.config_json,
        results=[
            ExecutionResultRecord(
                id=UUID(result.id),
                execution_id=UUID(result.execution_id),
                profile=result.profile,
                result_json=result.result_json,
                created_at=result.created_at,
            )
            for result in sorted(
                execution.results,
                key=lambda item: (item.profile or "", item.created_at, item.id),
            )
        ],
    )


def _validate_corpus(db: Session, corpus_id: UUID) -> None:
    if db.get(Corpus, str(corpus_id)) is None:
        raise _not_found("Corpus", corpus_id)


def _config_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.post(
    "/rank",
    response_model=ExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_rank(
    payload: RankExecutionRequest,
    db: DbSession,
    session_factory: SessionFactoryDep,
    client: DecompositionClientDep,
    embedder_provider: EmbedderProviderDep,
    executor: ExecutorDep,
) -> ExecutionAccepted:
    _validate_corpus(db, payload.corpus_id)
    try:
        config, config_json = normalize_ranker_config(payload.config)
    except (TypeError, ValueError) as exc:
        raise _config_error(exc) from exc

    execution = create_execution(
        db,
        corpus_id=str(payload.corpus_id),
        kind=ExecutionKind.RANK,
        config_json=config_json,
        profiles=[payload.profile],
        m=None,
    )
    submit_execution(
        executor,
        session_factory,
        execution_id=execution.id,
        kind=ExecutionKind.RANK,
        config=config,
        profile=payload.profile,
        profiles=None,
        m=None,
        client=client,
        embedder_provider=embedder_provider,
    )
    return ExecutionAccepted(
        execution_id=UUID(execution.id),
        status=ExecutionStatus.PENDING.value,
    )


@router.post(
    "/select",
    response_model=ExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_select(
    payload: SelectExecutionRequest,
    db: DbSession,
    session_factory: SessionFactoryDep,
    client: DecompositionClientDep,
    embedder_provider: EmbedderProviderDep,
    executor: ExecutorDep,
) -> ExecutionAccepted:
    _validate_corpus(db, payload.corpus_id)
    try:
        config, config_json = normalize_ranker_config(payload.config, m=payload.m)
    except (TypeError, ValueError) as exc:
        raise _config_error(exc) from exc

    execution = create_execution(
        db,
        corpus_id=str(payload.corpus_id),
        kind=ExecutionKind.SELECT,
        config_json=config_json,
        profiles=[payload.profile],
        m=payload.m,
    )
    submit_execution(
        executor,
        session_factory,
        execution_id=execution.id,
        kind=ExecutionKind.SELECT,
        config=config,
        profile=payload.profile,
        profiles=None,
        m=payload.m,
        client=client,
        embedder_provider=embedder_provider,
    )
    return ExecutionAccepted(
        execution_id=UUID(execution.id),
        status=ExecutionStatus.PENDING.value,
    )


@router.post(
    "/compare",
    response_model=ExecutionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_compare(
    payload: CompareProfilesExecutionRequest,
    db: DbSession,
    session_factory: SessionFactoryDep,
    client: DecompositionClientDep,
    embedder_provider: EmbedderProviderDep,
    executor: ExecutorDep,
) -> ExecutionAccepted:
    _validate_corpus(db, payload.corpus_id)
    try:
        config, config_json = normalize_ranker_config(payload.config)
    except (TypeError, ValueError) as exc:
        raise _config_error(exc) from exc

    profiles = payload.profiles or list(config.profiles)
    execution = create_execution(
        db,
        corpus_id=str(payload.corpus_id),
        kind=ExecutionKind.COMPARE_PROFILES,
        config_json=config_json,
        profiles=profiles,
        m=None,
    )
    submit_execution(
        executor,
        session_factory,
        execution_id=execution.id,
        kind=ExecutionKind.COMPARE_PROFILES,
        config=config,
        profile=None,
        profiles=profiles,
        m=None,
        client=client,
        embedder_provider=embedder_provider,
    )
    return ExecutionAccepted(
        execution_id=UUID(execution.id),
        status=ExecutionStatus.PENDING.value,
    )


@router.get("", response_model=list[ExecutionSummary])
def list_executions(
    db: DbSession,
    corpus_id: UUID | None = None,
    kind: ExecutionKindValue | None = None,
    status_filter: Annotated[
        ExecutionStatusValue | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExecutionSummary]:
    statement: Select[tuple[Execution]] = select(Execution)
    if corpus_id is not None:
        statement = statement.where(Execution.corpus_id == str(corpus_id))
    if kind is not None:
        statement = statement.where(Execution.kind == kind)
    if status_filter is not None:
        statement = statement.where(Execution.status == status_filter)
    statement = (
        statement
        .order_by(Execution.created_at.desc(), Execution.id)
        .limit(limit)
        .offset(offset)
    )
    return [_execution_summary(execution) for execution in db.scalars(statement)]


@router.get("/{execution_id}", response_model=ExecutionDetail)
def get_execution(execution_id: UUID, db: DbSession) -> ExecutionDetail:
    execution = db.scalar(
        select(Execution)
        .where(Execution.id == str(execution_id))
        .options(selectinload(Execution.results))
    )
    if execution is None:
        raise _not_found("Execution", execution_id)
    return _execution_detail(execution)


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_execution(execution_id: UUID, db: DbSession) -> Response:
    execution = db.get(Execution, str(execution_id))
    if execution is None:
        raise _not_found("Execution", execution_id)
    db.delete(execution)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
