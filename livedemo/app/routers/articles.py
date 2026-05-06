from email import policy
from email.parser import BytesParser
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from news_ranker.config import RankerConfig
from news_ranker.decompose import DecompositionClient, DecompositionError
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from livedemo.app.db.models import Article, Corpus, StructuredArticle
from livedemo.app.deps import (
    get_db,
    get_mistral_client,
    get_ranker_config,
    get_session_factory,
)
from livedemo.app.schemas import (
    ArticleDetail,
    ArticleUploadResponse,
    StructuredArticleRecord,
)
from livedemo.app.services.decomposition import (
    decompose_article,
    decompose_article_by_id,
    latest_structured_article,
)
from livedemo.app.services.ingestion import (
    ArticleDecodeError,
    ArticleUpload,
    DuplicateFilenameError,
    UnsupportedArticleTypeError,
    create_articles,
)

router = APIRouter(tags=["articles"])
DbSession = Annotated[Session, Depends(get_db)]
DecompositionClientDep = Annotated[DecompositionClient, Depends(get_mistral_client)]
RankerConfigDep = Annotated[RankerConfig, Depends(get_ranker_config)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def _not_found(entity: str, entity_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} {entity_id} was not found.",
    )


def _structured_record(structured: StructuredArticle) -> StructuredArticleRecord:
    return StructuredArticleRecord(
        id=UUID(structured.id),
        article_id=UUID(structured.article_id),
        llm_model=structured.llm_model,
        prompt_version=structured.prompt_version,
        schema_version=structured.schema_version,
        payload_json=structured.payload_json,
        created_at=structured.created_at,
    )


def _article_detail(
    article: Article,
    structured: StructuredArticle | None,
) -> ArticleDetail:
    return ArticleDetail(
        id=UUID(article.id),
        corpus_id=UUID(article.corpus_id),
        filename=article.filename,
        title=article.title,
        body=article.body,
        decomposition_status="decomposed" if structured is not None else "not_started",
        structured_article=(
            _structured_record(structured) if structured is not None else None
        ),
        uploaded_at=article.uploaded_at,
    )


async def _parse_multipart_uploads(request: Request) -> list[ArticleUpload]:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Article upload expects multipart/form-data.",
        )

    body = await request.body()
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
    )
    uploads: list[ArticleUpload] = []
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename is None:
            continue
        payload = part.get_payload(decode=True)
        uploads.append(ArticleUpload(filename=filename, content=payload or b""))

    if not uploads:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Upload at least one .txt file.",
        )
    return uploads


@router.post(
    "/corpora/{corpus_id}/articles",
    response_model=ArticleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_articles(
    corpus_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    client: DecompositionClientDep,
    ranker_config: RankerConfigDep,
    session_factory: SessionFactoryDep,
) -> ArticleUploadResponse:
    if db.get(Corpus, str(corpus_id)) is None:
        raise _not_found("Corpus", corpus_id)

    uploads = await _parse_multipart_uploads(request)
    try:
        articles = create_articles(db, corpus_id=corpus_id, uploads=uploads)
    except UnsupportedArticleTypeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ArticleDecodeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DuplicateFilenameError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    for article in articles:
        background_tasks.add_task(
            decompose_article_by_id,
            session_factory,
            article_id=article.id,
            client=client,
            ranker_config=ranker_config,
        )

    return ArticleUploadResponse(article_ids=[UUID(article.id) for article in articles])


@router.get("/articles/{article_id}", response_model=ArticleDetail)
def get_article(article_id: UUID, db: DbSession) -> ArticleDetail:
    article = db.scalar(select(Article).where(Article.id == str(article_id)))
    if article is None:
        raise _not_found("Article", article_id)
    structured = latest_structured_article(db, article_id=article.id)
    return _article_detail(article, structured)


@router.post("/articles/{article_id}/decompose", response_model=StructuredArticleRecord)
def decompose_article_endpoint(
    article_id: UUID,
    db: DbSession,
    client: DecompositionClientDep,
    ranker_config: RankerConfigDep,
) -> StructuredArticleRecord:
    article = db.scalar(select(Article).where(Article.id == str(article_id)))
    if article is None:
        raise _not_found("Article", article_id)

    try:
        structured = decompose_article(
            db,
            article=article,
            client=client,
            ranker_config=ranker_config,
        )
    except (DecompositionError, RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Article decomposition failed: {exc}",
        ) from exc

    return _structured_record(structured)
