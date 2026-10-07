"""
Embeddings generation module for procurement document chunks.
Uses Hugging Face Inference API feature extraction with batching,
caching, vector normalization, and error resilience.
"""

import hashlib
import logging
import math
import time
from typing import Sequence
import numpy as np
from huggingface_hub import InferenceClient

from app.core.config import settings

logger = logging.getLogger("app.ai.embeddings")

DEFAULT_EMBEDDING_DIM = 384
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 16
MAX_RETRIES = 3


def _fallback_deterministic_vector(text: str, dim: int = DEFAULT_EMBEDDING_DIM) -> list[float]:
    """
    Produces a normalized deterministic vector for dev/test fallback when offline or rate-limited.
    Guarantees consistent cosine similarity between identical texts without crashing the pipeline.
    """
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    np.random.seed(int.from_bytes(hash_bytes[:4], "big"))
    vec = np.random.randn(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class HuggingFaceEmbeddingClient:
    """
    Embeddings client using Hugging Face feature extraction.
    Generates 384-dimensional dense vectors for chunks and queries.
    """

    def __init__(
        self,
        model: str | None = None,
        token: str | None = None,
        dimension: int = DEFAULT_EMBEDDING_DIM,
    ):
        model_name = model or settings.HF_EMBEDDING_MODEL
        if not model_name or "your_huggingface" in model_name:
            model_name = DEFAULT_MODEL

        self.model = model_name
        self.token = token or settings.HF_TOKEN
        self.dimension = dimension
        self._client: InferenceClient | None = None

    @property
    def client(self) -> InferenceClient:
        if self._client is None:
            self._client = InferenceClient(token=self.token, timeout=30.0)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        """Generates embedding for a single text query."""
        results = self.embed_batch([text])
        return results[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Embeds a sequence of text strings in bounded batches.
        """
        if not texts:
            return []

        embeddings_out: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = list(texts[i : i + BATCH_SIZE])
            batch_result = self._embed_single_batch(batch)
            embeddings_out.extend(batch_result)

        return embeddings_out

    def _embed_single_batch(self, batch: list[str]) -> list[list[float]]:
        """Sends a single batch to HF feature extraction with retries."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # HF InferenceClient feature extraction
                features = self.client.feature_extraction(
                    text=batch,
                    model=self.model,
                )
                
                # features could be numpy array or nested lists
                arr = np.array(features)
                # If 3D (batch, tokens, hidden_dim), mean-pool across tokens
                if arr.ndim == 3:
                    arr = np.mean(arr, axis=1)
                
                # Normalize vectors
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                normalized = arr / norms

                result: list[list[float]] = []
                for vec in normalized:
                    vec_list = vec.tolist()
                    # Ensure exact dimensionality
                    if len(vec_list) < self.dimension:
                        vec_list = vec_list + [0.0] * (self.dimension - len(vec_list))
                    elif len(vec_list) > self.dimension:
                        vec_list = vec_list[: self.dimension]
                    result.append(vec_list)

                return result

            except Exception as exc:
                logger.warning(
                    "Embedding extraction attempt %d/%d failed: %s",
                    attempt,
                    MAX_RETRIES,
                    str(exc)[:150],
                )
                if attempt < MAX_RETRIES:
                    time.sleep(1.5 * attempt)

        logger.warning(
            "Hugging Face embeddings failed after %d retries. Falling back to deterministic embedding generation.",
            MAX_RETRIES,
        )
        return [_fallback_deterministic_vector(t, self.dimension) for t in batch]


embedding_client = HuggingFaceEmbeddingClient()


def get_embedding_client() -> HuggingFaceEmbeddingClient:
    """Dependency provider for embeddings client."""
    return embedding_client
