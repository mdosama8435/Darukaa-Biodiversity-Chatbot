"""Embedding service abstraction and SentenceTransformer implementation with strict dimension validation."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.config import settings


class BaseEmbeddingService(ABC):
    """Abstract contract for text vectorization services."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the vector dimensionality of this embedding service."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generates a dense vector embedding for a search query."""
        pass


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Generates embeddings using open-source models via sentence-transformers."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        expected_dimension: Optional[int] = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.expected_dimension = expected_dimension or settings.EMBEDDING_DIMENSION

        from sentence_transformers import SentenceTransformer

        # Load the sentence-transformer model
        self.model = SentenceTransformer(self.model_name)

        # Validate actual output dimension against expected dimension
        probe = self.model.encode(["probe validation"], normalize_embeddings=True)
        self._dimension = probe.shape[1]

        if self.expected_dimension is not None and self._dimension != self.expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: configured EMBEDDING_DIMENSION={self.expected_dimension}, "
                f"but model '{self.model_name}' produces vectors of dimension {self._dimension}. "
                "Embeddings cannot be silently truncated or padded. Update configuration to match model."
            )

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embeds a batch of texts with L2 normalization for exact cosine similarity."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string with L2 normalization."""
        # For bge models, query can be prefixed if desired; bge-small-en-v1.5 performs strongly directly
        clean_q = query.strip()
        if not clean_q:
            raise ValueError("Cannot generate embedding for an empty query string.")
        vec = self.model.encode([clean_q], normalize_embeddings=True)[0]
        return vec.tolist()


_embedding_service_instance: Optional[BaseEmbeddingService] = None


def get_embedding_service() -> BaseEmbeddingService:
    """Returns the singleton embedding service instance."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = SentenceTransformerEmbeddingService()
    return _embedding_service_instance
