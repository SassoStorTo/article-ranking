from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


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
