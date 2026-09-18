"""Constraint-Aware Recommendation Candidate Generator with multi-metric reasoning."""

from typing import Any, Dict, List, Optional
from app.environmental.schemas import ActiveRelationship, MetricClassification
from app.evidence.schemas import EvidenceItem
from app.recommendations.schemas import (
    RecommendationItem,
    TimeHorizon,
    ExpectedEffect,
    EnvironmentalReasoningStep,
)
from app.models.environmental import EnvironmentalData


class RecommendationGenerator:
    """Generates constraint-aware ecological recommendations evaluated against site-specific environmental variables."""

    @classmethod
    def generate_candidates(
        cls,
        environmental_data: Dict[str, Any],
        active_relationships: List[ActiveRelationship],
        evidence_items: List[EvidenceItem],
        classifications: Optional[List[MetricClassification]] = None,
    ) -> List[RecommendationItem]:
        """Synthesizes candidate recommendations grounded in environmental constraints and retrieved evidence.
        
        Args:
            environmental_data: Dictionary of observed environmental variables.
            active_relationships: Discovered relationships (prioritized by multi-metric compound interactions).
            evidence_items: Verified scientific evidence items.
            classifications: Context-dependent heuristic classifications.
            
        Returns:
            List of unvalidated candidate RecommendationItem objects.
        """
        env = EnvironmentalData.from_flat_or_nested(environmental_data)
        flat = env.get_provided_fields()
        classifications = classifications or []

        candidates: List[RecommendationItem] = []

        # Extract primary metrics
        soc = flat.get("soil_organic_carbon")
        rain = flat.get("rainfall")
        land_use = flat.get("land_use")
        region = flat.get("region")
        soil_ph = flat.get("soil_ph")

        reg_str = str(region or "").lower()
        is_arid_region = any(k in reg_str for k in ["arid", "semi-arid", "dryland"])

        is_water_limited = False
        rain_cls = next((c for c in classifications if c.variable == "rainfall"), None)
        if rain_cls and "water_limited" in rain_cls.classification:
            is_water_limited = True
        elif is_arid_region:
            is_water_limited = True
        elif rain is not None:
            try:
                if float(rain) < 500.0:
                    is_water_limited = True
            except (ValueError, TypeError):
                if any(k in str(rain).lower() for k in ["low", "arid", "drought"]):
                    is_water_limited = True

        is_low_soc = False
        soc_cls = next((c for c in classifications if c.variable == "soil_organic_carbon"), None)
        if soc_cls and "depleted" in soc_cls.classification:
            is_low_soc = True
        elif soc is not None:
            try:
                if float(soc) < 1.0:
                    is_low_soc = True
            except (ValueError, TypeError):
                pass

        is_monoculture = False
        if land_use:
            lu_str = str(land_use).lower()
            if any(w in lu_str for w in ["monoculture", "continuous", "wheat", "intensive"]):
                is_monoculture = True

        # ---------------------------------------------------------------------
        # Candidate 1: Diversified Cropping & Agroforestry Integration
        # (Directly addresses SOC + Rainfall + Land Use joint compound pressure)
        # ---------------------------------------------------------------------
        if is_monoculture or is_low_soc:
            # Action title framed generically per Correction 5
            action_title = (
                "Agroforestry Integration with Drought-Compatible Woody Species and Crop Diversification"
                if is_water_limited
                else "Agroforestry Integration and Diversified Cropping System Transition"
            )

            why_points = [
                "Continuous monoculture depletes soil organic carbon stocks and destroys vertical ecological niches.",
                "Perennial woody root systems enhance hydraulic conductivity, facilitating water infiltration into subsoil horizons.",
                "Multi-tiered vegetative canopies provide thermal buffering, reducing evaporation under temperature stress.",
            ]

            # Genuinely present variables among driving set (Condition 1: Never artificially add a third variable)
            compound_vars = []
            if soc is not None:
                compound_vars.append("soil_organic_carbon")
            if rain is not None:
                compound_vars.append("rainfall")
            if land_use is not None:
                compound_vars.append("land_use")

            if len(compound_vars) >= 3:
                reasoning_explanation = (
                    "Depleted soil organic carbon combined with precipitation dynamics under annual monoculture creates "
                    "cascading stress: lack of root diversity limits soil macro-aggregate formation, precipitating "
                    "moisture deficits that arrest microbial enzymatic mineralization. Transitioning to agroforestry "
                    "simultaneously restores organic substrate inputs and deep-root water channels."
                )
                rel_id = "soc_rainfall_monoculture_stress"
                step1_vars = compound_vars[:3]
            elif len(compound_vars) == 2:
                reasoning_explanation = (
                    f"Observed interaction between {' and '.join(compound_vars)} highlights the need for structural diversification. "
                    "Transitioning toward diversified agroforestry mitigates biological degradation."
                )
                rel_id = "pairwise_environmental_interaction"
                step1_vars = compound_vars
            else:
                reasoning_explanation = (
                    "Observed simplified land management constrains biological niches. "
                    "Vegetative diversification improves organic residue diversity and micro-refugia."
                )
                rel_id = "pairwise_environmental_interaction"
                step1_vars = [compound_vars[0] if compound_vars else "land_use", "habitat_diversity"]

            reasoning_steps = [
                EnvironmentalReasoningStep(
                    variables=step1_vars,
                    relationship=rel_id,
                    explanation=reasoning_explanation,
                ),
                EnvironmentalReasoningStep(
                    variables=["land_use", "habitat_diversity", "species_richness"],
                    relationship="land_use_habitat_diversity",
                    explanation=(
                        "Replacing single-layer monoculture with multi-strata perennial cover creates heterogeneous "
                        "micro-refugia, increasing beneficial arthropod and avian predator populations."
                    ),
                ),
            ]

            limitations = [
                "Species selection requires local agronomic and ecological validation; species must be adapted to local water table and salinity.",
                "Initial tree sapling establishment requires protected moisture management during the first 1-2 dry seasons.",
            ]
            if is_water_limited:
                limitations.append(
                    "High-water-demand tree species must be avoided in semi-arid conditions to prevent competitive water depletion with understory crops."
                )

            # Link matching evidence
            matched_evidence = [
                e for e in evidence_items
                if any(v in e.matched_variables for v in ["soil_organic_carbon", "land_use", "species_richness", "soil_moisture"])
            ][:4]

            cand1 = RecommendationItem(
                action=action_title,
                why=why_points,
                environmental_reasoning=reasoning_steps,
                impacted_metrics=["soil_organic_carbon", "species_richness", "habitat_diversity", "soil_moisture"],
                time_horizon=TimeHorizon(
                    short_term="0-1 years: Establishment of drought-adapted tree lines, cover crops, and baseline mulching.",
                    medium_term="1-3 years: Fine-root biomass accumulation, improved infiltration, and macrofauna recovery.",
                    long_term="3-7+ years: Stabilized macro-aggregate soil carbon stocks and multi-trophic biodiversity resilience.",
                ),
                expected_effect=ExpectedEffect(
                    description="Evidence suggests positive improvement in soil organic carbon stocks and taxonomic richness.",
                    direction="positive",
                    quantitative_estimate=None,  # Handled generically by EvidenceValidator
                    estimate_source=None,
                ),
                evidence=matched_evidence,
                limitations=limitations,
            )
            candidates.append(cand1)

        # ---------------------------------------------------------------------
        # Candidate 2: Continuous Soil Cover & Residue Retention
        # (Addresses SOC + Moisture retention + Thermal stress)
        # ---------------------------------------------------------------------
        if is_low_soc or is_water_limited:
            cand2 = RecommendationItem(
                action="Continuous Organic Residue Retention and Surface Mulching",
                why=[
                    "Retaining crop residues shields the mineral soil surface from direct solar radiation and raindrop kinetic impact.",
                    "Slow decomposition of surface biomass continuously supplies labile carbon to epigeic earthworms and fungi.",
                    "Reduces soil surface evaporation, maintaining volumetric root-zone moisture during dry intervals.",
                ],
                environmental_reasoning=[
                    EnvironmentalReasoningStep(
                        variables=["soil_organic_carbon", "soil_moisture"],
                        relationship="temp_soil_carbon_oxidation",
                        explanation=(
                            "Surface residue mulch acts as thermal insulation, mitigating extreme topsoil heating that "
                            "accelerates heterotrophic oxidation of soil organic matter, while simultaneously slowing moisture loss."
                        ),
                    ),
                ],
                impacted_metrics=["soil_organic_carbon", "soil_moisture", "species_richness"],
                time_horizon=TimeHorizon(
                    short_term="0-6 months: Suppression of evaporative soil moisture loss and surface crust formation.",
                    medium_term="6-24 months: Increased microbial biomass carbon and improved aggregate water stability.",
                    long_term="2-5 years: Elevated topsoil organic matter horizons and fungal-to-bacterial biomass ratios.",
                ),
                expected_effect=ExpectedEffect(
                    description="Associated with enhanced soil moisture retention and microbial biomass protection.",
                    direction="positive",
                    quantitative_estimate=None,
                    estimate_source=None,
                ),
                evidence=[
                    e for e in evidence_items
                    if any(v in e.matched_variables for v in ["soil_organic_carbon", "soil_moisture", "rainfall"])
                ][:3],
                limitations=[
                    "Residue retention requires specialized no-till seeding equipment to avoid sowing blockage.",
                    "In termite-dense semi-arid areas, decomposition rates must be monitored.",
                ],
            )
            candidates.append(cand2)

        return candidates
