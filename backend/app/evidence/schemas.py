"""Evidence subsystem schemas representing grounded scientific claims and scoring."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvidenceScoreBreakdown(BaseModel):
    """Transparent breakdown of multi-factor evidence quality scoring."""
    model_config = ConfigDict(extra="ignore")

    semantic_relevance: float = Field(ge=0.0, le=1.0, description="Cosine similarity from vector retrieval")
    metadata_relevance: float = Field(ge=0.0, le=1.0, description="Match ratio of query/state variables in chunk tags")
    relationship_match: float = Field(ge=0.0, le=1.0, description="Alignment with active environmental relationship")
    source_quality: float = Field(ge=0.0, le=1.0, description="Tiered weighting based on authoritative peer review")
    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted composite evidence score")


class EvidenceItem(BaseModel):
    """Factual evidence grounded in an authoritative scientific document chunk."""
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    claim: str = Field(..., description="Verbatim or core claim extracted from the chunk")
    source_title: str
    source_organization: str
    publication_year: Optional[int] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    supports_relationship: bool = True
    matched_variables: List[str] = Field(default_factory=list)
    matched_topics: List[str] = Field(default_factory=list)
    verified_source: bool = Field(default=False, description="Whether source metadata and DOI/URL have been verified")
    score_breakdown: Optional[EvidenceScoreBreakdown] = None
