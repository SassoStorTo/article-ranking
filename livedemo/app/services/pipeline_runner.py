from collections.abc import Sequence
from concurrent.futures import Future
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from livedemo.app.db.models import (
    Article,
    Corpus,
    Execution,
    ExecutionKind,
    ExecutionResult,
    ExecutionStatus,
    utc_now,
)
from livedemo.app.deps import EmbedderProvider
from livedemo.app.serialize import to_jsonable
from livedemo.app.services.decomposition import (
    decompose_article,
    latest_structured_article,
)
from news_ranker.config import RankerConfig
from news_ranker.decompose import DecompositionClient
from news_ranker.pipeline import NewsRanker
from news_ranker.results import ProfileComparison, RankResult, SelectionResult
from news_ranker.schemas import StructuredArticle as NewsRankerStructuredArticle


def create_execution(
    db: Session,
    *,
    corpus_id: str,
    kind: ExecutionKind,
    config_json: dict[str, Any],
    profiles: Sequence[str],
    m: int | None,
) -> Execution:
    execution = Execution(
        corpus_id=corpus_id,
        kind=kind,
        status=ExecutionStatus.PENDING,
        config_json=config_json,
        profiles=list(profiles),
        m=m,
        started_at=None,
        finished_at=None,
        error=None,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def submit_execution(
    executor: Any,
    session_factory: sessionmaker[Session],
    *,
    execution_id: str,
    kind: ExecutionKind,
    config: RankerConfig,
    profile: str | None,
    profiles: Sequence[str] | None,
    m: int | None,
    client: DecompositionClient,
    embedder_provider: EmbedderProvider,
) -> Future[None]:
    return executor.submit(
        run_execution,
        session_factory,
        execution_id=execution_id,
        kind=kind,
        config=config,
        profile=profile,
        profiles=profiles,
        m=m,
        client=client,
        embedder_provider=embedder_provider,
    )


def run_execution(
    session_factory: sessionmaker[Session],
    *,
    execution_id: str,
    kind: ExecutionKind,
    config: RankerConfig,
    profile: str | None,
    profiles: Sequence[str] | None,
    m: int | None,
    client: DecompositionClient,
    embedder_provider: EmbedderProvider,
) -> None:
    with session_factory() as db:
        execution = db.get(Execution, execution_id)
        if execution is None:
            return

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = utc_now()
        execution.error = None
        db.commit()

        try:
            structured_articles = _load_structured_corpus(
                db,
                corpus_id=execution.corpus_id,
                client=client,
                ranker_config=config,
            )
            ranker = NewsRanker(
                embedder=embedder_provider(config.embedding_model_name),
                config=config,
            )
            result = _run_ranker(
                ranker,
                kind=kind,
                articles=structured_articles,
                profile=profile,
                profiles=profiles,
                m=m,
            )
            _replace_results(db, execution=execution, result=result)
            execution.status = ExecutionStatus.SUCCEEDED
        except Exception as exc:
            db.rollback()
            execution = db.get(Execution, execution_id)
            if execution is None:
                return
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)
        finally:
            execution = db.get(Execution, execution_id)
            if execution is not None:
                execution.finished_at = utc_now()
                db.commit()


def _load_structured_corpus(
    db: Session,
    *,
    corpus_id: str,
    client: DecompositionClient,
    ranker_config: RankerConfig,
) -> list[NewsRankerStructuredArticle]:
    corpus = db.scalar(select(Corpus).where(Corpus.id == corpus_id))
    if corpus is None:
        msg = f"Corpus {corpus_id} was not found."
        raise ValueError(msg)

    articles = list(
        db.scalars(
            select(Article)
            .where(Article.corpus_id == corpus_id)
            .order_by(Article.uploaded_at, Article.id)
        ).all()
    )
    if not articles:
        msg = "Execution requires at least one article."
        raise ValueError(msg)

    structured_articles: list[NewsRankerStructuredArticle] = []
    for article in articles:
        structured = latest_structured_article(db, article_id=article.id)
        if structured is None:
            structured = decompose_article(
                db,
                article=article,
                client=client,
                ranker_config=ranker_config,
            )
        article_payload = NewsRankerStructuredArticle.model_validate(
            structured.payload_json
        )
        if article_payload.article_id != article.id:
            article_payload = article_payload.model_copy(
                update={"article_id": article.id}
            )
        structured_articles.append(article_payload)
    return structured_articles


def _run_ranker(
    ranker: NewsRanker,
    *,
    kind: ExecutionKind,
    articles: Sequence[NewsRankerStructuredArticle],
    profile: str | None,
    profiles: Sequence[str] | None,
    m: int | None,
) -> RankResult | SelectionResult | ProfileComparison:
    if kind == ExecutionKind.RANK:
        return ranker.rank(articles, profile=profile or "representative")
    if kind == ExecutionKind.SELECT:
        return ranker.select(articles, m=m, profile=profile or "representative")
    if kind == ExecutionKind.COMPARE_PROFILES:
        return ranker.compare_profiles(articles, profiles=profiles)
    msg = f"Unsupported execution kind: {kind}"
    raise ValueError(msg)


def _replace_results(
    db: Session,
    *,
    execution: Execution,
    result: RankResult | SelectionResult | ProfileComparison,
) -> None:
    for existing in execution.results:
        db.delete(existing)
    db.flush()

    profile = None
    if isinstance(result, RankResult | SelectionResult):
        profile = result.profile

    db.add(
        ExecutionResult(
            execution_id=execution.id,
            profile=profile,
            result_json=to_jsonable(result),
        )
    )
