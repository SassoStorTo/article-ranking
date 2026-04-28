import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.embed import embed_article_from_clusters, embed_facts


class FakeEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        rows = [float(index + 1) for index, _ in enumerate(texts)]
        return np.array([[value, value + 10.0] for value in rows], dtype=np.float32)


class Float64Embedder:
    def embed(self, texts: list[str]) -> NDArray[np.float64]:
        return np.ones((len(texts), 2), dtype=np.float64)


class OneDimensionalEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        return np.ones((len(texts),), dtype=np.float32)


class NonFiniteEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        embeddings = np.ones((len(texts), 2), dtype=np.float32)
        embeddings[0, 0] = np.nan
        return embeddings


class FailingEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        raise AssertionError("embedder should not be called")


def test_embed_facts_returns_float32_2d_embeddings() -> None:
    embeddings = embed_facts(["first fact", "second fact"], FakeEmbedder())

    assert embeddings.shape == (2, 2)
    assert embeddings.dtype == np.float32
    np.testing.assert_array_equal(
        embeddings,
        np.array([[1.0, 11.0], [2.0, 12.0]], dtype=np.float32),
    )


def test_embed_facts_rejects_empty_input_without_calling_embedder() -> None:
    with pytest.raises(ValueError, match="facts must not be empty"):
        embed_facts([], FailingEmbedder())


def test_embed_facts_rejects_non_float32_output() -> None:
    with pytest.raises(TypeError, match="dtype float32"):
        embed_facts(["fact"], Float64Embedder())  # type: ignore[arg-type]


def test_embed_facts_rejects_non_2d_output() -> None:
    with pytest.raises(ValueError, match="2-D"):
        embed_facts(["fact"], OneDimensionalEmbedder())


def test_embed_facts_rejects_non_finite_output() -> None:
    with pytest.raises(ValueError, match="finite"):
        embed_facts(["fact"], NonFiniteEmbedder())


def test_embed_article_from_clusters_means_unique_covered_clusters() -> None:
    article_ids = ["article-a", "article-b"]
    coverage_matrix = np.array(
        [
            [2, 0, 1],
            [0, 1, 0],
        ],
    )
    cluster_vectors = np.array(
        [
            [1.0, 3.0],
            [100.0, 100.0],
            [5.0, 7.0],
        ],
        dtype=np.float32,
    )

    article_vector = embed_article_from_clusters(
        "article-a",
        article_ids,
        coverage_matrix,
        cluster_vectors,
    )

    np.testing.assert_array_equal(
        article_vector,
        np.array([3.0, 5.0], dtype=np.float32),
    )


def test_embed_article_from_clusters_rejects_unknown_article_id() -> None:
    with pytest.raises(ValueError, match="unknown article_id"):
        embed_article_from_clusters(
            "missing",
            ["article-a"],
            np.array([[1]]),
            np.array([[1.0, 2.0]], dtype=np.float32),
        )


def test_embed_article_from_clusters_rejects_non_2d_coverage_matrix() -> None:
    with pytest.raises(ValueError, match="coverage_matrix must be a 2-D array"):
        embed_article_from_clusters(
            "article-a",
            ["article-a"],
            np.array([1]),
            np.array([[1.0, 2.0]], dtype=np.float32),
        )


def test_embed_article_from_clusters_rejects_non_2d_cluster_vectors() -> None:
    with pytest.raises(ValueError, match="cluster_vectors must be a 2-D array"):
        embed_article_from_clusters(
            "article-a",
            ["article-a"],
            np.array([[1]]),
            np.array([1.0, 2.0], dtype=np.float32),
        )


def test_embed_article_from_clusters_rejects_article_row_mismatch() -> None:
    with pytest.raises(ValueError, match="row count"):
        embed_article_from_clusters(
            "article-a",
            ["article-a", "article-b"],
            np.array([[1]]),
            np.array([[1.0, 2.0]], dtype=np.float32),
        )


def test_embed_article_from_clusters_rejects_cluster_row_mismatch() -> None:
    with pytest.raises(ValueError, match="column count"):
        embed_article_from_clusters(
            "article-a",
            ["article-a"],
            np.array([[1, 0]]),
            np.array([[1.0, 2.0]], dtype=np.float32),
        )


def test_embed_article_from_clusters_rejects_no_covered_clusters() -> None:
    with pytest.raises(ValueError, match="covers no clusters"):
        embed_article_from_clusters(
            "article-a",
            ["article-a"],
            np.array([[0, 0]]),
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        )
