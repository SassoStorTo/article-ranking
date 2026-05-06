from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from livedemo.app.db.models import Article, Corpus
from livedemo.app.deps import get_db
from livedemo.app.schemas import (
    ArticleSummary,
    CorpusCreate,
    CorpusDetail,
    CorpusSummary,
    IdResponse,
)

router = APIRouter(prefix="/corpora", tags=["corpora"])
DbSession = Annotated[Session, Depends(get_db)]


def _corpus_not_found(corpus_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Corpus {corpus_id} was not found.",
    )


def _article_summary(article: Article) -> ArticleSummary:
    return ArticleSummary(
        id=UUID(article.id),
        corpus_id=UUID(article.corpus_id),
        filename=article.filename,
        title=article.title,
        body_length=len(article.body),
        decomposition_status=(
            "decomposed" if article.structured_articles else "not_started"
        ),
        uploaded_at=article.uploaded_at,
    )


def _corpus_detail(corpus: Corpus) -> CorpusDetail:
    return CorpusDetail(
        id=UUID(corpus.id),
        name=corpus.name,
        notes=corpus.notes,
        created_at=corpus.created_at,
        articles=[_article_summary(article) for article in corpus.articles],
    )


def _corpus_summary(row: tuple[Corpus, int]) -> CorpusSummary:
    corpus, article_count = row
    return CorpusSummary(
        id=UUID(corpus.id),
        name=corpus.name,
        notes=corpus.notes,
        created_at=corpus.created_at,
        article_count=article_count,
    )


@router.post("", response_model=IdResponse, status_code=status.HTTP_201_CREATED)
def create_corpus(payload: CorpusCreate, db: DbSession) -> IdResponse:
    corpus = Corpus(name=payload.name, notes=payload.notes)
    db.add(corpus)
    db.commit()
    db.refresh(corpus)
    return IdResponse(id=UUID(corpus.id))


@router.get("", response_model=list[CorpusSummary])
def list_corpora(db: DbSession) -> list[CorpusSummary]:
    statement: Select[tuple[Corpus, int]] = (
        select(Corpus, func.count(Article.id))
        .outerjoin(Article)
        .group_by(Corpus.id)
        .order_by(Corpus.created_at.desc(), Corpus.name)
    )
    return [_corpus_summary(row) for row in db.execute(statement).all()]


@router.get("/{corpus_id}", response_model=CorpusDetail)
def get_corpus(corpus_id: UUID, db: DbSession) -> CorpusDetail:
    corpus = db.scalar(
        select(Corpus)
        .where(Corpus.id == str(corpus_id))
        .options(
            selectinload(Corpus.articles).selectinload(Article.structured_articles)
        )
    )
    if corpus is None:
        raise _corpus_not_found(corpus_id)
    corpus.articles.sort(key=lambda article: article.uploaded_at)
    return _corpus_detail(corpus)


@router.delete("/{corpus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_corpus(corpus_id: UUID, db: DbSession) -> Response:
    corpus = db.get(Corpus, str(corpus_id))
    if corpus is None:
        raise _corpus_not_found(corpus_id)
    db.delete(corpus)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
