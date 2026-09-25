"""Environmental Context Manager managing multi-turn memory, state merging, and provenance."""

import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from app.conversation.schemas import (
    MetricStatus,
    VariableProvenance,
    ContextUpdateRecord,
    EnvironmentalContextModel,
)


class EnvironmentalContextManager:
    """Manages multi-turn environmental state accumulation, value overrides, and provenance tracking."""

    # In-memory session store (used when running without PostgreSQL daemon or in tests)
    _MEMORY_STORE: Dict[str, EnvironmentalContextModel] = {}

    @classmethod
    def get_or_create_context(
        cls,
        conversation_id: str,
        initial_depth: int = 0,
    ) -> EnvironmentalContextModel:
        """Retrieves active conversation context or initializes a fresh context model."""
        if conversation_id not in cls._MEMORY_STORE:
            cls._MEMORY_STORE[conversation_id] = EnvironmentalContextModel(
                conversation_id=conversation_id,
                variables={},
                detected_updates=[],
                clarification_depth=initial_depth,
            )
        return cls._MEMORY_STORE[conversation_id]

    @classmethod
    def verify_access_boundary(
        cls,
        conversation_user_id: Optional[str],
        request_user_id: Optional[str],
    ) -> bool:
        """Enforces access control boundary (Correction 4).
        
        If a conversation is bound to a user, requests must match the owning user_id.
        """
        if conversation_user_id and request_user_id:
            return str(conversation_user_id) == str(request_user_id)
        # If conversation has an owner but request is anonymous -> reject
        if conversation_user_id and not request_user_id:
            return False
        return True

    @classmethod
    def extract_from_message(
        cls,
        text: str,
        turn_id: int,
        active_context: Optional[EnvironmentalContextModel] = None,
    ) -> Tuple[Dict[str, VariableProvenance], List[str], Optional[str]]:
        """Extracts environmental observations, explicit unknowns, and handles ambiguous references.
        
        Returns:
            Tuple of:
            - extracted_variables: Dict[str, VariableProvenance]
            - explicit_unknowns: List[str] (variables explicitly stated as unknown)
            - ambiguous_resolution_needed: Optional[str] (question to clarify pronoun/ambiguity)
        """
        extracted: Dict[str, VariableProvenance] = {}
        explicit_unknowns: List[str] = []
        lower = text.lower().strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        # ---------------------------------------------------------------------
        # 1. Detect Explicit UNKNOWN Declarations (Step 4 & Correction 2)
        # e.g. "I don't know my soil organic carbon", "SOC is unknown"
        # ---------------------------------------------------------------------
        unknown_patterns = [
            (r"(?:don't know|do not know|unknown|no idea|haven't measured)\s*(?:about\s*)?(?:my\s*)?(?:soc|soil organic carbon)", "soil_organic_carbon"),
            (r"(?:don't know|do not know|unknown|no idea)\s*(?:about\s*)?(?:my\s*)?(?:soil\s*)?ph", "soil_ph"),
            (r"(?:don't know|do not know|unknown|no idea)\s*(?:about\s*)?(?:my\s*)?(?:rainfall|precipitation)", "rainfall"),
            (r"(?:don't know|do not know|unknown|no idea)\s*(?:about\s*)?(?:my\s*)?(?:soil\s*)?moisture", "soil_moisture"),
        ]
        for pattern, var_name in unknown_patterns:
            if re.search(pattern, lower):
                explicit_unknowns.append(var_name)
                extracted[var_name] = VariableProvenance(
                    variable=var_name,
                    value=None,  # UNKNOWN != ZERO
                    unit=None,
                    source="user_statement",
                    turn_id=turn_id,
                    timestamp=now_iso,
                    status=MetricStatus.UNKNOWN,
                    notes="User explicitly stated metric is unknown",
                )

        # ---------------------------------------------------------------------
        # 2. Correction 3: Ambiguous Reference Resolution (e.g. "It is 0.3%")
        # ---------------------------------------------------------------------
        ambiguous_match = re.search(r"^(?:it is|it\'s|value is)?\s*([0-9]+(?:\.[0-9]+)?)\s*(%|mm|ph)?\.?$", lower)
        if ambiguous_match and active_context:
            number_val = float(ambiguous_match.group(1))
            unit_val = ambiguous_match.group(2)

            # Check prior turn clarification or context to see what could be the referent
            # If percentage: could be SOC or soil moisture
            if unit_val == "%" or number_val < 5.0:
                soc_missing = "soil_organic_carbon" not in active_context.variables or active_context.variables["soil_organic_carbon"].status == MetricStatus.UNKNOWN
                moist_missing = "soil_moisture" not in active_context.variables or active_context.variables["soil_moisture"].status == MetricStatus.UNKNOWN

                # If both are candidate percentage targets, DO NOT guess per Correction 3!
                if soc_missing and moist_missing:
                    return extracted, explicit_unknowns, "Do you mean Soil Organic Carbon (SOC) or Soil Moisture?"

        # ---------------------------------------------------------------------
        # 3. Explicit Numeric Environmental Measurements
        # ---------------------------------------------------------------------
        # Soil Organic Carbon (%)
        soc_match = re.search(r"(?:soc|soil organic carbon)\s*(?:is|=|level is|of|:)?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*%", lower)
        if soc_match and "soil_organic_carbon" not in explicit_unknowns:
            soc_val = float(soc_match.group(1))
            extracted["soil_organic_carbon"] = VariableProvenance(
                variable="soil_organic_carbon",
                value=soc_val,
                unit="%",
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )

        # Soil pH
        ph_match = re.search(r"\b(?:soil\s*)?ph\s*(?:is|=|level is|of|:)?\s*(-?[0-9]+(?:\.[0-9]+)?)\b", lower)
        if ph_match and "soil_ph" not in explicit_unknowns:
            ph_val = float(ph_match.group(1))
            extracted["soil_ph"] = VariableProvenance(
                variable="soil_ph",
                value=ph_val,
                unit="pH",
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )

        # Rainfall (mm)
        rain_match = re.search(r"(?:rainfall|precipitation)\s*(?:is|=|is around|around|:)?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(?:mm|millimeters)", lower)
        if not rain_match:
            rain_match = re.search(r"\b(-?[0-9]+(?:\.[0-9]+)?)\s*(?:mm|millimeters)\b", lower)
        if rain_match and "rainfall" not in explicit_unknowns:
            rain_val = float(rain_match.group(1))
            extracted["rainfall"] = VariableProvenance(
                variable="rainfall",
                value=rain_val,
                unit="mm",
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif any(p in lower for p in ["rainfall is low", "low rainfall", "rainfall: low", "low precipitation", "rainfall of low", "rainfall is around low"]):
            if "rainfall" not in explicit_unknowns:
                extracted["rainfall"] = VariableProvenance(
                    variable="rainfall",
                    value="low",
                    unit=None,
                    source="user_statement",
                    turn_id=turn_id,
                    timestamp=now_iso,
                    status=MetricStatus.PROVIDED,
                    notes="Qualitative rainfall regime provided by user",
                )
        elif any(p in lower for p in ["very dry", "arid area", "drought prone"]):
            # Inferred qualitative signal when user did not mention rainfall explicitly
            if "rainfall" not in extracted and "rainfall" not in explicit_unknowns:
                extracted["rainfall"] = VariableProvenance(
                    variable="rainfall",
                    value=None,
                    unit=None,
                    source="inferred",
                    turn_id=turn_id,
                    timestamp=now_iso,
                    status=MetricStatus.INFERRED,
                    notes="Qualitative dryland signal mentioned; numeric measurement not provided",
                )

        # Soil Moisture (% or volumetric) - completely independent from rainfall (Condition 3)
        moist_match = re.search(r"\b(?:soil\s+)?moisture\s*(?:is|=|level is|of|:)?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(?:%|percent)?\b", lower)
        if moist_match and "soil_moisture" not in explicit_unknowns:
            moist_val = float(moist_match.group(1))
            extracted["soil_moisture"] = VariableProvenance(
                variable="soil_moisture",
                value=moist_val,
                unit="%",
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )

        # ---------------------------------------------------------------------
        # 4. Land Use & Crop Type (Handles Updates e.g. wheat -> maize & Wheat Context)
        # ---------------------------------------------------------------------
        if "switched from wheat to maize" in lower or "switched to maize" in lower or "now grow maize" in lower:
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="maize",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.UPDATED,
            )
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="maize",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.UPDATED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif "wheat monoculture" in lower or "monoculture wheat" in lower or ("monoculture" in lower and "wheat" in lower):
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="wheat",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="wheat monoculture",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif "grow wheat continuously" in lower or "wheat continuously" in lower or ("grow wheat" in lower and "continuous" in lower) or "continuous wheat" in lower:
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="wheat",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="wheat continuous cropping",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif any(p in lower for p in ["wheat farm", "wheat field", "wheat cultivation", "wheat cropping"]):
            # Section 5: Establishes crop context and land use without assuming continuous monoculture
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="wheat",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="wheat cultivation",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif any(p in lower for p in ["i grow wheat", "grow wheat", "growing wheat", "we grow wheat"]):
            # Section 5: "I grow wheat" establishes crop = wheat, but should NOT automatically establish continuous monoculture
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="wheat",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif any(p in lower for p in ["i grow maize", "grow maize", "growing maize", "maize farm", "maize field"]):
            extracted["crop"] = VariableProvenance(
                variable="crop",
                value="maize",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
            extracted["land_cover"] = VariableProvenance(
                variable="land_cover",
                value="cropland",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif "agroforestry" in lower:
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="agroforestry",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif "intercropping" in lower:
            extracted["land_use"] = VariableProvenance(
                variable="land_use",
                value="intercropping",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )

        # ---------------------------------------------------------------------
        # 5. Region / Spatial Context
        # ---------------------------------------------------------------------
        if "bihar" in lower:
            reg_val = "semi-arid Bihar" if "semi-arid" in lower or "semi arid" in lower else "Bihar"
            extracted["region"] = VariableProvenance(
                variable="region",
                value=reg_val,
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )
        elif "semi-arid" in lower or "semi arid" in lower or "arid region" in lower or "dryland" in lower:
            extracted["region"] = VariableProvenance(
                variable="region",
                value="semi-arid",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
            )

        # ---------------------------------------------------------------------
        # 6. Biodiversity Indicators & Species Richness
        # ---------------------------------------------------------------------
        if any(p in lower for p in ["low species richness", "species richness is low", "low species count"]):
            extracted["species_richness"] = VariableProvenance(
                variable="species_richness",
                value="low",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
                notes="Qualitative low species richness reported by user",
            )
        elif any(p in lower for p in ["biodiversity has been declining", "biodiversity has declined", "biodiversity is declining", "biodiversity declining", "poor biodiversity", "low biodiversity"]):
            extracted["habitat_diversity"] = VariableProvenance(
                variable="habitat_diversity",
                value="low",
                unit=None,
                source="user_statement",
                turn_id=turn_id,
                timestamp=now_iso,
                status=MetricStatus.PROVIDED,
                notes="Qualitative biodiversity decline reported by user",
            )

        return extracted, explicit_unknowns, None

    @classmethod
    def validate_candidate_variables(
        cls,
        candidate_variables: Dict[str, VariableProvenance],
    ) -> List[str]:
        """Validates newly candidate variables BEFORE environmental state mutation.
        
        Section 1 Pipeline:
        Candidate values must be strictly validated before entering active state, provenance,
        detected updates, or database records. Invalid values return friendly user-facing messages
        without exposing raw Pydantic errors or stack traces.
        """
        errors: List[str] = []

        for var_name, prov in candidate_variables.items():
            val = prov.value
            if val is None or prov.status == MetricStatus.UNKNOWN:
                continue

            # 1. Soil pH (Must be 0 <= pH <= 14)
            if var_name == "soil_ph":
                if isinstance(val, (int, float)):
                    if val < 0.0 or val > 14.0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Soil pH must be between 0 and 14. The value `{clean_v}` is outside the valid measurement range. "
                            f"Please check the value and provide the corrected pH."
                        )

            # 2. Soil Moisture (Must be 0 <= moisture <= 100)
            elif var_name == "soil_moisture":
                if isinstance(val, (int, float)):
                    if val < 0.0 or val > 100.0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Soil moisture must be between 0 and 100%. The value `{clean_v}` is outside the valid measurement range. "
                            f"Please check the value and provide the corrected moisture."
                        )

            # 3. Soil Organic Carbon (Must be 0 <= SOC <= 100)
            elif var_name == "soil_organic_carbon":
                if isinstance(val, (int, float)):
                    if val < 0.0 or val > 100.0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Soil organic carbon must be between 0 and 100%. The value `{clean_v}` is outside the valid measurement range. "
                            f"Please check the value and provide the corrected SOC."
                        )

            # 4. Rainfall (Must be non-negative)
            elif var_name == "rainfall":
                if isinstance(val, (int, float)):
                    if val < 0.0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Rainfall cannot be negative. The value `{clean_v}` is outside the valid measurement range. "
                            f"Please check the value and provide the corrected rainfall."
                        )

            # 5. Temperature (Must be between -60 and 70 C)
            elif var_name == "temperature":
                if isinstance(val, (int, float)):
                    if val < -60.0 or val > 70.0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Temperature must be between -60 and 70 °C. The value `{clean_v}` is outside the valid measurement range. "
                            f"Please check the value and provide the corrected temperature."
                        )

            # 6. Species Richness (Must be non-negative count if numeric)
            elif var_name == "species_richness":
                if isinstance(val, (int, float)):
                    if val < 0:
                        clean_v = int(val) if isinstance(val, float) and val.is_integer() else val
                        errors.append(
                            f"Species richness count cannot be negative. The value `{clean_v}` is outside the valid measurement range."
                        )

        return errors

    @classmethod
    def merge_context(
        cls,
        current_context: EnvironmentalContextModel,
        new_variables: Dict[str, VariableProvenance],
        turn_id: int,
    ) -> Tuple[EnvironmentalContextModel, List[ContextUpdateRecord]]:
        """Merges newly extracted variables into persistent context, preserving unmentioned variables
        and recording value overrides (Step 3).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        updates_detected: List[ContextUpdateRecord] = []

        for var_name, new_prov in new_variables.items():
            # Correction 2: Inferred signals must NEVER overwrite explicit user measurements
            if new_prov.status == MetricStatus.INFERRED:
                if var_name in current_context.variables and current_context.variables[var_name].value is not None:
                    continue  # Do not overwrite existing explicit measurement with inferred signal

            if var_name in current_context.variables:
                old_prov = current_context.variables[var_name]
                # Check if value has changed
                if old_prov.value != new_prov.value and new_prov.value is not None:
                    rec = ContextUpdateRecord(
                        variable=var_name,
                        old_value=old_prov.value,
                        new_value=new_prov.value,
                        turn_id=turn_id,
                        timestamp=now_iso,
                        reason=f"Overridden in Turn {turn_id}",
                    )
                    updates_detected.append(rec)
                    current_context.detected_updates.append(rec)
                    new_prov.status = MetricStatus.UPDATED
                    new_prov.notes = f"Updated from {old_prov.value} in Turn {turn_id}"

            current_context.variables[var_name] = new_prov

        current_context.updated_at = now_iso
        return current_context, updates_detected

    @classmethod
    def get_flat_environmental_data(
        cls,
        context: EnvironmentalContextModel,
    ) -> Dict[str, Any]:
        """Flattens persistent context to key-value pairs suitable for Phase 3 reasoning."""
        flat: Dict[str, Any] = {}
        for var_name, prov in context.variables.items():
            # Only include non-None values; UNKNOWN remains None/omitted
            if prov.value is not None:
                flat[var_name] = prov.value
        return flat
