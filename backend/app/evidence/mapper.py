"""Evidence Mapper linking retrieved knowledge chunks to active environmental relationships."""

from typing import Any, Dict, List, Optional
from app.environmental.schemas import ActiveRelationship
from app.evidence.schemas import EvidenceItem
from app.evidence.scoring import compute_evidence_score


class EvidenceMapper:
    """Maps vector-retrieved knowledge chunks to active environmental relationships with source verification."""

    @classmethod
    def verify_source(cls, chunk_dict: Dict[str, Any]) -> bool:
        """Verifies source authenticity (Correction 11).
        
        A source is verified if:
        - It has a recognized institutional/peer-reviewed source name.
        - Has a valid DOI or source URL.
        """
        source = str(chunk_dict.get("source") or "").lower()
        doi = chunk_dict.get("doi")
        url = chunk_dict.get("url") or chunk_dict.get("source_url")
        has_authoritative_name = any(k in source for k in ["fao", "ipcc", "research", "journal", "academic"])
        has_identifier = bool(doi or url)
        return has_authoritative_name and has_identifier

    @classmethod
    def map_chunks_to_evidence(
        cls,
        retrieved_chunks: List[Dict[str, Any]],
        active_relationships: List[ActiveRelationship],
        observed_variables: List[str],
    ) -> List[EvidenceItem]:
        """Maps retrieved chunks to evidence items grounded in active relationships.
        
        Args:
            retrieved_chunks: List of chunk dictionaries retrieved from pgvector.
            active_relationships: List of active relationships identified by the analyzer.
            observed_variables: Environmental variables present in user context.
            
        Returns:
            List of structured EvidenceItem objects with transparent scoring and source verification.
        """
        evidence_items: List[EvidenceItem] = []
        seen_chunk_ids = set()

        for chunk in retrieved_chunks:
            chunk_id = chunk.get("chunk_id")
            if chunk_id and chunk_id in seen_chunk_ids:
                continue
            if chunk_id:
                seen_chunk_ids.add(chunk_id)

            content = chunk.get("content") or chunk.get("chunk_text") or ""
            if not content.strip():
                continue

            similarity = float(chunk.get("similarity") or 0.0)
            chunk_vars = chunk.get("variables") or []
            chunk_topics = chunk.get("topics") or []
            source_title = chunk.get("title") or "Scientific Assessment"
            source_org = chunk.get("source") or "Unknown"
            doi = chunk.get("doi")
            url = chunk.get("url") or chunk.get("source_url")
            page_num = chunk.get("page_number")
            section = chunk.get("section")
            doc_id = chunk.get("document_id")

            # Check source verification
            is_verified = cls.verify_source(chunk)

            # Find matching active relationship
            matched_rel: Optional[ActiveRelationship] = None
            for rel in active_relationships:
                rel_vars = set(v.lower() for v in rel.variables_involved)
                chunk_vars_set = set(v.lower() for v in chunk_vars)
                if rel_vars.intersection(chunk_vars_set):
                    matched_rel = rel
                    break

            target_rel_vars = matched_rel.variables_involved if matched_rel else None

            # Compute transparent evidence score
            score_breakdown = compute_evidence_score(
                semantic_similarity=similarity,
                chunk_variables=chunk_vars,
                query_variables=observed_variables,
                active_relationship_variables=target_rel_vars,
                source_name=source_org,
                doi=doi,
            )

            # Extract a concise representative claim sentence from chunk
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
            claim_text = sentences[0] + "." if sentences else content[:200]

            item = EvidenceItem(
                document_id=doc_id,
                chunk_id=chunk_id,
                claim=claim_text,
                source_title=source_title,
                source_organization=source_org,
                publication_year=chunk.get("publication_year"),
                url=url,
                doi=doi,
                page_number=page_num,
                section=section,
                relevance_score=score_breakdown.overall_score,
                supports_relationship=True if score_breakdown.relationship_match > 0 else False,
                matched_variables=chunk_vars,
                matched_topics=chunk_topics,
                verified_source=is_verified,
                score_breakdown=score_breakdown,
            )
            evidence_items.append(item)

        # Sort evidence items by overall score descending
        evidence_items.sort(key=lambda e: e.relevance_score, reverse=True)
        return evidence_items
