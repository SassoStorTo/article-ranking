"""Structured article schemas for decomposed news JSON fixtures."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    """Base model rejecting unknown fields and coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Entity(_StrictModel):
    """Named entity in article decomposition."""

    name: str
    role: str


class Entities(_StrictModel):
    """Entity groups in article decomposition."""

    people: list[Entity]
    organizations: list[Entity]
    locations: list[Entity]


class Event(_StrictModel):
    """Atomic event in article decomposition."""

    id: str
    when: str
    who: list[str]
    what: str
    where: str | None
    why: str | None
    how: str | None
    depends_on: list[str]


class Claim(_StrictModel):
    """Atomic claim in article decomposition."""

    id: str
    statement: str
    type: str
    attributed_to: str


class StructuredArticle(_StrictModel):
    """Structured decomposition for one article."""

    article_id: str | None = None
    headline_neutral: str
    topic: str
    entities: Entities
    events: list[Event]
    claims: list[Claim]
    context: list[str]


def derive_article_id(path_like_id: str | Path) -> str:
    """Derive stable path-like article ID from path or path-like ID."""

    path = Path(path_like_id)
    parts = list(path.with_suffix("").parts)
    if "articles" in parts:
        parts = parts[parts.index("articles") + 1 :]
    return "/".join(parts)


def load_structured_article(
    path: str | Path, article_id: str | None = None
) -> StructuredArticle:
    """Load structured article JSON and set runtime article ID."""

    article_path = Path(path)
    article = StructuredArticle.model_validate_json(
        article_path.read_text(encoding="utf-8")
    )
    runtime_article_id = (
        article_id or article.article_id or derive_article_id(article_path)
    )
    return article.model_copy(update={"article_id": runtime_article_id})
