"""Pydantic schemas for the scientific knowledge retrieval system."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class DocumentMetadata(BaseModel):
    """Metadata describing an authoritative scientific document."""
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=1, description="Title of the publication or assessment")
    source: str = Field(..., min_length=1, description="Publishing organization or institution (e.g. FAO, IPCC)")
    document_type: str = Field(default="report", description="Type of document (e.g. report, paper, summary)")
    publication_year: Optional[int] = Field(default=None, ge=1800, le=2100, description="Year of publication")
    authors: List[str] = Field(default_factory=list, description="Author names or research body")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier (DOI) if assigned")
    journal: Optional[str] = Field(default=None, description="Journal or publisher name")
    url: Optional[str] = Field(default=None, description="Official publication URL or persistent handle")
    license: Optional[str] = Field(default=None, description="Access/usage license (e.g. CC BY-NC-SA 3.0, Open Access)")
    geographic_scope: Optional[str] = Field(default="global", description="Ecoregion or geographical scope")
    topics: List[str] = Field(default_factory=list, description="Associated high-level ecological topics")
    variables: List[str] = Field(default_factory=list, description="Associated environmental variables")


class ProcessedChunk(BaseModel):
    """A scientifically meaningful chunk of text with structural and semantic tags."""
    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1, description="Chunk text content")
    chunk_index: int = Field(..., ge=0, description="Sequential index within the document")
    chunk_hash: str = Field(..., min_length=16, description="Deterministic SHA-256 hash for deduplication")
    page_number: Optional[int] = Field(default=None, ge=1, description="Source document page number if available")
    section: Optional[str] = Field(default=None, description="Section heading or structural context")
    topics: List[str] = Field(default_factory=list, description="Tagged ecological topics")
    variables: List[str] = Field(default_factory=list, description="Tagged environmental variables")
    token_count: Optional[int] = Field(default=None, ge=0, description="Estimated token length")


class KnowledgeSearchRequest(BaseModel):
    """Search request against the scientific knowledge store."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, description="Natural language scientific inquiry")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of chunks to retrieve")
    source: Optional[str] = Field(default=None, description="Filter by source organization (e.g. 'FAO', 'IPCC')")
    variables: Optional[List[str]] = Field(default=None, description="Filter chunks matching any of these variables")
    topics: Optional[List[str]] = Field(default=None, description="Filter chunks matching any of these topics")
    min_similarity: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold between 0.0 and 1.0",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Search query cannot be empty or whitespace only.")
        return trimmed


class KnowledgeSearchResultItem(BaseModel):
    """Individual retrieved evidence chunk with source traceability."""
    model_config = ConfigDict(extra="ignore")

    chunk_id: int = Field(..., description="Unique database identifier for the chunk")
    document_id: int = Field(..., description="Parent document identifier")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Publishing organization")
    page_number: Optional[int] = Field(default=None, description="Page number where chunk appears")
    section: Optional[str] = Field(default=None, description="Section heading")
    content: str = Field(..., description="Exact textual excerpt from the source")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Computed cosine similarity score")
    url: Optional[str] = Field(default=None, description="Direct URL to source document")
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    variables: List[str] = Field(default_factory=list, description="Associated environmental variables")
    topics: List[str] = Field(default_factory=list, description="Associated ecological topics")


class KnowledgeSearchResponse(BaseModel):
    """Complete response payload for a semantic search operation."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="The query evaluated")
    results_count: int = Field(..., ge=0, description="Total number of results returned")
    results: List[KnowledgeSearchResultItem] = Field(default_factory=list)


class DocumentSummaryItem(BaseModel):
    """Summary of an ingested scientific document."""
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    source: str
    document_type: str
    publication_year: Optional[int] = None
    authors: Optional[List[str]] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    license: Optional[str] = None
    chunk_count: int = 0
    variables: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
