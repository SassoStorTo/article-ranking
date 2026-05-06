from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from livedemo.app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExecutionKind(StrEnum):
    RANK = "rank"
    SELECT = "select"
    COMPARE_PROFILES = "compare_profiles"
    EVALUATE = "evaluate"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EvaluationHelper(StrEnum):
    TOP_M_OVERLAP = "top_m_overlap"
    RANK_CORRELATION = "rank_correlation"
    COMPONENT_SCORE_TABLE = "component_score_table"
    CLUSTER_INSPECTION_ROWS = "cluster_inspection_rows"
    ANONYMIZED_USER_STUDY_BUNDLE = "anonymized_user_study_bundle"


class Corpus(Base):
    __tablename__ = "corpus"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    notes: Mapped[str | None] = mapped_column(Text)

    articles: Mapped[list["Article"]] = relationship(
        back_populates="corpus",
        cascade="all, delete-orphan",
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="corpus",
        cascade="all, delete-orphan",
    )


class Article(Base):
    __tablename__ = "article"
    __table_args__ = (UniqueConstraint("corpus_id", "filename"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    corpus_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("corpus.id", ondelete="CASCADE"),
        index=True,
    )
    filename: Mapped[str]
    title: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    corpus: Mapped["Corpus"] = relationship(back_populates="articles")
    structured_articles: Mapped[list["StructuredArticle"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )


class StructuredArticle(Base):
    __tablename__ = "structured_article"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "llm_model",
            "prompt_version",
            "schema_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    article_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("article.id", ondelete="CASCADE"),
        index=True,
    )
    llm_model: Mapped[str]
    prompt_version: Mapped[str]
    schema_version: Mapped[str]
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    article: Mapped["Article"] = relationship(back_populates="structured_articles")


class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    corpus_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("corpus.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[ExecutionKind]
    status: Mapped[ExecutionStatus]
    config_json: Mapped[dict[str, object]] = mapped_column(JSON)
    profiles: Mapped[list[str]] = mapped_column(JSON)
    m: Mapped[int | None]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    corpus: Mapped["Corpus"] = relationship(back_populates="executions")
    results: Mapped[list["ExecutionResult"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
    )
    evaluation_artifacts: Mapped[list["EvaluationArtifact"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class ExecutionResult(Base):
    __tablename__ = "execution_result"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution.id", ondelete="CASCADE"),
        index=True,
    )
    profile: Mapped[str | None]
    result_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    execution: Mapped["Execution"] = relationship(back_populates="results")


class EvaluationArtifact(Base):
    __tablename__ = "evaluation_artifact"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("execution.id", ondelete="CASCADE"),
        index=True,
    )
    helper: Mapped[EvaluationHelper]
    params_json: Mapped[dict[str, object]] = mapped_column(JSON)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    execution: Mapped["Execution"] = relationship(back_populates="evaluation_artifacts")
