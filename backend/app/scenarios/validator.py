"""Scenario Plausibility & Boundary Validator.

Validates that hypothetical changes satisfy physical, agronomic, and ecological limits.
Rejects impossible values (e.g., negative precipitation, pH > 14), contradictory changes,
and ensures outcome metrics are not specified as direct interventions.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.scenarios.schemas import ScenarioChange, ScenarioType


ALLOWED_VARIABLES = {
    "soil_organic_carbon",
    "soil_ph",
    "soil_moisture",
    "temperature",
    "rainfall",
    "land_use",
    "land_cover",
    "species_richness",
    "habitat_diversity",
    "pollution",
    "deforestation",
    "region",
}

OUTCOME_METRICS = {
    "species_richness",
    "habitat_diversity",
    "biodiversity",
}


class ScenarioValidator:
    """Enforces physical bounds, prevents contradictory deltas, and validates unit plausibility."""

    @classmethod
    def validate_changes(
        cls,
        changes: List[ScenarioChange],
        baseline: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """Validates a list of ScenarioChange specifications.
        
        Returns:
            Tuple of:
            - is_valid: bool
            - error_messages: List[str]
        """
        if not changes:
            return False, ["No scenario changes were provided to simulate."]

        errors: List[str] = []
        seen_vars = set()

        for idx, ch in enumerate(changes, start=1):
            var_name = ch.variable.lower().strip()

            # 1. Variable domain check
            if var_name not in ALLOWED_VARIABLES:
                errors.append(f"Change #{idx}: Variable '{ch.variable}' is not a recognized environmental parameter.")
                continue

            # 2. Outcome metric check (Cannot directly set outcome metrics as interventions)
            if var_name in OUTCOME_METRICS:
                errors.append(
                    f"Change #{idx}: '{ch.variable}' is an ecosystem outcome metric rather than a direct management intervention. "
                    "Please specify an intervention practice (e.g., intercropping, agroforestry, reduced tillage, cover crops)."
                )
                continue

            # 3. Contradictory changes check (same variable specified multiple times)
            if var_name in seen_vars:
                errors.append(f"Change #{idx}: Contradictory changes detected for '{ch.variable}'. A variable cannot have multiple targets in one scenario.")
            seen_vars.add(var_name)

            # 4. No-op check (scenario value equals baseline value)
            if ch.baseline_value is not None and ch.scenario_value is not None and ch.baseline_value == ch.scenario_value:
                errors.append(f"Change #{idx}: Scenario value for '{ch.variable}' ({ch.scenario_value}) is identical to baseline (no-op change).")

            # 5. Numerical physical boundary checks
            val = ch.scenario_value
            if ch.change_type == ScenarioType.RELATIVE_CHANGE or ch.unit in ("percent", "%"):
                if isinstance(ch.change_value, (int, float)):
                    if var_name == "rainfall" and ch.change_value < -100.0:
                        errors.append(f"Change #{idx}: Rainfall reduction cannot exceed 100% ({ch.change_value}%).")
                    elif ch.change_value == 0:
                        errors.append(f"Change #{idx}: Relative change for '{ch.variable}' is 0% (no-op change).")

            if isinstance(val, (int, float)):
                # Rainfall
                if var_name == "rainfall":
                    if val < 0.0:
                        errors.append(f"Change #{idx}: Negative rainfall ({val} mm) is physically impossible.")
                    elif val > 10000.0:
                        errors.append(f"Change #{idx}: Rainfall value ({val} mm) exceeds plausible terrestrial boundaries (>10,000 mm).")

                # Soil pH
                elif var_name == "soil_ph":
                    if val < 0.0 or val > 14.0:
                        errors.append(f"Change #{idx}: Soil pH ({val}) is invalid. The standard logarithmic scale is bounded between 0.0 and 14.0.")

                # Soil Moisture
                elif var_name == "soil_moisture":
                    if val < 0.0 or val > 100.0:
                        errors.append(f"Change #{idx}: Soil moisture ({val}%) must be between 0.0% and 100.0%.")

                # Soil Organic Carbon
                elif var_name == "soil_organic_carbon":
                    if val < 0.0:
                        errors.append(f"Change #{idx}: Soil organic carbon ({val}%) cannot be negative.")
                    elif val > 100.0:
                        errors.append(f"Change #{idx}: Soil organic carbon ({val}%) exceeds physical soil fraction (>100%).")

                # Temperature
                elif var_name == "temperature":
                    if val < -60.0 or val > 70.0:
                        errors.append(f"Change #{idx}: Ambient temperature ({val}°C) falls outside terrestrial biological limits (-60°C to 70°C).")

            # 6. Qualitative values: Ensure qualitative values are not synthetic numbers
            elif isinstance(val, str):
                if val.lower() in ["high", "low", "medium", "moderate"]:
                    # Qualitative allowed, but flag that it cannot be converted to a guessed number
                    ch.status = "assumed_scenario"

        return len(errors) == 0, errors
