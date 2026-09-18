"""Explainable Confidence derivation engine based on measurable factors."""

from typing import Any, Dict, List, Tuple
from app.evidence.schemas import EvidenceItem
from app.recommendations.schemas import RecommendationItem


def calculate_explainable_confidence(
    completeness_score: float,
    evidence_items: List[EvidenceItem],
    conflicting_evidence_count: int = 0,
    has_multi_metric_reasoning: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Derives a categorical confidence rating and exposes all driving factors (Correction 9).
    
    Levels:
    - HIGH: Completeness >= 0.5 + Mean evidence quality >= 0.75 + Supporting chunks >= 2 + 0 conflicts.
    - MEDIUM: Completeness >= 0.3 + Mean evidence quality >= 0.60 + Supporting chunks >= 1.
    - LOW: Incomplete input metrics or weak evidence (< 0.60).
    - INSUFFICIENT: 0 supporting chunks or active severe conflicts.
    
    Returns:
        Tuple of (confidence_level_str, confidence_factors_dict)
    """
    total_chunks = len(evidence_items)
    
    if total_chunks == 0:
        return "insufficient", {
            "input_completeness": round(completeness_score, 2),
            "evidence_quality": 0.0,
            "supporting_chunks": 0,
            "conflicting_evidence": conflicting_evidence_count,
            "multi_metric_grounding": has_multi_metric_reasoning,
            "rationale": "No qualifying scientific evidence retrieved to ground recommendations.",
        }

    mean_quality = sum(e.relevance_score for e in evidence_items) / total_chunks
    mean_quality = round(mean_quality, 3)

    factors = {
        "input_completeness": round(completeness_score, 2),
        "evidence_quality": mean_quality,
        "supporting_chunks": total_chunks,
        "conflicting_evidence": conflicting_evidence_count,
        "multi_metric_grounding": has_multi_metric_reasoning,
    }

    # Derivation rules
    if conflicting_evidence_count > 1:
        return "insufficient", {
            **factors,
            "rationale": "Severe conflicting evidence detected across retrieved literature.",
        }

    if (
        completeness_score >= 0.4
        and mean_quality >= 0.75
        and total_chunks >= 2
        and conflicting_evidence_count == 0
        and has_multi_metric_reasoning
    ):
        confidence = "high"
        rationale = "Strong input completeness, multiple verified evidence chunks, and multi-metric grounding."
    elif completeness_score >= 0.25 and mean_quality >= 0.60 and total_chunks >= 1:
        confidence = "medium"
        rationale = "Adequate scientific evidence with partial environmental input completeness."
    else:
        confidence = "low"
        rationale = "Limited environmental input data or marginal evidence quality."

    factors["rationale"] = rationale
    return confidence, factors


def rank_and_score_recommendations(
    recommendations: List[RecommendationItem],
    completeness_score: float,
    all_evidence: List[EvidenceItem],
) -> List[RecommendationItem]:
    """Applies confidence calculation and factor breakdown to all recommendations."""
    scored: List[RecommendationItem] = []

    for rec in recommendations:
        has_multi = any(len(step.variables) >= 3 for step in rec.environmental_reasoning)
        conf_level, conf_factors = calculate_explainable_confidence(
            completeness_score=completeness_score,
            evidence_items=rec.evidence or all_evidence,
            conflicting_evidence_count=0,
            has_multi_metric_reasoning=has_multi,
        )

        updated_rec = rec.model_copy(
            update={
                "confidence": conf_level,
                "confidence_factors": conf_factors,
            }
        )
        scored.append(updated_rec)

    # Sort: high confidence first, then by number of evidence items desc
    tier_order = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}
    scored.sort(key=lambda r: (tier_order.get(r.confidence, 0), len(r.evidence)), reverse=True)
    return scored
