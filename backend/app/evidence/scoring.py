"""Transparent evidence scoring mechanism with explicit mathematical weights."""

from typing import Any, Dict, List, Optional
from app.evidence.schemas import EvidenceScoreBreakdown


# Explicit weights documenting the internal evidence quality score (Requirement 10)
# Weight rationale:
# - Semantic relevance (0.35): Foundation of textual similarity between retrieval query and chunk.
# - Metadata relevance (0.25): Verifies deterministic environmental variable tags in the chunk.
# - Relationship match (0.25): Ensures the chunk specifically addresses the active ecological relationship.
# - Source quality (0.15): Authoritative weight (peer-reviewed / intergovernmental reports like FAO/IPCC).
WEIGHT_SEMANTIC = 0.35
WEIGHT_METADATA = 0.25
WEIGHT_RELATIONSHIP = 0.25
WEIGHT_SOURCE_QUALITY = 0.15


def resolve_source_quality(source_name: Optional[str], doi: Optional[str] = None) -> float:
    """Assigns an authoritative source quality weight based on publication type."""
    src = (source_name or "").lower().strip()
    if "fao" in src:
        return 0.95
    elif "ipcc" in src:
        return 0.95
    elif "research" in src or "journal" in src or doi:
        return 0.90
    elif src:
        return 0.75
    return 0.50


def compute_evidence_score(
    semantic_similarity: float,
    chunk_variables: List[str],
    query_variables: List[str],
    active_relationship_variables: Optional[List[str]] = None,
    source_name: Optional[str] = None,
    doi: Optional[str] = None,
) -> EvidenceScoreBreakdown:
    """Computes a multi-factor transparent evidence score.
    
    Args:
        semantic_similarity: Cosine similarity from embedding retrieval [0.0 - 1.0].
        chunk_variables: Controlled vocabulary variables tagged on the chunk.
        query_variables: Environmental variables present in the user inquiry.
        active_relationship_variables: Variables defining the target relationship.
        source_name: Publishing organization or journal.
        doi: Digital Object Identifier.
        
    Returns:
        EvidenceScoreBreakdown containing individual components and the weighted overall score.
    """
    # 1. Semantic relevance
    sem_score = max(0.0, min(1.0, float(semantic_similarity)))

    # 2. Metadata relevance: overlap with user query variables
    clean_chunk_vars = set(v.lower().strip() for v in chunk_variables if v)
    clean_query_vars = set(v.lower().strip() for v in query_variables if v)
    if clean_query_vars:
        meta_score = len(clean_chunk_vars.intersection(clean_query_vars)) / len(clean_query_vars)
    else:
        meta_score = 0.5 if clean_chunk_vars else 0.0
    meta_score = max(0.0, min(1.0, meta_score))

    # 3. Relationship match: overlap with active relationship variables
    if active_relationship_variables:
        clean_rel_vars = set(v.lower().strip() for v in active_relationship_variables if v)
        rel_score = len(clean_chunk_vars.intersection(clean_rel_vars)) / len(clean_rel_vars) if clean_rel_vars else 0.5
    else:
        rel_score = meta_score
    rel_score = max(0.0, min(1.0, rel_score))

    # 4. Source quality weight
    source_score = resolve_source_quality(source_name, doi)

    # 5. Composite score
    overall = (
        WEIGHT_SEMANTIC * sem_score
        + WEIGHT_METADATA * meta_score
        + WEIGHT_RELATIONSHIP * rel_score
        + WEIGHT_SOURCE_QUALITY * source_score
    )
    overall = round(max(0.0, min(1.0, overall)), 4)

    return EvidenceScoreBreakdown(
        semantic_relevance=round(sem_score, 4),
        metadata_relevance=round(meta_score, 4),
        relationship_match=round(rel_score, 4),
        source_quality=round(source_score, 4),
        overall_score=overall,
    )
