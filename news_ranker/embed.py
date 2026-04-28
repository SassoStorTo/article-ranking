"""Embedding helpers for structured article facts."""

from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray


class FactEmbedder(Protocol):
    """Protocol for injected local fact embedders."""

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed fact texts."""


class SentenceTransformerEmbedder:
    """Local SentenceTransformer-backed embedder."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Create local SentenceTransformer model."""

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed texts as a two-dimensional float32 array."""

        embeddings = cast(
            Any,
            self._model.encode(texts, convert_to_numpy=True),
        )
        return np.asarray(embeddings, dtype=np.float32)


def embed_facts(facts: list[str], embedder: FactEmbedder) -> NDArray[np.float32]:
    """Embed non-empty fact texts and validate numeric output."""

    if not facts:
        msg = "facts must not be empty"
        raise ValueError(msg)

    embeddings = np.asarray(embedder.embed(facts))
    if embeddings.ndim != 2:
        msg = "fact embeddings must be a 2-D array"
        raise ValueError(msg)
    if embeddings.dtype != np.float32:
        msg = "fact embeddings must have dtype float32"
        raise TypeError(msg)
    if not np.isfinite(embeddings).all():
        msg = "fact embeddings must contain only finite values"
        raise ValueError(msg)
    return embeddings
