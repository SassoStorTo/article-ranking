from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdResponse(ApiSchema):
    id: UUID


class TimestampFields(ApiSchema):
    created_at: datetime


class HealthResponse(ApiSchema):
    ok: bool


class ErrorDetail(ApiSchema):
    message: str


class ValidationErrorItem(ApiSchema):
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(ApiSchema):
    detail: str | ErrorDetail | list[ValidationErrorItem]


class CorpusCreate(ApiSchema):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None


DecompositionStatus = Literal["not_started", "decomposed"]


class StructuredArticleRecord(ApiSchema):
    id: UUID
    article_id: UUID
    llm_model: str
    prompt_version: str
    schema_version: str
    payload_json: dict[str, Any]
    created_at: datetime


class CorpusSummary(TimestampFields):
    id: UUID
    name: str
    notes: str | None
    article_count: int


class ArticleSummary(ApiSchema):
    id: UUID
    corpus_id: UUID
    filename: str
    title: str
    body_length: int
    decomposition_status: DecompositionStatus
    uploaded_at: datetime


class ArticleDetail(ApiSchema):
    id: UUID
    corpus_id: UUID
    filename: str
    title: str
    body: str
    decomposition_status: DecompositionStatus
    structured_article: StructuredArticleRecord | None
    uploaded_at: datetime


class ArticleUploadResponse(ApiSchema):
    article_ids: list[UUID]


class CorpusDetail(TimestampFields):
    id: UUID
    name: str
    notes: str | None
    articles: list[ArticleSummary]
