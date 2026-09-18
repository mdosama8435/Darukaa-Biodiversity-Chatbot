"""Pydantic schemas for deterministic environmental relationships and state analysis."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RelationshipType(str, Enum):
    """Categorical interaction type between environmental metrics."""
    ASSOCIATED_WITH = "associated_with"
    INFLUENCES = "influences"
    CAN_REDUCE = "can_reduce"
    ENHANCES = "enhances"
    EXACERBATES = "exacerbates"


class RelationshipDirection(str, Enum):
    """Directionality of correlation or functional response."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NON_LINEAR = "non_linear"
    COMPLEX = "complex"


class MetricRelationshipDefinition(BaseModel):
    """Deterministic scientific relationship definition with structured literature provenance."""
    model_config = ConfigDict(extra="ignore")

    relationship_id: str = Field(..., description="Unique slug for the ecological relationship")
    variables: List[str] = Field(..., min_length=2, description="Environmental variables involved in the relationship")
    relationship_type: RelationshipType = Field(default=RelationshipType.ASSOCIATED_WITH)
    direction: RelationshipDirection = Field(default=RelationshipDirection.POSITIVE)
    mechanism: str = Field(..., description="Scientifically described biogeochemical or ecological mechanism")
    evidence_required: bool = Field(default=True, description="Whether retrieval evidence is mandatory to ground this claim")
    
    # Structured provenance (Correction 3)
    evidence_document_ids: List[str] = Field(default_factory=list, description="IDs or slugs of supporting literature documents")
    evidence_chunk_ids: List[str] = Field(default_factory=list, description="IDs or references to supporting chunks")
    source_urls: List[str] = Field(default_factory=list, description="Direct web URLs for scientific citations")
    doi: List[str] = Field(default_factory=list, description="Digital Object Identifiers for peer-reviewed sources")
    publication_titles: List[str] = Field(default_factory=list, description="Formal citations or publication titles")
    
    topics: List[str] = Field(default_factory=list, description="Controlled vocabulary topics associated with this interaction")
    required_variables: List[str] = Field(default_factory=list, description="Variables that MUST be present to activate this relationship")
    practice_keywords: List[str] = Field(default_factory=list, description="Optional keywords that must match context for practice-specific relationships")


class MetricClassification(BaseModel):
    """Context-dependent qualitative classification of an observed metric (Correction 4)."""
    model_config = ConfigDict(extra="ignore")

    variable: str = Field(..., description="Environmental metric key")
    observed_value: Any = Field(..., description="The raw measured value")
    classification: str = Field(..., description="Qualitative category (e.g. depleted, optimal, water-limited)")
    basis: str = Field(
        default="context-dependent heuristic",
        description="Scientific basis; clearly labeled as heuristic unless backed by a specific standard",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit caveats regarding local soil texture, climatic baseline, or crop variations",
    )


class ActiveRelationship(BaseModel):
    """An instantiated relationship grounded in user observations with multi-variable awareness."""
    model_config = ConfigDict(extra="ignore")

    relationship_id: str
    variables_involved: List[str]
    observed_values: Dict[str, Any]
    relationship_type: str
    direction: str
    mechanism: str
    relevance_score: float = Field(ge=0.0, le=1.0, description="Confidence/relevance score based on data completeness and severity")
    evidence_required: bool = True
    is_multi_metric: bool = Field(default=False, description="True if relationship jointly reasons across >= 3 variables")
    activation_reason: Optional[str] = Field(default=None, description="Explicit documented rationale for why this relationship is active in current state")
    scientific_provenance: Dict[str, Any] = Field(default_factory=dict)
