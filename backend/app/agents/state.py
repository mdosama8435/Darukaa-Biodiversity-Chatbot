"""LangGraph state schema for multi-variable environmental reasoning."""

from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict


class EnvironmentalState(TypedDict, total=False):
    """Core state object passed between nodes in the reasoning graph."""

    # 1. User input and conversation context
    user_query: str
    conversation_history: List[Dict[str, Any]]

    # 2. Extracted and validated environmental parameters
    environmental_data: Dict[str, Any]
    missing_fields: List[str]
    completeness_score: float
    status: str  # "ready", "needs_clarification", "insufficient_evidence", "error"
    clarification_questions: List[str]

    # 3. Multi-metric analysis and relationship reasoning
    metric_classifications: List[Dict[str, Any]]
    compound_synthesis: Optional[str]
    metric_relationships: List[Dict[str, Any]]

    # 4. Scientific retrieval and evidence grounding
    retrieval_queries: List[str]
    retrieved_chunks: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]

    # 5. Recommendation synthesis and validation
    candidate_recommendations: List[Dict[str, Any]]
    validated_recommendations: List[Dict[str, Any]]

    # 6. Confidence, limitations, and final structured response
    confidence: Union[str, float]
    confidence_factors: Dict[str, Any]
    limitations: List[str]
    final_response: Dict[str, Any]
    error: Optional[str]

    # 7. Phase 5: Hypothetical what-if scenario simulation fields
    is_scenario: bool
    scenario_query: Optional[str]
    scenario_changes: Optional[List[Dict[str, Any]]]
    scenario_state: Optional[Dict[str, Any]]
    scenario_comparison: Optional[Dict[str, Any]]

