import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from livedemo.app.db.models import Article, StructuredArticle, utc_now
from news_ranker.config import RankerConfig
from news_ranker.decompose import (
    DecompositionClient,
    DecompositionConfig,
    decompose,
)
from news_ranker.schemas import StructuredArticle as NewsRankerStructuredArticle

logger = logging.getLogger(__name__)


class NormalizingDecompositionClient:
    def __init__(self, client: DecompositionClient) -> None:
        self._client = client

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        output = self._client.complete(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return _normalize_decomposition_output(output)


def build_decomposition_config(config: RankerConfig) -> DecompositionConfig:
    return DecompositionConfig(
        model=config.llm_model_name,
        prompt_version=config.prompt_version,
        schema_version=config.schema_version,
    )


def decompose_article(
    db: Session,
    *,
    article: Article,
    client: DecompositionClient,
    ranker_config: RankerConfig,
) -> StructuredArticle:
    decomposition_config = build_decomposition_config(ranker_config)
    structured = decompose(
        {
            "id": article.id,
            "title": article.title,
            "body": article.body,
        },
        NormalizingDecompositionClient(client),
        config=decomposition_config,
    )
    return upsert_structured_article(
        db,
        article_id=article.id,
        structured=structured,
        config=decomposition_config,
    )


def decompose_article_by_id(
    session_factory: sessionmaker[Session],
    *,
    article_id: str,
    client: DecompositionClient,
    ranker_config: RankerConfig,
) -> None:
    with session_factory() as db:
        article = db.get(Article, article_id)
        if article is None:
            return
        try:
            decompose_article(
                db,
                article=article,
                client=client,
                ranker_config=ranker_config,
            )
        except Exception:
            db.rollback()
            logger.exception("Article decomposition failed for %s", article_id)


def upsert_structured_article(
    db: Session,
    *,
    article_id: str,
    structured: NewsRankerStructuredArticle,
    config: DecompositionConfig,
) -> StructuredArticle:
    existing = db.scalar(
        select(StructuredArticle).where(
            StructuredArticle.article_id == article_id,
            StructuredArticle.llm_model == config.model,
            StructuredArticle.prompt_version == config.prompt_version,
            StructuredArticle.schema_version == config.schema_version,
        )
    )
    if existing is None:
        existing = StructuredArticle(
            article_id=article_id,
            llm_model=config.model,
            prompt_version=config.prompt_version,
            schema_version=config.schema_version,
            payload_json=structured.model_dump(mode="json"),
        )
        db.add(existing)
    else:
        existing.payload_json = structured.model_dump(mode="json")
        existing.created_at = utc_now()

    db.commit()
    db.refresh(existing)
    return existing


def latest_structured_article(
    db: Session,
    *,
    article_id: UUID | str,
) -> StructuredArticle | None:
    return db.scalar(
        select(StructuredArticle)
        .where(StructuredArticle.article_id == str(article_id))
        .order_by(StructuredArticle.created_at.desc(), StructuredArticle.id.desc())
        .limit(1)
    )


def _normalize_decomposition_output(output: str) -> str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return output

    if not isinstance(payload, dict):
        return output

    normalized = dict(payload)
    context = normalized.get("context")
    if isinstance(context, str):
        normalized["context"] = [context]
    elif context is None:
        normalized["context"] = []
    elif isinstance(context, list):
        normalized["context"] = [item for item in context if isinstance(item, str)]

    return json.dumps(_jsonable(normalized), ensure_ascii=False)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
