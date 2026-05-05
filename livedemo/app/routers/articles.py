from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Article, Corpus, StructuredArticle
from app.deps import get_session, get_settings
from app.schemas import ArticleDetail, ArticleSummary, UploadedArticles
from app.services.ingestion import (
    InvalidUploadFilenameError,
    content_sha256,
    decode_upload_bytes,
    derive_title,
    validate_txt_filename,
    write_upload_bytes,
)

router = APIRouter(tags=["articles"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
FilesDep = Annotated[list[UploadFile], File()]


def _article_summary(article: Article) -> ArticleSummary:
    return ArticleSummary.model_validate(article)


def _latest_structured_payload(
    session: Session,
    article_id: str,
) -> dict[str, Any] | None:
    structured = session.scalars(
        select(StructuredArticle)
        .where(StructuredArticle.article_id == article_id)
        .order_by(StructuredArticle.created_at.desc(), StructuredArticle.id.desc()),
    ).first()
    if structured is None:
        return None
    return structured.payload_json


def _remove_written_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


@router.post(
    "/api/corpora/{corpus_id}/articles",
    response_model=UploadedArticles,
    status_code=status.HTTP_201_CREATED,
)
async def upload_articles(
    corpus_id: str,
    files: FilesDep,
    session: SessionDep,
    settings: SettingsDep,
) -> UploadedArticles:
    corpus = session.get(Corpus, corpus_id)
    if corpus is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found",
        )

    uploads: list[tuple[str, bytes, str]] = []
    seen_filenames: set[str] = set()
    for upload in files:
        try:
            filename = validate_txt_filename(upload.filename or "")
            data = await upload.read()
            body = decode_upload_bytes(data)
        except InvalidUploadFilenameError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="uploaded files must be valid UTF-8",
            ) from exc
        if filename in seen_filenames:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Article filename already exists in corpus",
            )
        seen_filenames.add(filename)
        uploads.append((filename, data, body))

    articles: list[Article] = []
    written_paths: list[Path] = []
    try:
        for filename, data, body in uploads:
            article = Article(
                corpus_id=corpus_id,
                filename=filename,
                title=derive_title(filename, body),
                body=body,
                content_sha256=content_sha256(body),
            )
            session.add(article)
            session.flush()
            written_paths.append(
                write_upload_bytes(settings.uploads_dir, corpus_id, article.id, data),
            )
            articles.append(article)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _remove_written_files(written_paths)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Article filename already exists in corpus",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        _remove_written_files(written_paths)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while uploading articles",
        ) from exc

    return UploadedArticles(
        articles=[_article_summary(article) for article in articles],
    )


@router.get("/api/articles/{article_id}", response_model=ArticleDetail)
def get_article(article_id: str, session: SessionDep) -> ArticleDetail:
    article = session.get(Article, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    return ArticleDetail(
        id=article.id,
        corpus_id=article.corpus_id,
        filename=article.filename,
        title=article.title,
        body=article.body,
        content_sha256=article.content_sha256,
        uploaded_at=article.uploaded_at,
        structured_payload=_latest_structured_payload(session, article.id),
    )
