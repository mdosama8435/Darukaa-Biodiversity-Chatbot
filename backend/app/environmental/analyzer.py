"""Environmental Relationship Analyzer executing compound multi-metric reasoning."""

from typing import Any, Dict, List, Optional, Tuple
from app.environmental.schemas import ActiveRelationship, MetricClassification
from app.environmental.relationship_graph import EnvironmentalRelationshipGraph, get_relationship_graph
from app.environmental.metric_rules import classify_metric
from app.models.environmental import EnvironmentalData


class EnvironmentalRelationshipAnalyzer:
    """Analyzes environmental observations to discover active compound relationships (>= 3 variables)."""

    def __init__(self, graph: Optional[EnvironmentalRelationshipGraph] = None) -> None:
        self.graph = graph or get_relationship_graph()

    def analyze(
        self,
        environmental_data: Dict[str, Any],
        active_variables: Optional[List[str]] = None,
    ) -> Tuple[List[ActiveRelationship], List[MetricClassification], Dict[str, Any]]:
        """Executes multi-metric relationship analysis on observed environmental data.
        
        Args:
            environmental_data: Dictionary of flattened or nested environmental variables.
            active_variables: Optional list of additional active scenario variables (e.g. uncalibrated deltas).
            
        Returns:
            Tuple of:
            - List[ActiveRelationship]: Discovered active relationships, prioritized by multi-metric compound interactions.
            - List[MetricClassification]: Heuristic classifications with documented limitations.
            - Dict[str, Any]: Analytical summary (compound pressure synthesis, completeness, variable counts).
        """
        # 1. Normalize environmental data into flat dict without coercing None to 0
        env_obj = EnvironmentalData.from_flat_or_nested(environmental_data)
        flat_data = env_obj.to_flat_dict()
        provided_fields = env_obj.get_provided_fields()

        # 2. Run context-dependent classifications for all provided variables
        classifications: List[MetricClassification] = []
        for var, val in provided_fields.items():
            cls_item = classify_metric(var, val)
            if cls_item:
                classifications.append(cls_item)

        observed_vars = list(provided_fields.keys())
        if active_variables:
            for av in active_variables:
                av_clean = str(av).lower().strip()
                if av_clean and av_clean not in observed_vars:
                    observed_vars.append(av_clean)

        # Context string for practice keyword matching
        context_parts = [str(v).lower() for v in flat_data.values() if v is not None]
        if active_variables:
            context_parts.extend(str(av).lower() for av in active_variables if av)
        context_str = " ".join(context_parts)

        # 3. Discover matching relationships from the relationship graph
        all_candidates = self.graph.all_relationships()

        active_relationships: List[ActiveRelationship] = []

        for rel in all_candidates:
            req_vars = [v.lower().strip() for v in (rel.required_variables or rel.variables)]
            
            # Rule 1: ALL required variables MUST be genuinely present in observed_vars
            if not all(v in observed_vars for v in req_vars):
                continue

            # Rule 2: If practice keywords are defined, at least one must match context
            if rel.practice_keywords:
                if not any(kw.lower() in context_str for kw in rel.practice_keywords):
                    continue

            # Section 4 Precondition Evaluation: ph_microbial_structure is scientifically grounded in acidification (pH <= 5.5) / neutral diversity
            if rel.relationship_id == "ph_microbial_structure":
                ph_obs = flat_data.get("soil_ph")
                if ph_obs is not None:
                    try:
                        ph_float = float(ph_obs)
                        # Alkaline pH > 7.5 is outside the domain of FAO 2020 acidification relationship
                        if ph_float > 7.5:
                            continue
                    except (ValueError, TypeError):
                        pass

            matched_vars = [v for v in rel.variables if v.lower().strip() in observed_vars]
            missing_vars = [v for v in rel.variables if v.lower().strip() not in observed_vars]

            # Calculate relevance score: fraction of relationship variables present
            # with bonus for severity of classifications
            base_score = len(matched_vars) / len(rel.variables)
            
            # Boost score if classifications show stress/depletion
            severity_boost = 0.0
            for var in matched_vars:
                var_cls = next((c for c in classifications if c.variable == var), None)
                if var_cls and any(s in var_cls.classification for s in ["depleted", "limited", "stress", "intensive"]):
                    severity_boost += 0.1

            relevance = round(min(1.0, max(0.2, base_score + severity_boost)), 3)
            # Compound interaction requires >= 3 variables to be genuinely present!
            is_multi = len(rel.variables) >= 3 and len(matched_vars) >= 3

            observed_subset = {v: provided_fields.get(v) for v in rel.variables}

            # Generate structured activation reason (Audit Requirement 1)
            if rel.practice_keywords:
                matched_kws = [kw for kw in rel.practice_keywords if kw.lower() in context_str]
                activation_reason = (
                    f"Required driving variables [{', '.join(req_vars)}] observed; "
                    f"management practice matches [{', '.join(matched_kws)}]"
                )
            else:
                activation_reason = (
                    f"Required driving variable(s) [{', '.join(req_vars)}] genuinely present in observation"
                )

            provenance = {
                "document_ids": rel.evidence_document_ids,
                "chunk_ids": rel.evidence_chunk_ids,
                "source_urls": rel.source_urls,
                "doi": rel.doi,
                "publication_titles": rel.publication_titles,
            }

            active_relationships.append(
                ActiveRelationship(
                    relationship_id=rel.relationship_id,
                    variables_involved=rel.variables,
                    observed_values=observed_subset,
                    relationship_type=rel.relationship_type.value,
                    direction=rel.direction.value,
                    mechanism=rel.mechanism,
                    relevance_score=relevance,
                    evidence_required=rel.evidence_required,
                    is_multi_metric=is_multi,
                    activation_reason=activation_reason,
                    scientific_provenance=provenance,
                )
            )

        # Sort active relationships: multi-metric compound relationships first, then by relevance score desc
        active_relationships.sort(key=lambda r: (r.is_multi_metric, r.relevance_score), reverse=True)

        # 4. Construct Compound Multi-Metric Synthesis (Correction 7)
        # Check specifically for the 3-variable compound interaction: SOC + Rainfall + Land Use
        compound_synthesis: Optional[str] = None
        has_soc = "soil_organic_carbon" in provided_fields
        has_rain = "rainfall" in provided_fields
        has_land = "land_use" in provided_fields

        if has_soc and has_rain and has_land:
            soc_val = provided_fields["soil_organic_carbon"]
            rain_val = provided_fields["rainfall"]
            land_val = provided_fields["land_use"]
            reg_val = str(provided_fields.get("region") or "").lower()

            # Determine precipitation contextual description (Bug 5 / Condition 2)
            is_arid = any(k in reg_val for k in ["arid", "semi-arid", "dryland"])
            try:
                rain_num = float(rain_val)
            except (ValueError, TypeError):
                rain_num = None

            if (rain_num is not None and rain_num < 500.0) or is_arid or str(rain_val).lower() == "low":
                precip_clause = f"low precipitation ({rain_val} mm)" if rain_num is not None else f"low precipitation regime ({rain_val})"
                water_stress_clause = "water deficit impairs soil aggregate stability, which suppresses subterranean microbial enzymatic function, while"
            elif rain_num is not None:
                precip_clause = f"annual rainfall of {rain_val} mm (whether this represents water stress depends on regional and seasonal context)"
                water_stress_clause = "moisture dynamics interact with soil aggregate stability, while"
            else:
                precip_clause = f"precipitation level ({rain_val})"
                water_stress_clause = "moisture availability interacts with soil biological function, while"

            compound_synthesis = (
                f"COMPOUND MULTI-METRIC INTERACTION: Observed depleted soil carbon ({soc_val}) "
                f"conjoined with {precip_clause} under intensive cropping ({land_val}) "
                f"creates a compounding ecological interaction: {water_stress_clause} monoculture canopy absence "
                f"deprives the ecosystem of multi-tiered microclimatic buffering. Interventions must simultaneously "
                f"address organic substrate replenishment, root water retention, and structural vegetative complexity."
            )

        summary = {
            "total_observed_variables": len(provided_fields),
            "completeness_score": env_obj.completeness_score(),
            "active_relationships_count": len(active_relationships),
            "multi_metric_relationships_count": sum(1 for r in active_relationships if r.is_multi_metric),
            "compound_synthesis": compound_synthesis,
        }

        return active_relationships, classifications, summary
