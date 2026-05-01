from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Article, Corpus, StructuredArticle
from app.db.session import init_db, make_engine, make_session_factory


def make_session(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'models.sqlite'}")
    init_db(engine)
    session_factory = make_session_factory(engine)
    return session_factory()


def make_article(corpus: Corpus, filename: str = "article.txt") -> Article:
    return Article(
        corpus=corpus,
        filename=filename,
        title="Article title",
        body="Article body",
        content_sha256="a" * 64,
    )


def test_corpus_article_and_structured_article_round_trip(tmp_path: Path) -> None:
    with make_session(tmp_path) as session:
        corpus = Corpus(name="corpus", notes="notes")
        article = make_article(corpus)
        structured = StructuredArticle(
            article=article,
            llm_model="mistral-small-latest",
            prompt_version="v1",
            schema_version="v1",
            payload_json={"claims": [{"text": "claim"}]},
        )
        session.add(structured)
        session.commit()

        stored = session.scalars(select(Corpus).where(Corpus.id == corpus.id)).one()

        assert stored.name == "corpus"
        assert stored.notes == "notes"
        assert stored.created_at is not None
        assert stored.articles[0].filename == "article.txt"
        assert stored.articles[0].uploaded_at is not None
        assert stored.articles[0].structured_articles[0].payload_json == {
            "claims": [{"text": "claim"}],
        }


def test_filename_uniqueness_is_scoped_per_corpus(tmp_path: Path) -> None:
    with make_session(tmp_path) as session:
        first_corpus = Corpus(name="first")
        second_corpus = Corpus(name="second")
        session.add_all(
            [
                make_article(first_corpus, filename="same.txt"),
                make_article(second_corpus, filename="same.txt"),
            ],
        )
        session.commit()

        session.add(make_article(first_corpus, filename="same.txt"))

        with pytest.raises(IntegrityError):
            session.commit()


def test_structured_article_uniqueness_by_article_and_versions(
    tmp_path: Path,
) -> None:
    with make_session(tmp_path) as session:
        corpus = Corpus(name="corpus")
        article = make_article(corpus)
        session.add_all(
            [
                StructuredArticle(
                    article=article,
                    llm_model="mistral-small-latest",
                    prompt_version="v1",
                    schema_version="v1",
                    payload_json={"claims": []},
                ),
                StructuredArticle(
                    article=article,
                    llm_model="mistral-small-latest",
                    prompt_version="v2",
                    schema_version="v1",
                    payload_json={"claims": []},
                ),
            ],
        )
        session.commit()

        session.add(
            StructuredArticle(
                article=article,
                llm_model="mistral-small-latest",
                prompt_version="v1",
                schema_version="v1",
                payload_json={"claims": []},
            ),
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_corpus_cascades_to_articles_and_structured_rows(
    tmp_path: Path,
) -> None:
    with make_session(tmp_path) as session:
        corpus = Corpus(name="corpus")
        article = make_article(corpus)
        structured = StructuredArticle(
            article=article,
            llm_model="mistral-small-latest",
            prompt_version="v1",
            schema_version="v1",
            payload_json={"claims": []},
        )
        session.add(structured)
        session.commit()

        session.delete(corpus)
        session.commit()

        assert session.scalar(select(func.count()).select_from(Corpus)) == 0
        assert session.scalar(select(func.count()).select_from(Article)) == 0
        assert session.scalar(select(func.count()).select_from(StructuredArticle)) == 0
