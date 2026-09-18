"""Pydantic schemas for evidence-backed environmental recommendations."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.evidence.schemas import EvidenceItem


class TimeHorizon(BaseModel):
    """Ecological maturation phases for intervention outcomes."""
    model_config = ConfigDict(extra="ignore")

    short_term: str = Field(..., description="0-1 years: Immediate soil cover and microbial substrate input")
    medium_term: str = Field(..., description="1-3 years: Root architecture establishment and aggregate formation")
    long_term: str = Field(..., description="3-7+ years: Stabilized organic carbon stocks and faunal recovery")


class ExpectedEffect(BaseModel):
    """Anticipated directional or quantified impact on target metrics (Correction 2)."""
    model_config = ConfigDict(extra="ignore")

    description: str = Field(..., description="Qualitative mechanism of ecological improvement")
    direction: str = Field(default="positive", description="Directional vector: positive, neutral, preventative")
    quantitative_estimate: Optional[str] = Field(
        default=None,
        description="Exact quantitative improvement range if verbatim verified in evidence chunk; otherwise None",
    )
    estimate_source: Optional[str] = Field(
        default=None,
        description="Verifiable source reference for the numerical estimate; otherwise None",
    )


class EnvironmentalReasoningStep(BaseModel):
    """Explicit multi-variable reasoning step connecting metrics to interventions (Correction 7)."""
    model_config = ConfigDict(extra="ignore")

    variables: List[str] = Field(..., min_length=2, description="Metrics jointly analyzed in this step")
    relationship: str = Field(..., description="Relationship slug or interaction description")
    explanation: str = Field(..., description="Step-by-step causal or associative reasoning chain")


class RecommendationItem(BaseModel):
    """Evidence-grounded recommendation with multi-variable reasoning and strict claim validation."""
    model_config = ConfigDict(extra="ignore")

    recommendation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str = Field(..., description="Core intervention title")
    why: List[str] = Field(..., description="Scientific justification bullets")
    environmental_reasoning: List[EnvironmentalReasoningStep] = Field(
        default_factory=list,
        description="Multi-metric reasoning demonstrating joint interactions across >= 3 variables",
    )
    impacted_metrics: List[str] = Field(default_factory=list, description="Target environmental indicators")
    time_horizon: TimeHorizon
    expected_effect: ExpectedEffect
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Grounding evidence chunks")
    confidence: str = Field(default="medium", description="Categorical confidence: high, medium, low, insufficient")
    confidence_factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Explicit breakdown of inputs driving the confidence score",
    )
    limitations: List[str] = Field(default_factory=list, description="Site-specific agronomic/climatic caveats")
    traceability: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full audit chain: recommendation -> relationship -> evidence -> chunk -> document -> URL/DOI",
    )
