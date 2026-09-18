"""Multi-Dimensional Retrieval Query Builder informed by active environmental relationships."""

from typing import Any, Dict, List, Optional
from app.environmental.schemas import ActiveRelationship
from app.models.environmental import EnvironmentalData


class MultiDimensionalQueryBuilder:
    """Constructs focused, multi-variable scientific search queries avoiding naive keyword concatenation."""

    @classmethod
    def build_queries(
        cls,
        environmental_data: Dict[str, Any],
        active_relationships: Optional[List[ActiveRelationship]] = None,
        max_queries: int = 6,
    ) -> List[str]:
        """Synthesizes targeted scientific queries from environmental state and active relationships.
        
        Args:
            environmental_data: Flat or nested dictionary of environmental variables.
            active_relationships: List of active relationships discovered by the analyzer.
            max_queries: Upper bound on generated queries to maintain retrieval focus.
            
        Returns:
            List of targeted, deduplicated scientific queries.
        """
        env = EnvironmentalData.from_flat_or_nested(environmental_data)
        flat = env.get_provided_fields()
        queries: List[str] = []

        # 1. Compound multi-metric relationship queries (prioritize highest relevance)
        rel_queries: List[str] = []
        if active_relationships:
            for rel in active_relationships:
                if rel.is_multi_metric or len(rel.variables_involved) >= 3:
                    vars_str = " ".join([v.replace("_", " ") for v in rel.variables_involved])
                    rel_queries.append(f"{vars_str} biodiversity ecological resilience")
                elif rel.relevance_score >= 0.6:
                    vars_str = " ".join([v.replace("_", " ") for v in rel.variables_involved])
                    rel_queries.append(f"{vars_str} soil biological function")

        # 2. Domain-specific multi-metric queries based on key co-occurring variables
        domain_queries: List[str] = []
        soc = flat.get("soil_organic_carbon")
        rain = flat.get("rainfall")
        land = flat.get("land_use")
        region = flat.get("region")

        # Low SOC + Monoculture / Agriculture -> Soil carbon & microbial diversity
        if soc is not None:
            domain_queries.append("soil organic carbon biodiversity soil health microbial biomass")

        # Low rainfall / drought stress + biodiversity / water availability
        if rain is not None:
            domain_queries.append("water limited agriculture rainfall biodiversity soil moisture retention")

        # Land use monoculture -> diversified cropping & agroforestry
        if land is not None:
            land_str = str(land).lower()
            if any(w in land_str for w in ["monoculture", "wheat", "crop", "continuous", "intensive"]):
                domain_queries.append("diversified cropping systems agroforestry biodiversity soil carbon")
                domain_queries.append("monoculture cropland habitat diversity structural complexity")

        # Semi-arid / Arid region context
        if region is not None:
            region_str = str(region).lower()
            if any(w in region_str for w in ["semi-arid", "arid", "dryland", "bihar"]):
                domain_queries.append("semi-arid dryland agroforestry soil carbon moisture management")

        # Interleave: 1 relationship query, 1 domain query, etc., up to max_queries
        combined: List[str] = []
        max_len = max(len(rel_queries), len(domain_queries))
        for i in range(max_len):
            if i < len(domain_queries):
                combined.append(domain_queries[i])
            if i < len(rel_queries):
                combined.append(rel_queries[i])

        # 3. Clean, normalize, and deduplicate
        seen = set()
        deduped: List[str] = []
        for q in combined:
            normalized = " ".join(q.lower().split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(q.strip())
            if len(deduped) >= max_queries:
                break

        # Fallback if sparse variables
        if not deduped:
            deduped.append("soil organic carbon biodiversity agroforestry ecological restoration")

        return deduped
