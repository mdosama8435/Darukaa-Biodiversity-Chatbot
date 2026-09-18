"""Scenario State Builder creating immutable hypothetical states with explicit assumptions.

Ensures:
- Baseline is cloned immutably; original conversation memory is never modified.
- Variable statuses are strictly maintained (observed, inferred, assumed_scenario, unknown).
- Generates explicit scenario assumptions for the response report.
"""

from copy import deepcopy
from typing import Any, Dict, List, Tuple
from app.scenarios.schemas import ScenarioChange


class ScenarioStateBuilder:
    """Derives scenario environmental profiles from baseline states and validated deltas."""

    @classmethod
    def build_scenario_state(
        cls,
        baseline: Dict[str, Any],
        changes: List[ScenarioChange],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Constructs an immutable scenario environmental state and assumptions list.
        
        Args:
            baseline: Established baseline environmental key-value dictionary.
            changes: Validated list of scenario changes.
            
        Returns:
            Tuple of:
            - scenario_state: Dict[str, Any] (cloned and updated)
            - assumptions: List[str] (human-readable scenario assumptions)
        """
        scenario_state = deepcopy(baseline)
        assumptions: List[str] = []

        for ch in changes:
            var_name = ch.variable
            scen_val = ch.scenario_value
            unit_str = f" {ch.unit}" if ch.unit else ""
            prev_str = f" (baseline: {ch.baseline_value}{unit_str})" if ch.baseline_value is not None else ""

            scenario_state[var_name] = scen_val

            # Build assumption description
            if ch.change_type.value in ("relative_change",) or (ch.unit in ("percent", "%") and ch.change_value is not None):
                cv = ch.change_value
                direction = "decreases" if (isinstance(cv, (int, float)) and cv < 0) else "increases"
                pct_str = f"{abs(cv)}%" if isinstance(cv, (int, float)) else f"{cv}%"
                if scen_val is not None and ch.baseline_value is not None:
                    m_unit = " mm" if var_name == "rainfall" else (" °C" if var_name == "temperature" else "")
                    assumptions.append(f"Assume {var_name.replace('_', ' ')} {direction} by {pct_str} relative to baseline ({ch.baseline_value}{m_unit} → {scen_val}{m_unit}).")
                elif scen_val is not None:
                    assumptions.append(f"Assume {var_name.replace('_', ' ')} changes to {scen_val}{unit_str}{prev_str}.")
                else:
                    assumptions.append(f"Assume {var_name.replace('_', ' ')} {direction} by {pct_str} relative to baseline (baseline uncalibrated).")
            elif ch.change_type.value in ("land_use_change", "categorical_change") or var_name == "land_use":
                assumptions.append(f"Assume land use is transitioned to '{scen_val}'{prev_str}.")
            elif ch.change_type.value == "management_intervention":
                assumptions.append(f"Assume adoption of management practice '{scen_val}'{prev_str}.")
            elif ch.change_type.value == "metric_change":
                if scen_val is not None:
                    assumptions.append(f"Assume {var_name.replace('_', ' ')} changes to {scen_val}{unit_str}{prev_str}.")
                else:
                    assumptions.append(f"Assume {var_name.replace('_', ' ')} changes by {ch.change_value}{unit_str}{prev_str}.")
            elif ch.change_type.value == "combined":
                assumptions.append(f"Assume {var_name.replace('_', ' ')} is set to {scen_val}{unit_str}{prev_str}.")
            else:
                assumptions.append(f"Assume {var_name} is {scen_val if scen_val is not None else ch.change_value}{unit_str}.")

        # Add assumption regarding unchanged variables
        unchanged = [k for k in baseline.keys() if k not in [c.variable for c in changes]]
        if unchanged:
            assumptions.append(
                f"All other baseline variables ({', '.join(unchanged)}) are assumed to remain constant."
            )

        return scenario_state, assumptions
