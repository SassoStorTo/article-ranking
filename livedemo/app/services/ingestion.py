import json
from dataclasses import dataclass
from pathlib import PurePath
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from livedemo.app.db.models import Article, StructuredArticle
from news_ranker.config import RankerConfig
from news_ranker.schemas import StructuredArticle as NewsRankerStructuredArticle


class IngestionError(ValueError):
    """Base error for rejected article uploads."""


class UnsupportedArticleTypeError(IngestionError):
    """Raised when an upload is not a supported article file."""


class DuplicateFilenameError(IngestionError):
    """Raised when a filename already exists in the target corpus."""


class ArticleDecodeError(IngestionError):
    """Raised when an upload cannot be decoded as UTF-8 text."""


class StructuredArticleJsonError(IngestionError):
    """Raised when JSON upload content is malformed."""


class StructuredArticleValidationError(IngestionError):
    """Raised when JSON upload content fails structured schema validation."""


@dataclass(frozen=True)
class ArticleUpload:
    filename: str
    content: bytes


@dataclass(frozen=True)
class ArticleUploadResult:
    article: Article
    needs_decomposition: bool


@dataclass(frozen=True)
class _PreparedUpload:
    filename: str
    body: str
    title: str
    kind: Literal["txt", "json"]
    structured: NewsRankerStructuredArticle | None


def derive_title(filename: str, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped if len(stripped) < 200 else PurePath(filename).stem
    return PurePath(filename).stem


def derive_structured_title(
    filename: str, structured: NewsRankerStructuredArticle
) -> str:
    headline = structured.headline_neutral.strip()
    stem = PurePath(filename).stem
    if not headline:
        return stem
    return f"{headline} ({filename})"


def create_articles(
    db: Session,
    *,
    corpus_id: UUID,
    uploads: list[ArticleUpload],
    ranker_config: RankerConfig,
) -> list[ArticleUploadResult]:
    seen_filenames: set[str] = set()
    prepared_uploads: list[_PreparedUpload] = []

    existing_filenames = set(
        db.scalars(
            select(Article.filename).where(Article.corpus_id == str(corpus_id))
        ).all()
    )

    for upload in uploads:
        filename = PurePath(upload.filename).name
        suffix = PurePath(filename).suffix.lower()
        if suffix not in {".txt", ".json"}:
            raise UnsupportedArticleTypeError(
                f"{filename}: unsupported file type {suffix or '(none)'}. "
                "Upload a .txt or .json file."
            )
        if filename in seen_filenames or filename in existing_filenames:
            raise DuplicateFilenameError(f"{filename} already exists in this corpus.")
        seen_filenames.add(filename)

        try:
            body = upload.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArticleDecodeError(
                f"{filename}: could not be decoded as UTF-8 text at byte {exc.start}."
            ) from exc

        if suffix == ".json":
            structured = _validate_structured_article(filename, body)
            prepared_uploads.append(
                _PreparedUpload(
                    filename=filename,
                    body=body,
                    title=derive_structured_title(filename, structured),
                    kind="json",
                    structured=structured,
                )
            )
        else:
            prepared_uploads.append(
                _PreparedUpload(
                    filename=filename,
                    body=body,
                    title=derive_title(filename, body),
                    kind="txt",
                    structured=None,
                )
            )

    articles = [
        Article(
            corpus_id=str(corpus_id),
            filename=prepared.filename,
            title=prepared.title,
            body=prepared.body,
        )
        for prepared in prepared_uploads
    ]
    db.add_all(articles)
    db.flush()

    for article, prepared in zip(articles, prepared_uploads, strict=True):
        if prepared.kind == "json" and prepared.structured is not None:
            structured = prepared.structured.model_copy(
                update={"article_id": article.id}
            )
            db.add(
                StructuredArticle(
                    article_id=article.id,
                    llm_model=ranker_config.llm_model_name,
                    prompt_version=ranker_config.prompt_version,
                    schema_version=ranker_config.schema_version,
                    payload_json=structured.model_dump(mode="json"),
                )
            )

    db.commit()
    results: list[ArticleUploadResult] = []
    for article, prepared in zip(articles, prepared_uploads, strict=True):
        db.refresh(article)
        results.append(
            ArticleUploadResult(
                article=article,
                needs_decomposition=prepared.kind == "txt",
            )
        )
    return results


def _validate_structured_article(
    filename: str,
    body: str,
) -> NewsRankerStructuredArticle:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise StructuredArticleJsonError(
            f"{filename}: malformed JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}."
        ) from exc

    try:
        return NewsRankerStructuredArticle.model_validate(payload)
    except ValidationError as exc:
        first_error = exc.errors()[0]
        loc = ".".join(str(part) for part in first_error.get("loc", ()))
        msg = str(first_error.get("msg", "invalid value"))
        error_type = str(first_error.get("type", "value_error"))
        detail = f"{loc}: {msg} ({error_type})" if loc else f"{msg} ({error_type})"
        raise StructuredArticleValidationError(
            f"{filename}: StructuredArticle schema validation failed: {detail}."
        ) from exc
