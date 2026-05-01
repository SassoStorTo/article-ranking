from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Article, Corpus
from app.deps import get_session
from app.schemas import ArticleSummary, CorpusCreate, CorpusDetail, CorpusSummary

router = APIRouter(prefix="/api/corpora", tags=["corpora"])

SessionDep = Annotated[Session, Depends(get_session)]


def _article_summary(article: Article) -> ArticleSummary:
    return ArticleSummary.model_validate(article)


def _corpus_detail(corpus: Corpus) -> CorpusDetail:
    return CorpusDetail(
        id=corpus.id,
        name=corpus.name,
        notes=corpus.notes,
        created_at=corpus.created_at,
        articles=[
            _article_summary(article)
            for article in sorted(
                corpus.articles,
                key=lambda article: (article.uploaded_at, article.filename),
            )
        ],
    )


def _get_corpus_or_404(session: Session, corpus_id: str) -> Corpus:
    corpus = session.get(Corpus, corpus_id)
    if corpus is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found",
        )
    return corpus


@router.post("", response_model=CorpusDetail, status_code=status.HTTP_201_CREATED)
def create_corpus(payload: CorpusCreate, session: SessionDep) -> CorpusDetail:
    corpus = Corpus(name=payload.name, notes=payload.notes)
    session.add(corpus)
    session.commit()
    session.refresh(corpus)
    return _corpus_detail(corpus)


@router.get("", response_model=list[CorpusSummary])
def list_corpora(session: SessionDep) -> list[CorpusSummary]:
    rows = session.execute(
        select(Corpus, func.count(Article.id))
        .outerjoin(Article)
        .group_by(Corpus.id)
        .order_by(Corpus.created_at.desc(), Corpus.id.desc()),
    ).all()
    return [
        CorpusSummary(
            id=corpus.id,
            name=corpus.name,
            notes=corpus.notes,
            created_at=corpus.created_at,
            article_count=article_count,
        )
        for corpus, article_count in rows
    ]


@router.get("/{corpus_id}", response_model=CorpusDetail)
def get_corpus(corpus_id: str, session: SessionDep) -> CorpusDetail:
    return _corpus_detail(_get_corpus_or_404(session, corpus_id))


@router.delete("/{corpus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_corpus(corpus_id: str, session: SessionDep) -> Response:
    corpus = _get_corpus_or_404(session, corpus_id)
    session.delete(corpus)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
