from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from livedemo.app.db.models import Article


class IngestionError(ValueError):
    """Base error for rejected article uploads."""


class UnsupportedArticleTypeError(IngestionError):
    """Raised when an upload is not a plain text article."""


class DuplicateFilenameError(IngestionError):
    """Raised when a filename already exists in the target corpus."""


class ArticleDecodeError(IngestionError):
    """Raised when an upload cannot be decoded as UTF-8 text."""


@dataclass(frozen=True)
class ArticleUpload:
    filename: str
    content: bytes


def derive_title(filename: str, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped if len(stripped) < 200 else PurePath(filename).stem
    return PurePath(filename).stem


def create_articles(
    db: Session,
    *,
    corpus_id: UUID,
    uploads: list[ArticleUpload],
) -> list[Article]:
    seen_filenames: set[str] = set()
    articles: list[Article] = []

    existing_filenames = set(
        db.scalars(
            select(Article.filename).where(Article.corpus_id == str(corpus_id))
        ).all()
    )

    for upload in uploads:
        filename = PurePath(upload.filename).name
        if not filename.lower().endswith(".txt"):
            raise UnsupportedArticleTypeError(f"{filename} is not a .txt file.")
        if filename in seen_filenames or filename in existing_filenames:
            raise DuplicateFilenameError(f"{filename} already exists in this corpus.")
        seen_filenames.add(filename)

        try:
            body = upload.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArticleDecodeError(
                f"{filename} could not be decoded as UTF-8 text."
            ) from exc

        articles.append(
            Article(
                corpus_id=str(corpus_id),
                filename=filename,
                title=derive_title(filename, body),
                body=body,
            )
        )

    db.add_all(articles)
    db.commit()
    for article in articles:
        db.refresh(article)
    return articles
