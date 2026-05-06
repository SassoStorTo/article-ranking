from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
