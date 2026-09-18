"""Semantic retriever querying PostgreSQL + pgvector with metadata filtering and source traceability."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.database.models import KnowledgeDocument, KnowledgeChunk
from app.rag.embeddings import BaseEmbeddingService, get_embedding_service
from app.rag.schemas import KnowledgeSearchRequest, KnowledgeSearchResultItem, KnowledgeSearchResponse


class KnowledgeRetriever:
    """Orchestrates embedding generation, vector similarity search, and metadata filtering."""

    def __init__(self, embedding_service: Optional[BaseEmbeddingService] = None) -> None:
        self.embedding_service = embedding_service or get_embedding_service()

    def search(
        self,
        db: Session,
        request: KnowledgeSearchRequest,
    ) -> KnowledgeSearchResponse:
        """Performs vector similarity search against pgvector with optional metadata filters."""
        query_text = request.query.strip()
        top_k = request.top_k
        min_sim = request.min_similarity or 0.0

        # 1. Generate query embedding with L2 normalization
        query_vector = self.embedding_service.embed_query(query_text)

        # 2. Build pgvector cosine distance expression: 1.0 - (embedding <=> query_vector)
        # Note: pgvector's cosine_distance method computes distance (0.0 = identical, 2.0 = opposite)
        # Cosine similarity for normalized vectors is: 1.0 - distance
        cosine_distance_expr = KnowledgeChunk.embedding.cosine_distance(query_vector)

        # Base query joining KnowledgeChunk with its parent KnowledgeDocument
        query = (
            db.query(KnowledgeChunk, KnowledgeDocument, cosine_distance_expr.label("distance"))
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .filter(KnowledgeChunk.embedding.isnot(None))
        )

        # 3. Apply metadata filters
        if request.source:
            query = query.filter(KnowledgeDocument.source.ilike(request.source.strip()))

        # Execute query ordered by ascending cosine distance (highest similarity first)
        query = query.order_by(cosine_distance_expr.asc())

        # Retrieve candidates
        # Fetch more candidates if client-side tag filtering is needed for JSON column compatibility
        fetch_limit = top_k * 3 if (request.variables or request.topics) else top_k
        rows = query.limit(fetch_limit).all()

        results: List[KnowledgeSearchResultItem] = []
        for chunk, doc, distance in rows:
            # Distance is None if vectors are empty
            dist_val = float(distance) if distance is not None else 1.0
            similarity = round(max(0.0, min(1.0, 1.0 - dist_val)), 4)

            # Enforce minimum similarity threshold
            if similarity < min_sim:
                continue

            # Check variable filter
            chunk_vars = chunk.variables or []
            if request.variables:
                req_vars = set(v.lower() for v in request.variables)
                if not any(v.lower() in req_vars for v in chunk_vars):
                    continue

            # Check topic filter
            chunk_topics = chunk.topics or []
            if request.topics:
                req_topics = set(t.lower() for t in request.topics)
                if not any(t.lower() in req_topics for t in chunk_topics):
                    continue

            results.append(
                KnowledgeSearchResultItem(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    title=doc.title,
                    source=doc.source,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    content=chunk.chunk_text,
                    similarity=similarity,
                    url=doc.source_url,
                    doi=doc.doi,
                    variables=chunk_vars,
                    topics=chunk_topics,
                )
            )

            if len(results) >= top_k:
                break

        return KnowledgeSearchResponse(
            query=query_text,
            results_count=len(results),
            results=results,
        )
