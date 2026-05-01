from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Article,
    Corpus,
    EvaluationArtifact,
    EvaluationHelper,
    Execution,
    ExecutionKind,
    ExecutionResult,
    ExecutionStatus,
    StructuredArticle,
)
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


def test_execution_models_round_trip_enums_json_and_nullable_fields(
    tmp_path: Path,
) -> None:
    with make_session(tmp_path) as session:
        corpus = Corpus(name="corpus")
        executions = [
            Execution(
                corpus=corpus,
                kind=kind,
                status=status,
                config_json={"threshold": 0.85, "nested": {"enabled": True}},
                profiles=["representative", "rare-facts"],
                m=None,
                started_at=None,
                finished_at=None,
                error=None,
            )
            for kind, status in zip(
                ExecutionKind,
                ExecutionStatus,
                strict=True,
            )
        ]
        result = ExecutionResult(
            execution=executions[0],
            profile=None,
            result_json={"ranking": [{"article_id": "a1", "score": 1.0}]},
        )
        artifact = EvaluationArtifact(
            execution=executions[0],
            helper=EvaluationHelper.TOP_M_OVERLAP,
            params_json={"m": 3, "other_execution_id": "other"},
            payload_json={"jaccard": 0.5, "overlap": ["a1"]},
        )
        session.add_all([*executions, result, artifact])
        session.commit()

        stored = session.scalars(
            select(Execution).where(Execution.id == executions[0].id),
        ).one()
        all_kinds = set(session.scalars(select(Execution.kind)).all())
        all_statuses = set(session.scalars(select(Execution.status)).all())

        assert all_kinds == set(ExecutionKind)
        assert all_statuses == set(ExecutionStatus)
        assert stored.config_json == {
            "threshold": 0.85,
            "nested": {"enabled": True},
        }
        assert stored.profiles == ["representative", "rare-facts"]
        assert stored.m is None
        assert stored.started_at is None
        assert stored.finished_at is None
        assert stored.error is None
        assert stored.results[0].profile is None
        assert stored.results[0].result_json == {
            "ranking": [{"article_id": "a1", "score": 1.0}],
        }
        assert stored.evaluation_artifacts[0].helper is EvaluationHelper.TOP_M_OVERLAP
        assert stored.evaluation_artifacts[0].params_json == {
            "m": 3,
            "other_execution_id": "other",
        }
        assert stored.evaluation_artifacts[0].payload_json == {
            "jaccard": 0.5,
            "overlap": ["a1"],
        }


def test_execution_timing_error_and_all_evaluation_helpers_round_trip(
    tmp_path: Path,
) -> None:
    with make_session(tmp_path) as session:
        started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        finished_at = datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
        execution = Execution(
            corpus=Corpus(name="corpus"),
            kind=ExecutionKind.SELECT,
            status=ExecutionStatus.FAILED,
            config_json={"selection_mode": "mmr"},
            profiles=["representative"],
            m=3,
            started_at=started_at,
            finished_at=finished_at,
            error="boom",
        )
        session.add_all(
            [
                EvaluationArtifact(
                    execution=execution,
                    helper=helper,
                    params_json={"helper": helper.value},
                    payload_json={"ok": True},
                )
                for helper in EvaluationHelper
            ],
        )
        session.commit()

        stored = session.scalars(select(Execution)).one()
        stored_helpers = {artifact.helper for artifact in stored.evaluation_artifacts}

        assert stored.kind is ExecutionKind.SELECT
        assert stored.status is ExecutionStatus.FAILED
        assert stored.m == 3
        assert stored.started_at == started_at
        assert stored.finished_at == finished_at
        assert stored.error == "boom"
        assert stored_helpers == set(EvaluationHelper)


def test_deleting_execution_cascades_to_results_and_evaluation_artifacts(
    tmp_path: Path,
) -> None:
    with make_session(tmp_path) as session:
        execution = Execution(
            corpus=Corpus(name="corpus"),
            kind=ExecutionKind.RANK,
            status=ExecutionStatus.SUCCEEDED,
            config_json={},
            profiles=["representative"],
        )
        session.add_all(
            [
                ExecutionResult(
                    execution=execution,
                    profile="representative",
                    result_json={"ranked": []},
                ),
                EvaluationArtifact(
                    execution=execution,
                    helper=EvaluationHelper.COMPONENT_SCORE_TABLE,
                    params_json={},
                    payload_json={"rows": []},
                ),
            ],
        )
        session.commit()

        session.delete(execution)
        session.commit()

        assert session.scalar(select(func.count()).select_from(Execution)) == 0
        assert session.scalar(select(func.count()).select_from(ExecutionResult)) == 0
        assert session.scalar(select(func.count()).select_from(EvaluationArtifact)) == 0
