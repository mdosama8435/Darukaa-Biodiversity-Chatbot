"""Topic-Targeted Clarification Engine identifying decision-critical missing variables."""

from typing import Any, Dict, List, Optional
from app.conversation.schemas import (
    MetricStatus,
    ClarificationQuestionItem,
    EnvironmentalContextModel,
)


class ClarificationEngine:
    """Selects targeted, topic-relevant clarifying questions based on the specific ecological problem domain."""

    # Decision-relevant priority mappings by inquiry domain: (variable, priority, question, short_label)
    DOMAIN_PRIORITIES = {
        "biodiversity_decline": [
            ("land_use", 1, "What type of land use or cropping system do you currently have (e.g. continuous wheat monoculture, diversified agroforestry, pasture)?", "current cropping system"),
            ("rainfall", 2, "What is your approximate annual rainfall or general water availability (e.g. low/semi-arid <500 mm, seasonal monsoon)?", "approximate annual rainfall"),
            ("soil_organic_carbon", 3, "Do you have an estimate of your soil organic carbon (SOC) percentage or general soil organic matter level?", "soil organic carbon, if available"),
            ("region", 4, "What geographic region or agro-climatic zone is your land situated in (e.g. semi-arid Bihar)?", "geographic region or agro-climatic zone"),
        ],
        "soil_carbon_decline": [
            ("soil_organic_carbon", 1, "What is your measured soil organic carbon (SOC) level or approximate percentage?", "soil organic carbon, if available"),
            ("land_use", 2, "What cropping system and tillage practices are currently practiced on the land?", "current cropping system"),
            ("rainfall", 3, "What is your average seasonal rainfall or soil moisture availability?", "approximate annual rainfall"),
            ("soil_ph", 4, "Do you have recent soil pH test results?", "soil pH test results"),
        ],
        "water_limitation_drought": [
            ("rainfall", 1, "What is your average annual precipitation or typical drought duration?", "approximate annual rainfall"),
            ("land_use", 2, "What crops or tree species are currently cultivated on the plot?", "current cropping system"),
            ("soil_organic_carbon", 3, "What is your soil organic carbon status to determine water-holding capacity?", "soil organic carbon, if available"),
            ("soil_moisture", 4, "Do you have irrigation access or is production strictly rainfed?", "soil moisture or irrigation access"),
        ],
        "deforestation_habitat_loss": [
            ("deforestation", 1, "What is the historical extent of tree cover loss or canopy clearance on your site?", "historical tree cover loss"),
            ("land_cover", 2, "What is the remaining vegetative cover type (e.g. bare soil, scrubland, fragmented canopy)?", "remaining vegetative cover type"),
            ("rainfall", 3, "What is the typical rainfall intensity in your area to assess erosion vulnerability?", "approximate annual rainfall"),
            ("species_richness", 4, "Are there notable indigenous plant or wildlife species you aim to restore?", "indigenous plant or wildlife species"),
        ],
        "general_restoration": [
            ("land_use", 1, "What type of land use or cropping system is currently in place?", "current cropping system"),
            ("rainfall", 2, "What is the approximate annual rainfall or climatic aridity level?", "approximate annual rainfall"),
            ("soil_organic_carbon", 3, "What is your soil organic carbon (SOC) level?", "soil organic carbon, if available"),
            ("region", 4, "What ecoregion or province is the property located in?", "geographic region or agro-climatic zone"),
        ],
    }

    @classmethod
    def identify_domain(cls, user_message: str) -> str:
        """Determines the primary ecological topic of the user's inquiry."""
        lower = user_message.lower()

        if any(w in lower for w in ["biodiversity", "species", "wildlife", "fauna", "flora", "pollinator"]):
            return "biodiversity_decline"
        elif any(w in lower for w in ["soil carbon", "soc", "soil organic", "soil health", "soil fertility", "compost"]):
            return "soil_carbon_decline"
        elif any(w in lower for w in ["drought", "dry", "water", "irrigation", "rainfall", "moisture", "arid"]):
            return "water_limitation_drought"
        elif any(w in lower for w in ["deforest", "tree", "forest", "clearance", "canopy", "timber"]):
            return "deforestation_habitat_loss"
        return "general_restoration"

    @classmethod
    def generate_clarification_questions(
        cls,
        user_message: str,
        active_context: EnvironmentalContextModel,
        max_questions: int = 3,
    ) -> List[ClarificationQuestionItem]:
        """Formulates targeted clarification questions tailored to the user's problem.
        
        Excludes:
        - Variables already provided with a measured value.
        - Variables already explicitly marked as UNKNOWN by the user.
        - Redundant requests (e.g. land use if crop is already provided, Section 5).
        """
        domain = cls.identify_domain(user_message)
        candidates = cls.DOMAIN_PRIORITIES.get(domain, cls.DOMAIN_PRIORITIES["general_restoration"])

        selected_questions: List[ClarificationQuestionItem] = []

        for candidate in candidates:
            if len(candidate) == 4:
                var_name, priority, q_text, short_lbl = candidate
            else:
                var_name, priority, q_text = candidate[:3]
                short_lbl = var_name.replace("_", " ")

            # Section 5: Check context - is it already provided?
            if var_name in active_context.variables:
                prov = active_context.variables[var_name]
                # If provided with a value, DO NOT re-ask!
                if prov.value is not None:
                    continue
                # If explicitly UNKNOWN in a prior turn, DO NOT badger the user!
                if prov.status == MetricStatus.UNKNOWN:
                    continue

            # Section 5: Do not ask for land use/crop if crop or land use is already established!
            if var_name == "land_use":
                crop_prov = active_context.variables.get("crop")
                if crop_prov and crop_prov.value is not None and crop_prov.status != MetricStatus.UNKNOWN:
                    continue
            elif var_name == "crop":
                lu_prov = active_context.variables.get("land_use")
                if lu_prov and lu_prov.value is not None and lu_prov.status != MetricStatus.UNKNOWN:
                    continue

            # Biodiversity / habitat indicators cross-check
            if var_name == "species_richness":
                hab_prov = active_context.variables.get("habitat_diversity")
                if hab_prov and hab_prov.value is not None and hab_prov.status != MetricStatus.UNKNOWN:
                    continue
            elif var_name == "habitat_diversity":
                sr_prov = active_context.variables.get("species_richness")
                if sr_prov and sr_prov.value is not None and sr_prov.status != MetricStatus.UNKNOWN:
                    continue

            selected_questions.append(
                ClarificationQuestionItem(
                    question=q_text,
                    target_variable=var_name,
                    priority=priority,
                    rationale=f"Decision-relevant for domain '{domain}'",
                    short_label=short_lbl,
                )
            )

            if len(selected_questions) >= max_questions:
                break

        return selected_questions
