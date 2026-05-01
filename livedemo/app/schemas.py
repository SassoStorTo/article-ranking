from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CorpusCreate(BaseModel):
    name: str
    notes: str | None = None


class ArticleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    corpus_id: str
    filename: str
    title: str
    content_sha256: str
    uploaded_at: datetime


class ArticleDetail(ArticleSummary):
    body: str
    structured_payload: dict[str, Any] | None = None


class CorpusSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    notes: str | None
    created_at: datetime
    article_count: int


class CorpusDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    notes: str | None
    created_at: datetime
    articles: list[ArticleSummary]


class UploadedArticles(BaseModel):
    articles: list[ArticleSummary]
