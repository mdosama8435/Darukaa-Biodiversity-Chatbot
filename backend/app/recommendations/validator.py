"""Recommendation Evidence Validator enforcing generic quantitative claim protection and associative language."""

import re
from typing import Any, Dict, List, Optional, Tuple
from app.evidence.schemas import EvidenceItem
from app.recommendations.schemas import RecommendationItem, ExpectedEffect


class RecommendationEvidenceValidator:
    """Validates candidate recommendations against retrieved scientific evidence and enforces safety guardrails."""

    @classmethod
    def soften_language(cls, text: str) -> str:
        """Enforces conservative scientific phrasing in place of unsupported deterministic/causal claims."""
        replacements = [
            (r"\bcauses\b", "is associated with"),
            (r"\bwill increase\b", "may contribute to an increase in"),
            (r"\bwill improve\b", "is expected to enhance"),
            (r"\bguarantees\b", "can support"),
            (r"\bproven to\b", "evidence suggests that it may"),
            (r"\balways\b", "typically under comparable conditions"),
        ]
        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    @classmethod
    def extract_numbers_from_text(cls, text: str) -> List[str]:
        """Extracts percentages, ratios, or numerical improvement ranges (e.g. '19%', '20–45%')."""
        pattern = r"\b(?:\d+(?:\.\d+)?\s*(?:%|percent)|\d+(?:\.\d+)?\s*(?:–|-|to)\s*\d+(?:\.\d+)?\s*(?:%|percent))\b"
        return re.findall(pattern, text, flags=re.IGNORECASE)

    @classmethod
    def validate_quantitative_claim(
        cls,
        candidate_estimate: Optional[str],
        attached_evidence: List[EvidenceItem],
        target_metric: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generic Quantitative Claim Guard (Correction 2).
        
        A quantitative claim is valid ONLY when:
        1. The exact numerical claim exists in retrieved evidence text;
        2. The evidence chunk is directly associated with the claim;
        3. Source metadata is available;
        4. Source identity has been verified;
        5. Context is sufficiently comparable.
        
        Otherwise:
            returns (None, None)
        """
        if not candidate_estimate or not attached_evidence:
            return None, None

        cand_str = str(candidate_estimate).strip().lower()

        # Look across attached evidence items
        for ev in attached_evidence:
            # Check condition 4: Source identity verified
            if not ev.verified_source:
                continue

            # Check condition 3: Source metadata available
            if not ev.source_title or not (ev.doi or ev.url):
                continue

            # Check condition 1: Exact numerical claim exists in evidence text (claim or full text if available)
            ev_claim = (ev.claim or "").lower()
            
            # Normalize dashes and spaces for comparison
            normalized_cand = cand_str.replace("–", "-").replace(" ", "")
            normalized_ev = ev_claim.replace("–", "-").replace(" ", "")

            # If the candidate estimate (or its numbers) appears verbatim in the verified evidence claim
            if normalized_cand in normalized_ev or cand_str in ev_claim:
                # Check condition 5: Context check (metric overlap)
                if target_metric and ev.matched_variables:
                    target_clean = target_metric.lower().strip()
                    if not any(target_clean in mv.lower() for mv in ev.matched_variables):
                        continue

                # Validated!
                source_citation = f"{ev.source_title} ({ev.publication_year or 'n.d.'}), DOI: {ev.doi or ev.url}"
                return candidate_estimate, source_citation

        # Unverified, unsupported, or mismatched
        return None, None

    @classmethod
    def validate_recommendation(
        cls,
        candidate: RecommendationItem,
        all_evidence: List[EvidenceItem],
    ) -> RecommendationItem:
        """Performs comprehensive evidence validation, language softening, and quantitative claim verification."""
        # 1. Soften action and why points
        clean_action = cls.soften_language(candidate.action)
        clean_why = [cls.soften_language(w) for w in candidate.why]
        
        # Soften reasoning explanations
        clean_reasoning = []
        for step in candidate.environmental_reasoning:
            clean_reasoning.append(
                step.model_copy(update={"explanation": cls.soften_language(step.explanation)})
            )

        # 2. Generic Quantitative Claim Guard
        current_est = candidate.expected_effect.quantitative_estimate
        verified_est, verified_source = cls.validate_quantitative_claim(
            candidate_estimate=current_est,
            attached_evidence=candidate.evidence,
            target_metric=candidate.impacted_metrics[0] if candidate.impacted_metrics else None,
        )

        clean_effect_desc = cls.soften_language(candidate.expected_effect.description)
        if verified_est is None and current_est is not None:
            clean_effect_desc = "Quantitative improvement cannot be estimated from the available evidence."

        new_expected_effect = ExpectedEffect(
            description=clean_effect_desc,
            direction=candidate.expected_effect.direction,
            quantitative_estimate=verified_est,
            estimate_source=verified_source,
        )

        # 3. Build comprehensive audit traceability chain
        rel_ids = [step.relationship for step in candidate.environmental_reasoning]
        ev_ids = [ev.evidence_id for ev in candidate.evidence]
        doc_ids = [str(ev.document_id) for ev in candidate.evidence if ev.document_id is not None]
        chunk_ids = [str(ev.chunk_id) for ev in candidate.evidence if ev.chunk_id is not None]
        source_links = [ev.doi or ev.url for ev in candidate.evidence if (ev.doi or ev.url)]

        traceability = {
            "recommendation_id": candidate.recommendation_id,
            "relationship_ids": rel_ids,
            "evidence_ids": ev_ids,
            "document_ids": doc_ids,
            "chunk_ids": chunk_ids,
            "source_references": list(set(source_links)),
        }

        return candidate.model_copy(
            update={
                "action": clean_action,
                "why": clean_why,
                "environmental_reasoning": clean_reasoning,
                "expected_effect": new_expected_effect,
                "traceability": traceability,
            }
        )
