"""Context-dependent heuristic metric classification rules.

In strict compliance with Correction 4:
- Thresholds are explicitly classified as 'context-dependent heuristic'.
- Never presented as universal scientific truths.
- Explicitly documents ecological limitations (e.g. soil texture, climate zone, crop type).
- UNKNOWN values (None) are never coerced to zero or classified as depleted.
"""

from typing import Any, Optional
from app.environmental.schemas import MetricClassification


def classify_metric(variable: str, value: Any) -> Optional[MetricClassification]:
    """Evaluates an environmental observation against context-dependent heuristics.
    
    Returns None if value is None (UNKNOWN != ZERO).
    """
    if value is None:
        return None

    var_key = variable.lower().strip()

    # 1. Soil Organic Carbon (SOC)
    if var_key == "soil_organic_carbon":
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            return None

        if val_float < 0.8:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="depleted_low",
                basis="context-dependent heuristic",
                limitations=[
                    "Sandy soils naturally support lower SOC than clayey soils.",
                    "Arid and semi-arid baseline SOC rarely exceeds 1.0% under natural conditions.",
                    "Local baseline sampling is required before inferring absolute degradation.",
                ],
            )
        elif val_float <= 2.0:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="moderate",
                basis="context-dependent heuristic",
                limitations=[
                    "Sufficient for standard dryland cropping but sub-optimal for aggregate resilience.",
                ],
            )
        else:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="elevated_high",
                basis="context-dependent heuristic",
                limitations=[
                    "High SOC supports robust microbial biomass; maintain continuous residue inputs.",
                ],
            )

    # 2. Rainfall (Annual precipitation in mm)
    elif var_key == "rainfall":
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            # Could be string like "low"
            val_str = str(value).lower()
            if "low" in val_str or "arid" in val_str:
                return MetricClassification(
                    variable=variable,
                    observed_value=value,
                    classification="water_limited_arid_semi_arid",
                    basis="context-dependent heuristic",
                    limitations=[
                        "Categorical description without millimeter quantification.",
                        "Interventions must prioritize water conservation and drought-adapted species.",
                    ],
                )
            return None

        if val_float < 500.0:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="water_limited_arid_semi_arid",
                basis="context-dependent heuristic",
                limitations=[
                    "Precipitation distribution across cropping seasons strongly modifies effective water availability.",
                    "Soil water infiltration capacity dictates effective moisture retention.",
                ],
            )
        elif val_float <= 1000.0:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="sub_humid_moderate",
                basis="context-dependent heuristic",
                limitations=[
                    f"Annual rainfall is {val_float} mm; whether this represents water stress depends on regional and seasonal context.",
                    "Suitable for diversified dryland and rainfed agroforestry systems.",
                ],
            )
        else:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="humid_high",
                basis="context-dependent heuristic",
                limitations=[
                    "Water erosion and nutrient leaching are primary degradation risks.",
                ],
            )

    # 3. Soil pH
    elif var_key == "soil_ph":
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            return None

        if val_float < 5.5:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="acidic_stress",
                basis="context-dependent heuristic",
                limitations=[
                    "Aluminum and proton toxicity inhibit bacterial diversity and legume Rhizobia nodulation.",
                    "Buffering capacity varies significantly with soil organic matter and clay minerology.",
                ],
            )
        elif val_float <= 7.5:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="optimal_neutral",
                basis="context-dependent heuristic",
                limitations=[
                    "Favorable range for broad microbial enzymatic activity and phosphorus bioavailability.",
                ],
            )
        else:
            return MetricClassification(
                variable=variable,
                observed_value=val_float,
                classification="alkaline_stress",
                basis="context-dependent heuristic",
                limitations=[
                    "Micronutrient immobilization (iron, zinc, phosphorus) restricts biological productivity.",
                ],
            )

    # 4. Land Use
    elif var_key == "land_use":
        val_str = str(value).lower().strip()
        if any(w in val_str for w in ["monoculture", "continuous", "intensive"]):
            return MetricClassification(
                variable=variable,
                observed_value=value,
                classification="intensive_simplified_cropping",
                basis="context-dependent heuristic",
                limitations=[
                    "Monoculture farming limits functional ecological niches and subterranean microbial diversity.",
                    "Specific crop species and tillage practices modify the severity of structural disturbance.",
                ],
            )
        elif any(w in val_str for w in ["agroforestry", "polyculture", "diversified", "intercropping"]):
            return MetricClassification(
                variable=variable,
                observed_value=value,
                classification="diversified_system",
                basis="context-dependent heuristic",
                limitations=[
                    "Vegetative structural complexity provides multiple canopy layers and ecological niches.",
                ],
            )

    return None
