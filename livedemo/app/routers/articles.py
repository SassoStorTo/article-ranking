from email import policy
from email.parser import BytesParser
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from livedemo.app.db.models import Article, Corpus
from livedemo.app.deps import get_db
from livedemo.app.schemas import ArticleDetail, ArticleUploadResponse
from livedemo.app.services.ingestion import ArticleDecodeError, ArticleUpload
from livedemo.app.services.ingestion import DuplicateFilenameError
from livedemo.app.services.ingestion import UnsupportedArticleTypeError
from livedemo.app.services.ingestion import create_articles

router = APIRouter(tags=["articles"])


def _not_found(entity: str, entity_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} {entity_id} was not found.",
    )


def _article_detail(article: Article) -> ArticleDetail:
    return ArticleDetail(
        id=UUID(article.id),
        corpus_id=UUID(article.corpus_id),
        filename=article.filename,
        title=article.title,
        body=article.body,
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    db: Session = Depends(get_db),
) -> ArticleUploadResponse:
    if db.get(Corpus, str(corpus_id)) is None:
        raise _not_found("Corpus", corpus_id)

    uploads = await _parse_multipart_uploads(request)
    try:
        articles = create_articles(db, corpus_id=corpus_id, uploads=uploads)
    except UnsupportedArticleTypeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ArticleDecodeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DuplicateFilenameError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ArticleUploadResponse(article_ids=[UUID(article.id) for article in articles])


@router.get("/articles/{article_id}", response_model=ArticleDetail)
def get_article(article_id: UUID, db: Session = Depends(get_db)) -> ArticleDetail:
    article = db.scalar(select(Article).where(Article.id == str(article_id)))
    if article is None:
        raise _not_found("Article", article_id)
    return _article_detail(article)
