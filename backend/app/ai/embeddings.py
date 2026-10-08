from huggingface_hub import InferenceClient

from app.core.config import settings


class EmbeddingClient:
    """Wrapper for Hugging Face embedding generation with batch support."""

    def __init__(self):
        self.client = InferenceClient(
            api_key=settings.HF_TOKEN
        )

    def embed_text(self, text: str) -> list[float]:
        """Generates embedding vector for a single text string."""
        result = self.client.feature_extraction(
            text,
            model=settings.HF_EMBEDDING_MODEL
        )
        return result.tolist() if hasattr(result, 'tolist') else list(result)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for multiple texts."""
        if not texts:
            return []

        embeddings = []
        for text in texts:
            emb = self.embed_text(text)
            embeddings.append(emb)

        return embeddings


_embedding_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    """Returns singleton embedding client instance."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


