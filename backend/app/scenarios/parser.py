"""Deterministic Natural Language & Structured Scenario Delta Parser.

Parses what-if inquiries into explicit ScenarioChange objects.
Enforces:
- Ambiguity detection (e.g., "diversify the farm" prompts clarification)
- Outcome metric guarding (e.g., "increase biodiversity by 40%" prompts for intervention)
- Relative numerical deltas (e.g., "rainfall decreases by 15%")
- Absolute numerical transitions (e.g., "SOC increases from 0.3% to 0.8%")
- Land-use and management transitions (e.g., "replace wheat monoculture with intercropping")
- Multi-intervention combined scenarios
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from app.scenarios.schemas import ScenarioChange, ScenarioType


class ScenarioParser:
    @classmethod
    def split_preamble_and_scenario(cls, query: str) -> Tuple[str, str]:
        """Splits query into baseline preamble and hypothetical scenario clause (Bug 3)."""
        # Look for transition from baseline preamble to scenario perturbation clause
        # Must be preceded by punctuation or transition word so initial "Suppose I have a farm..." is retained as preamble
        match = re.search(
            r"(?:[\.\?\!\n]|\b(?:then|now)\b)\s*(what happens if\b|what if\b|what would happen if\b|how would\b)",
            query,
            re.IGNORECASE,
        )
        if match:
            preamble = query[:match.start()].strip()
            scenario = query[match.start():].lstrip(".?!,; \n\t").strip()
            return preamble, scenario
        return "", query.strip()

    @classmethod
    def extract_baseline_declarations(cls, text: str) -> Dict[str, Any]:
        """Extracts environmental baseline variables declared in preambles or statements."""
        extracted: Dict[str, Any] = {}
        if not text:
            return extracted

        lower = text.lower()

        # Soil Organic Carbon (%)
        soc_match = re.search(r"(?:soc|soil organic carbon)\s*(?:is|=|level is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if soc_match:
            extracted["soil_organic_carbon"] = float(soc_match.group(1))

        # Rainfall (mm)
        rain_match = re.search(r"(?:annual\s*)?(?:rainfall|precipitation)\s*(?:is|=|of|around|is around)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mm|millimeters)", lower)
        if not rain_match:
            rain_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:mm|millimeters)\b", lower)
        if rain_match:
            extracted["rainfall"] = float(rain_match.group(1))

        # Land Use
        lu_match = re.search(r"land\s*use\s*(?:is|=|:)\s*([^\n\.,]+)", lower)
        if lu_match:
            extracted["land_use"] = lu_match.group(1).strip()
        elif "wheat monoculture" in lower:
            extracted["land_use"] = "wheat monoculture"
        elif "continuous wheat" in lower or "wheat continuous" in lower or "grow wheat continuously" in lower:
            extracted["land_use"] = "continuous wheat cropping"
        elif "monoculture" in lower:
            extracted["land_use"] = "monoculture"
        elif "agroforestry" in lower and "switch to" not in lower:
            extracted["land_use"] = "agroforestry"

        # Soil pH
        ph_match = re.search(r"\b(?:soil\s*)?ph\s*(?:is|=|level is)?\s*([0-9]+(?:\.[0-9]+)?)\b", lower)
        if ph_match:
            extracted["soil_ph"] = float(ph_match.group(1))

        # Soil Moisture
        moist_match = re.search(r"\b(?:soil\s*)?moisture\s*(?:is|=|level is)?\s*([0-9]+(?:\.[0-9]+)?)\s*%?", lower)
        if moist_match:
            extracted["soil_moisture"] = float(moist_match.group(1))

        # Region
        if "semi-arid bihar" in lower or "semi arid bihar" in lower:
            extracted["region"] = "semi-arid Bihar"
        elif "semi-arid" in lower or "semi arid" in lower:
            extracted["region"] = "semi-arid"

        return extracted

    @classmethod
    def parse_query(
        cls,
        query: str,
        baseline: Dict[str, Any],
    ) -> Tuple[List[ScenarioChange], bool, List[str]]:
        """Parses a natural language scenario inquiry.
        
        Args:
            query: User's what-if inquiry text.
            baseline: Established baseline environmental key-value dictionary.
            
        Returns:
            Tuple of:
            - changes: List[ScenarioChange]
            - clarification_needed: bool
            - clarification_questions: List[str]
        """
        # 0. Separate baseline preamble from scenario clause (Bug 3)
        preamble, scenario_clause = cls.split_preamble_and_scenario(query)
        target_text = query
        if preamble:
            preamble_baseline = cls.extract_baseline_declarations(preamble)
            if preamble_baseline:
                for k, v in preamble_baseline.items():
                    if baseline.get(k) is None:
                        baseline[k] = v
                target_text = scenario_clause

        lower = target_text.lower().strip()
        changes: List[ScenarioChange] = []
        clarification_questions: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Outcome Metric Guard (Correction 3 & Safety Rule)
        # ---------------------------------------------------------------------
        # e.g., "What if I increase biodiversity by 40%?", "What if species richness increases by 20?"
        if re.search(r"\b(?:increase|improve|boost)\s+biodiversity\s*(?:by\s*[0-9]+(?:\.[0-9]+)?%)?", lower) or \
           re.search(r"\bbiodiversity\s*(?:increases|improves|rises)\s*by\s*[0-9]+(?:\.[0-9]+)?%", lower):
            q = (
                "Biodiversity is an ecosystem outcome metric rather than a direct management intervention. "
                "What specific practice — such as intercropping, agroforestry, rotational grazing, or cover crops — "
                "would you like to evaluate?"
            )
            return [], True, [q]

        # ---------------------------------------------------------------------
        # 2. Ambiguity Detection (Correction 8)
        # ---------------------------------------------------------------------
        # e.g., "What if I diversify the farm?", "What if I diversify my land?"
        if re.search(r"\b(?:diversify|diversification)\s*(?:the\s*farm|my\s*land|my\s*farm|agriculture|crops)?\b", lower) and \
           not any(k in lower for k in ["intercropping", "agroforestry", "rotation", "cover crop"]):
            q = (
                "What diversification change do you want to evaluate — "
                "intercropping, agroforestry, crop rotation, or cover crops?"
            )
            return [], True, [q]

        # ---------------------------------------------------------------------
        # 3. Land Use & Management Interventions
        # ---------------------------------------------------------------------
        current_land_use = baseline.get("land_use")

        # Intercropping
        if "intercropping" in lower:
            prev_val = current_land_use or "monoculture"
            changes.append(
                ScenarioChange(
                    variable="land_use",
                    baseline_value=prev_val,
                    scenario_value="intercropping",
                    unit=None,
                    change_type=ScenarioType.LAND_USE_CHANGE if "monoculture" in str(prev_val).lower() else ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical adoption of diversified intercropping",
                )
            )

        # Agroforestry
        if "agroforestry" in lower:
            prev_val = current_land_use or "cropland"
            changes.append(
                ScenarioChange(
                    variable="land_use",
                    baseline_value=prev_val,
                    scenario_value="agroforestry",
                    unit=None,
                    change_type=ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical integration of perennial woody species into cropland",
                )
            )

        # Cover crops
        if "cover crop" in lower or "cover crops" in lower or "cover cropping" in lower:
            changes.append(
                ScenarioChange(
                    variable="land_use",
                    baseline_value=current_land_use or "conventional cropland",
                    scenario_value="cover cropping",
                    unit=None,
                    change_type=ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical introduction of off-season vegetative ground cover",
                )
            )

        # Switch crop: wheat to maize
        if "switch from wheat to maize" in lower or "switch to maize" in lower or "replace wheat with maize" in lower:
            changes.append(
                ScenarioChange(
                    variable="land_use",
                    baseline_value=current_land_use or "wheat monoculture",
                    scenario_value="maize",
                    unit=None,
                    change_type=ScenarioType.LAND_USE_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical crop substitution from wheat to maize",
                )
            )

        # Deforestation
        if "deforestation increases" in lower or "increase deforestation" in lower or "forest clearing" in lower:
            changes.append(
                ScenarioChange(
                    variable="deforestation",
                    baseline_value=baseline.get("deforestation", "none"),
                    scenario_value="severe",
                    unit=None,
                    change_type=ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical expansion of canopy clearance and vegetative removal",
                )
            )
        elif "reduce deforestation" in lower or "stop deforestation" in lower:
            changes.append(
                ScenarioChange(
                    variable="deforestation",
                    baseline_value=baseline.get("deforestation", "fragmented"),
                    scenario_value="none",
                    unit=None,
                    change_type=ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical cessation of forest clearing",
                )
            )

        # Pollution
        if "reduce pollution" in lower or "eliminate chemical runoff" in lower:
            changes.append(
                ScenarioChange(
                    variable="pollution",
                    baseline_value=baseline.get("pollution", "moderate"),
                    scenario_value="low",
                    unit=None,
                    change_type=ScenarioType.MANAGEMENT_INTERVENTION,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes="Hypothetical reduction in chemical runoff and synthetic agrochemical loads",
                )
            )

        # ---------------------------------------------------------------------
        # 4. Numerical Metric Changes (Relative & Absolute)
        # ---------------------------------------------------------------------
        # Rainfall Relative: "rainfall decreases by 15%", "rainfall -15%"
        rain_rel_match = re.search(r"rainfall\s*(?:decreases|declines|drops|reduces|drops by|decreases by|declines by|-)\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if not rain_rel_match:
            rain_rel_match = re.search(r"(?:decrease|reduce|drop)\s*rainfall\s*by\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if rain_rel_match:
            pct = float(rain_rel_match.group(1))
            raw_base_rain = baseline.get("rainfall")
            if raw_base_rain is not None:
                base_rain = float(raw_base_rain)
                scen_rain = round(base_rain * (1.0 - pct / 100.0), 1)
                unit_rain = "mm"
                notes_rain = f"Relative reduction of {pct}% applied to baseline ({base_rain} mm → {scen_rain} mm)"
            else:
                base_rain = None
                scen_rain = None
                unit_rain = "percent"
                notes_rain = f"Rainfall decreases by {pct}% relative to baseline; absolute scenario rainfall cannot be calculated without a baseline measurement."

            changes.append(
                ScenarioChange(
                    variable="rainfall",
                    value=-pct,
                    change_value=-pct,
                    baseline_value=base_rain,
                    scenario_value=scen_rain,
                    unit=unit_rain,
                    change_type=ScenarioType.RELATIVE_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes=notes_rain,
                )
            )
        else:
            # Rainfall Absolute: "rainfall is 500 mm", "rainfall of 450 mm"
            rain_abs_match = re.search(r"rainfall\s*(?:is|=|changes to|becomes)?\s*([0-9]+(?:\.[0-9]+)?)\s*mm", lower)
            if rain_abs_match:
                new_rain = float(rain_abs_match.group(1))
                changes.append(
                    ScenarioChange(
                        variable="rainfall",
                        baseline_value=baseline.get("rainfall"),
                        scenario_value=new_rain,
                        unit="mm",
                        change_type=ScenarioType.METRIC_CHANGE,
                        source="user_scenario",
                        status="assumed_scenario",
                        notes=f"Absolute rainfall scenario: {new_rain} mm",
                    )
                )

        # Temperature: "temperature rises by 2°C", "temperature +2C", "temperature increases by 2"
        temp_rel_match = re.search(r"temperature\s*(?:rises|increases|warms|rises by|increases by|\+)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:°?c|degrees)?\b", lower)
        if not temp_rel_match:
            temp_rel_match = re.search(r"(?:rise|increase|warm)\s*(?:in\s*)?temperature\s*by\s*([0-9]+(?:\.[0-9]+)?)\s*(?:°?c|degrees)?\b", lower)
        if temp_rel_match:
            delta_t = float(temp_rel_match.group(1))
            raw_base_temp = baseline.get("temperature")
            if raw_base_temp is not None:
                base_temp = float(raw_base_temp)
                scen_temp = round(base_temp + delta_t, 1)
                notes_temp = f"Thermal rise of +{delta_t}°C applied to baseline ({base_temp}°C → {scen_temp}°C)"
            else:
                base_temp = None
                scen_temp = None
                notes_temp = f"Temperature rises by {delta_t}°C relative to baseline; absolute temperature cannot be calculated without baseline."

            changes.append(
                ScenarioChange(
                    variable="temperature",
                    value=delta_t,
                    change_value=delta_t,
                    baseline_value=base_temp,
                    scenario_value=scen_temp,
                    unit="C",
                    change_type=ScenarioType.METRIC_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes=notes_temp,
                )
            )

        # Soil Organic Carbon: "soil organic carbon increases from 0.3% to 0.8%", "SOC from 0.3% to 0.8%"
        soc_trans_match = re.search(r"(?:soc|soil organic carbon)\s*(?:increases|changes|rises)?\s*from\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*to\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if soc_trans_match:
            base_soc = float(soc_trans_match.group(1))
            scen_soc = float(soc_trans_match.group(2))
            changes.append(
                ScenarioChange(
                    variable="soil_organic_carbon",
                    value=scen_soc,
                    baseline_value=base_soc,
                    scenario_value=scen_soc,
                    unit="%",
                    change_type=ScenarioType.METRIC_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes=f"Targeted SOC accrual from {base_soc}% to {scen_soc}%",
                )
            )
        else:
            # SOC single value: "SOC is 0.8%", "SOC increases to 0.8%"
            soc_single_match = re.search(r"(?:soc|soil organic carbon)\s*(?:is|=|increases to|to)?\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
            if soc_single_match:
                new_soc = float(soc_single_match.group(1))
                changes.append(
                    ScenarioChange(
                        variable="soil_organic_carbon",
                        value=new_soc,
                        baseline_value=baseline.get("soil_organic_carbon"),
                        scenario_value=new_soc,
                        unit="%",
                        change_type=ScenarioType.METRIC_CHANGE,
                        source="user_scenario",
                        status="assumed_scenario",
                        notes=f"Hypothetical SOC level: {new_soc}%",
                    )
                )

        # Soil Moisture: "soil moisture declines by 20%", "soil moisture drops by 10%"
        moist_rel_match = re.search(r"soil moisture\s*(?:declines|drops|falls|decreases|declines by|drops by|-)\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if not moist_rel_match and ("soil moisture declines" in lower or "moisture drops" in lower):
            moist_rel_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s*%\b", lower)
        if moist_rel_match:
            m_pct = float(moist_rel_match.group(1))
            raw_base_m = baseline.get("soil_moisture")
            if raw_base_m is not None:
                base_m = float(raw_base_m)
                scen_m = round(base_m * (1.0 - m_pct / 100.0), 1)
                unit_m = "%"
                notes_m = f"Relative moisture reduction of {m_pct}% ({base_m}% → {scen_m}%)"
            else:
                base_m = None
                scen_m = None
                unit_m = "percent"
                notes_m = f"Soil moisture decreases by {m_pct}% relative to baseline; absolute soil moisture cannot be calculated without baseline."

            changes.append(
                ScenarioChange(
                    variable="soil_moisture",
                    value=-m_pct,
                    change_value=-m_pct,
                    baseline_value=base_m,
                    scenario_value=scen_m,
                    unit=unit_m,
                    change_type=ScenarioType.RELATIVE_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes=notes_m,
                )
            )

        # Soil pH: "pH from 5.2 to 6.0", "pH changes from 5.2 to 6.0"
        ph_trans_match = re.search(r"\b(?:soil\s*)?ph\s*(?:changes|increases)?\s*from\s*([0-9]+(?:\.[0-9]+)?)\s*to\s*([0-9]+(?:\.[0-9]+)?)\b", lower)
        if ph_trans_match:
            base_ph = float(ph_trans_match.group(1))
            scen_ph = float(ph_trans_match.group(2))
            changes.append(
                ScenarioChange(
                    variable="soil_ph",
                    baseline_value=base_ph,
                    scenario_value=scen_ph,
                    unit="pH",
                    change_type=ScenarioType.METRIC_CHANGE,
                    source="user_scenario",
                    status="assumed_scenario",
                    notes=f"Soil pH adjustment from {base_ph} to {scen_ph}",
                )
            )

        # Filter out no-op changes where scenario_value is identical to baseline (Bug 3)
        valid_changes: List[ScenarioChange] = []
        for ch in changes:
            if ch.baseline_value is not None and ch.scenario_value is not None:
                if ch.baseline_value == ch.scenario_value and (ch.change_value is None or ch.change_value == 0):
                    # Statement declared a baseline equality rather than a scenario delta
                    continue
            valid_changes.append(ch)

        # If 3 or more changes extracted, mark change_type as COMBINED (combined scenario)
        if len(valid_changes) >= 3:
            for ch in valid_changes:
                ch.change_type = ScenarioType.COMBINED

        # If no changes were recognized from query text, check if query contains an unrecognized what-if
        if not valid_changes and ("what if" in lower or "compare" in lower or "suppose" in lower or "assume" in lower):
            q = "I could not identify a specific environmental parameter or management practice to simulate. Could you specify the intervention (e.g., 'What if I introduce intercropping?' or 'What if rainfall decreases by 15%?')?"
            return [], True, [q]

        return valid_changes, False, []
