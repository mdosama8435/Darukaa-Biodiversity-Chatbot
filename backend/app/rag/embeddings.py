"""Lightweight ONNX embedding service with strict dimension validation."""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.config import settings


class BaseEmbeddingService(ABC):
    """Abstract contract for text vectorization services."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """
    Compatibility class name retained for existing imports/tests.

    Actual inference uses FastEmbed/ONNX instead of
    sentence-transformers/PyTorch to keep Render memory usage low.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        expected_dimension: Optional[int] = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.expected_dimension = expected_dimension or settings.EMBEDDING_DIMENSION

        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=self.model_name)

        probe = list(self.model.embed(["probe validation"], batch_size=1))

        if not probe:
            raise ValueError("Embedding model returned no vector during validation.")

        self._dimension = len(probe[0])

        if (
            self.expected_dimension is not None
            and self._dimension != self.expected_dimension
        ):
            raise ValueError(
                f"Embedding dimension mismatch: "
                f"configured EMBEDDING_DIMENSION={self.expected_dimension}, "
                f"but model '{self.model_name}' produces vectors of "
                f"dimension {self._dimension}. "
                "Embeddings cannot be silently truncated or padded."
            )

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[List[float]]:
        """Generate dense embeddings using lightweight ONNX inference."""
        if not texts:
            return []

        embeddings = self.model.embed(
            texts,
            batch_size=batch_size,
        )

        return [vec.tolist() for vec in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Generate a single query embedding."""
        clean_q = query.strip()

        if not clean_q:
            raise ValueError("Cannot generate embedding for an empty query string.")

        vec = next(
            self.model.embed(
                [clean_q],
                batch_size=1,
            )
        )

        return vec.tolist()


_embedding_service_instance: Optional[BaseEmbeddingService] = None


def get_embedding_service() -> BaseEmbeddingService:
    """Returns the singleton embedding service instance."""
    global _embedding_service_instance

    if _embedding_service_instance is None:
        _embedding_service_instance = SentenceTransformerEmbeddingService()

    return _embedding_service_instance
