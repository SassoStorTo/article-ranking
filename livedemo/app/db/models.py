from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ExecutionKind(Enum):
    RANK = "rank"
    SELECT = "select"
    COMPARE_PROFILES = "compare_profiles"
    EVALUATE = "evaluate"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EvaluationHelper(Enum):
    TOP_M_OVERLAP = "top_m_overlap"
    RANK_CORRELATION = "rank_correlation"
    COMPONENT_SCORE_TABLE = "component_score_table"
    CLUSTER_INSPECTION_ROWS = "cluster_inspection_rows"
    ANONYMIZED_USER_STUDY_BUNDLE = "anonymized_user_study_bundle"


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]


class Corpus(Base):
    __tablename__ = "corpus"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    articles: Mapped[list[Article]] = relationship(
        back_populates="corpus",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    executions: Mapped[list[Execution]] = relationship(back_populates="corpus")


class Article(Base):
    __tablename__ = "article"
    __table_args__ = (
        UniqueConstraint("corpus_id", "filename", name="uq_article_corpus_filename"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    corpus_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("corpus.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    corpus: Mapped[Corpus] = relationship(back_populates="articles")
    structured_articles: Mapped[list[StructuredArticle]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class StructuredArticle(Base):
    __tablename__ = "structured_article"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "llm_model",
            "prompt_version",
            "schema_version",
            name="uq_structured_article_versions",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    article_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("article.id", ondelete="CASCADE"),
        nullable=False,
    )
    llm_model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    article: Mapped[Article] = relationship(back_populates="structured_articles")


class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    corpus_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("corpus.id"),
        nullable=False,
    )
    kind: Mapped[ExecutionKind] = mapped_column(
        SqlEnum(
            ExecutionKind,
            values_callable=enum_values,
            native_enum=False,
        ),
        nullable=False,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        SqlEnum(
            ExecutionStatus,
            values_callable=enum_values,
            native_enum=False,
        ),
        nullable=False,
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    profiles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    corpus: Mapped[Corpus] = relationship(back_populates="executions")
    results: Mapped[list[ExecutionResult]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evaluation_artifacts: Mapped[list[EvaluationArtifact]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExecutionResult(Base):
    __tablename__ = "execution_result"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile: Mapped[str | None] = mapped_column(String, nullable=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    execution: Mapped[Execution] = relationship(back_populates="results")


class EvaluationArtifact(Base):
    __tablename__ = "evaluation_artifact"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution.id", ondelete="CASCADE"),
        nullable=False,
    )
    helper: Mapped[EvaluationHelper] = mapped_column(
        SqlEnum(
            EvaluationHelper,
            values_callable=enum_values,
            native_enum=False,
        ),
        nullable=False,
    )
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    execution: Mapped[Execution] = relationship(back_populates="evaluation_artifacts")
