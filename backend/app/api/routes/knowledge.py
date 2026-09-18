"""API routes for scientific knowledge search and document inspection."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import KnowledgeDocument, KnowledgeChunk
from app.rag.retriever import KnowledgeRetriever
from app.rag.schemas import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    DocumentSummaryItem,
)

router = APIRouter(prefix="/knowledge", tags=["Scientific Knowledge"])
_retriever = KnowledgeRetriever()


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
) -> KnowledgeSearchResponse:
    """Executes semantic similarity search against pgvector knowledge store with optional metadata filtering.
    
    Returns genuine retrieved evidence chunks with source provenance.
    Never fabricates fallback responses or synthetic similarity scores.
    """
    try:
        response = _retriever.search(db=db, request=request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge retrieval error: {str(e)}",
        ) from e


@router.get("/documents", response_model=List[DocumentSummaryItem])
def list_documents(
    db: Session = Depends(get_db),
) -> List[DocumentSummaryItem]:
    """Returns metadata for all registered and indexed scientific documents."""
    docs = db.query(KnowledgeDocument).order_by(KnowledgeDocument.id.desc()).all()
    summaries: List[DocumentSummaryItem] = []

    for doc in docs:
        chunk_count = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).count()
        summaries.append(
            DocumentSummaryItem(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                document_type=doc.document_type,
                publication_year=doc.publication_year,
                authors=doc.authors if isinstance(doc.authors, list) else ([doc.authors] if doc.authors else []),
                url=doc.source_url,
                doi=doc.doi,
                license=doc.license,
                chunk_count=chunk_count,
                variables=doc.variables or [],
                topics=doc.topics or [],
            )
        )

    return summaries


@router.get("/documents/{document_id}", response_model=DocumentSummaryItem)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentSummaryItem:
    """Retrieves metadata and chunk count for a specific scientific document."""
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scientific document with ID {document_id} not found.",
        )

    chunk_count = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).count()
    return DocumentSummaryItem(
        id=doc.id,
        title=doc.title,
        source=doc.source,
        document_type=doc.document_type,
        publication_year=doc.publication_year,
        authors=doc.authors if isinstance(doc.authors, list) else ([doc.authors] if doc.authors else []),
        url=doc.source_url,
        doi=doc.doi,
        license=doc.license,
        chunk_count=chunk_count,
        variables=doc.variables or [],
        topics=doc.topics or [],
    )
