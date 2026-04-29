from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.select import select_mmr, select_top_score


def test_select_top_score_preserves_objects_and_order() -> None:
    first = object()
    second = object()
    third = object()
    ranking = [first, second, third]

    selected = select_top_score(ranking, 2)

    assert selected == [first, second]
    assert selected[0] is first
    assert selected[1] is second


@pytest.mark.parametrize("m", [-1, 4])
def test_select_top_score_rejects_invalid_m(m: int) -> None:
    with pytest.raises(ValueError, match="m"):
        select_top_score(["a", "b", "c"], m)


def test_select_top_score_rejects_non_integer_m() -> None:
    with pytest.raises(TypeError, match="integer"):
        select_top_score(["a"], 1.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("m", [-1, 4])
def test_select_mmr_rejects_invalid_m(m: int) -> None:
    scores = np.asarray([0.9, 0.8, 0.7], dtype=np.float32)
    embeddings = np.eye(3, dtype=np.float32)

    with pytest.raises(ValueError, match="m"):
        select_mmr(scores, embeddings, m, 0.5)


@pytest.mark.parametrize("lambda_", [-0.1, 1.1, np.inf, np.nan])
def test_select_mmr_rejects_invalid_lambda(lambda_: float) -> None:
    scores = np.asarray([0.9, 0.8], dtype=np.float32)
    embeddings = np.eye(2, dtype=np.float32)

    with pytest.raises(ValueError, match="lambda_"):
        select_mmr(scores, embeddings, 1, lambda_)


@pytest.mark.parametrize(
    ("scores", "embeddings", "error_type", "match"),
    [
        (np.ones((2, 1), dtype=np.float32), np.eye(2, dtype=np.float32), ValueError, "1-D"),
        (np.ones(2, dtype=np.float32), np.ones(2, dtype=np.float32), ValueError, "2-D"),
        (np.ones(3, dtype=np.float32), np.eye(2, dtype=np.float32), ValueError, "row count"),
        (np.asarray([1.0, np.nan], dtype=np.float32), np.eye(2, dtype=np.float32), ValueError, "finite"),
        (np.ones(2, dtype=np.float32), np.asarray([[np.inf], [0.0]], dtype=np.float32), ValueError, "finite"),
        (np.asarray([object()], dtype=object), np.ones((1, 1), dtype=np.float32), TypeError, "numeric"),
        (np.ones(1, dtype=np.float32), np.asarray([[object()]], dtype=object), TypeError, "numeric"),
    ],
)
def test_select_mmr_rejects_invalid_shapes_and_values(
    scores: NDArray[Any],
    embeddings: NDArray[Any],
    error_type: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error_type, match=match):
        select_mmr(scores, embeddings, 1, 0.5)


def test_select_mmr_first_pick_is_highest_score() -> None:
    scores = np.asarray([0.7, 0.9, 0.8], dtype=np.float32)
    embeddings = np.eye(3, dtype=np.float32)

    selected = select_mmr(scores, embeddings, 2, 0.5)

    assert selected[0] == 1


def test_select_mmr_chooses_diverse_item_when_lambda_allows() -> None:
    scores = np.asarray([1.0, 0.99, 0.8], dtype=np.float32)
    embeddings = np.asarray(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    selected = select_mmr(scores, embeddings, 2, 0.5)

    assert selected == [0, 2]


def test_select_mmr_lambda_one_reduces_to_score_order() -> None:
    scores = np.asarray([0.9, 0.9, 1.0, 0.8], dtype=np.float32)
    embeddings = np.asarray(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    selected = select_mmr(scores, embeddings, 4, 1.0)

    assert selected == [2, 0, 1, 3]


@pytest.mark.parametrize(
    "embeddings",
    [
        np.zeros((3, 0), dtype=np.float32),
        np.zeros((3, 2), dtype=np.float32),
    ],
)
def test_select_mmr_zero_width_or_zero_vector_embeddings_reduce_to_score_order(
    embeddings: NDArray[np.float32],
) -> None:
    scores = np.asarray([0.3, 0.9, 0.6], dtype=np.float32)

    selected = select_mmr(scores, embeddings, 3, 0.4)

    assert selected == [1, 2, 0]


def test_select_mmr_uses_lowest_index_tie_breaks() -> None:
    scores = np.asarray([1.0, 1.0, 1.0], dtype=np.float32)
    embeddings = np.eye(3, dtype=np.float32)

    selected = select_mmr(scores, embeddings, 3, 1.0)

    assert selected == [0, 1, 2]
