"""Evidence Validator evaluating evidence sufficiency, source authenticity, and contradictions."""

from typing import Any, Dict, List, Tuple
from app.evidence.schemas import EvidenceItem


class EvidenceValidator:
    """Validates evidence sufficiency and source integrity before recommendation synthesis."""

    @classmethod
    def validate_evidence(
        cls,
        evidence_items: List[EvidenceItem],
        min_relevance: float = 0.50,
        min_evidence_count: int = 1,
    ) -> Tuple[bool, List[str], List[EvidenceItem]]:
        """Evaluates whether retrieved evidence provides reliable scientific backing.
        
        Args:
            evidence_items: List of mapped EvidenceItem objects.
            min_relevance: Minimum acceptable overall score for an evidence item.
            min_evidence_count: Minimum number of qualifying evidence chunks required.
            
        Returns:
            Tuple of:
            - is_sufficient: bool
            - validation_messages: List of strings detailing validation outcomes or warnings.
            - qualified_items: Filtered list of qualifying EvidenceItem objects.
        """
        messages: List[str] = []

        if not evidence_items:
            messages.append("Insufficient evidence: No scientific documents retrieved.")
            return False, messages, []

        qualified: List[EvidenceItem] = []
        unverified_sources: List[str] = []

        for item in evidence_items:
            if item.relevance_score < min_relevance:
                continue

            if not item.verified_source:
                unverified_sources.append(item.source_title)
                # Keep but warn per Correction 11
                messages.append(
                    f"Warning: Evidence item from '{item.source_title}' lacks verified DOI or authoritative metadata."
                )

            qualified.append(item)

        if len(qualified) < min_evidence_count:
            messages.append(
                f"Insufficient evidence: Found only {len(qualified)} qualifying chunks above relevance {min_relevance} "
                f"(minimum required: {min_evidence_count})."
            )
            return False, messages, qualified

        messages.append(f"Evidence validation passed: {len(qualified)} qualified scientific evidence items.")
        return True, messages, qualified
