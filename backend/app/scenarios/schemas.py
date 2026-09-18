"""Pydantic domain schemas for the Environmental Scenario Analysis Engine.

Enforces strict taxonomy:
- Variable status: observed, inferred, assumed_scenario, unknown
- Change types: management_intervention, metric_change, land_use_change, combined
- Directions: increased, decreased, mixed, uncertain, no_supported_change
- Trade-off types: synergy, tradeoff, uncertain
- Evaluation Matrix: baseline vs scenario comparison with evidence and limitations
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ScenarioType(str, Enum):
    """Categorical classification of hypothetical environmental scenarios."""
    MANAGEMENT_INTERVENTION = "management_intervention"
    METRIC_CHANGE = "metric_change"
    LAND_USE_CHANGE = "land_use_change"
    COMBINED = "combined"
    RELATIVE_CHANGE = "relative_change"
    CATEGORICAL_CHANGE = "categorical_change"


class ImpactDirection(str, Enum):
    """Direction of evaluated ecological impact relative to baseline."""
    INCREASED = "increased"
    DECREASED = "decreased"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"
    NO_SUPPORTED_CHANGE = "no_supported_change"


class TradeoffType(str, Enum):
    """Classification of multi-dimensional interactions."""
    SYNERGY = "synergy"
    TRADEOFF = "tradeoff"
    UNCERTAIN = "uncertain"


class ScenarioChange(BaseModel):
    """Structured representation of a single parameter delta in a what-if scenario."""
    model_config = ConfigDict(extra="ignore")

    variable: str = Field(..., description="Target environmental variable name")
    value: Optional[Union[float, int, str]] = Field(default=None, description="Inbound generic value or delta")
    baseline_value: Optional[Union[float, int, str]] = Field(default=None, description="Established baseline value")
    scenario_value: Optional[Union[float, int, str]] = Field(default=None, description="Hypothetical scenario value")
    change_value: Optional[Union[float, int, str]] = Field(default=None, description="Explicit relative or absolute change amount")
    unit: Optional[str] = Field(default=None, description="Measurement unit (e.g., mm, %, pH, C, percent)")
    change_type: ScenarioType = Field(default=ScenarioType.METRIC_CHANGE, description="Intervention category")
    source: str = Field(default="user_scenario", description="Source of hypothetical delta")
    status: str = Field(default="assumed_scenario", description="observed, inferred, assumed_scenario, unknown")
    notes: Optional[str] = Field(default=None, description="Qualitative clarification or calculation note")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        var = str(data.get("variable") or "").lower().strip()
        val = data.get("value")
        raw_change = data.get("change_value")
        raw_scen = data.get("scenario_value")
        raw_base = data.get("baseline_value")
        unit = str(data.get("unit") or "").strip()
        unit_lower = unit.lower()
        raw_type = data.get("change_type")

        effective_val = val if val is not None else raw_change

        # Check if this represents a relative percentage change
        is_relative = False
        if raw_type in ("relative_change", ScenarioType.RELATIVE_CHANGE):
            is_relative = True
        elif unit_lower in ("percent", "%", "pct") and var in ("rainfall", "precipitation", "temperature"):
            is_relative = True
        elif unit_lower in ("percent", "%", "pct") and isinstance(effective_val, (int, float)) and var not in ("soil_organic_carbon", "soil_moisture"):
            is_relative = True

        if is_relative:
            if raw_change is None and effective_val is not None:
                data["change_value"] = effective_val
            if data.get("value") is None and effective_val is not None:
                data["value"] = effective_val
            if not raw_type or raw_type == ScenarioType.METRIC_CHANGE:
                data["change_type"] = ScenarioType.RELATIVE_CHANGE

            # If baseline is known, calculate scenario_value deterministically
            if raw_base is not None and isinstance(raw_base, (int, float)) and isinstance(data.get("change_value"), (int, float)):
                pct = float(data["change_value"])
                base = float(raw_base)
                data["scenario_value"] = round(base * (1.0 + pct / 100.0), 1)
                if not data.get("notes"):
                    direction_word = "reduction" if pct < 0 else "increase"
                    data["notes"] = f"Relative {direction_word} of {abs(pct)}% applied to baseline ({base} → {data['scenario_value']})"
            elif raw_scen is None:
                # Baseline is unknown: do not invent absolute scenario value!
                data["scenario_value"] = None
                if not data.get("notes") and data.get("change_value") is not None:
                    cv = data["change_value"]
                    direction_word = "decreases" if (isinstance(cv, (int, float)) and cv < 0) else "changes"
                    pct_str = f"{abs(cv)}%" if isinstance(cv, (int, float)) else str(cv)
                    data["notes"] = f"{var.replace('_', ' ').capitalize()} {direction_word} by {pct_str} relative to baseline; absolute scenario {var.replace('_', ' ')} cannot be calculated without a baseline measurement."

        else:
            # Not a relative percentage change:
            # Check if categorical (e.g. land_use = "intercropping")
            is_categorical = False
            if raw_type in ("categorical_change", ScenarioType.CATEGORICAL_CHANGE, "land_use_change", ScenarioType.LAND_USE_CHANGE, "management_intervention", ScenarioType.MANAGEMENT_INTERVENTION):
                is_categorical = True
            elif var in ("land_use", "land_cover", "pollution", "deforestation") or isinstance(effective_val, str):
                is_categorical = True

            if is_categorical:
                cat_val = raw_scen if raw_scen is not None else effective_val
                if raw_scen is None and cat_val is not None:
                    data["scenario_value"] = cat_val
                if raw_change is None and cat_val is not None:
                    data["change_value"] = cat_val
                if data.get("value") is None and cat_val is not None:
                    data["value"] = cat_val
                if not raw_type:
                    data["change_type"] = ScenarioType.CATEGORICAL_CHANGE
            else:
                # Standard metric change
                if raw_scen is None and effective_val is not None:
                    data["scenario_value"] = effective_val
                if data.get("value") is None and raw_scen is not None:
                    data["value"] = raw_scen

        return data


class EvaluationMatrixItem(BaseModel):
    """Single row in the structured Baseline-vs-Scenario Evaluation Matrix (Correction 7)."""
    model_config = ConfigDict(extra="ignore")

    metric: str = Field(..., description="Environmental metric evaluated")
    baseline: Optional[Union[float, int, str]] = Field(default=None, description="Baseline condition")
    scenario: Optional[Union[float, int, str]] = Field(default=None, description="Hypothetical scenario condition")
    direction: ImpactDirection = Field(..., description="Direction of supported ecological effect")
    evidence_chunk_ids: List[str] = Field(default_factory=list, description="IDs of grounding literature chunks")
    confidence: str = Field(default="medium", description="Categorical confidence (high, medium, low, insufficient)")
    limitations: str = Field(default="Local agronomic conditions may modulate observed response.", description="Ecological caveats")


class MetricImpact(BaseModel):
    """Detailed evaluated ecological impact for an individual environmental metric."""
    model_config = ConfigDict(extra="ignore")

    metric: str = Field(..., description="Environmental variable or ecosystem function")
    direction: ImpactDirection = Field(..., description="Supported directional response")
    rationale: str = Field(..., description="Mechanistic explanation grounded in relationship graph & literature")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence chunk IDs")
    confidence: str = Field(default="medium", description="Evidence-backed confidence grade")
    magnitude: Optional[Union[float, str]] = Field(default=None, description="Quantitative magnitude if scientifically supported")
    magnitude_supported: bool = Field(default=False, description="True ONLY if verified evidence directly supports exact number")
    limitations: List[str] = Field(default_factory=list, description="Limitations and context sensitivities")


class ScenarioTradeoff(BaseModel):
    """Evidence-grounded trade-off or synergy identified across metrics (Correction 2)."""
    model_config = ConfigDict(extra="ignore")

    metric: str = Field(..., description="Metric exhibiting synergy or trade-off")
    direction: ImpactDirection = Field(..., description="Impact direction")
    tradeoff_type: TradeoffType = Field(..., description="synergy, tradeoff, or uncertain")
    rationale: str = Field(..., description="Evidence-derived explanation of why this trade-off occurs")
    evidence_ids: List[str] = Field(default_factory=list, description="Literature chunk citations supporting trade-off")


class ScenarioTimeHorizon(BaseModel):
    """Qualitative temporal horizons for scenario effects without fabricated timelines."""
    model_config = ConfigDict(extra="ignore")

    short_term: str = Field(..., description="Immediate vegetative and habitat restructuring dynamics")
    medium_term: str = Field(..., description="Transitional soil organic matter and microclimate adjustments")
    long_term: str = Field(..., description="Persistent multi-trophic ecosystem equilibrium effects")


class ScenarioComparison(BaseModel):
    """Complete comparative analysis report contrasting Baseline with Scenario."""
    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(..., description="Unique scenario identifier")
    conversation_id: Optional[str] = Field(default=None, description="Associated multi-turn session ID")
    baseline_summary: Dict[str, Any] = Field(default_factory=dict, description="Active baseline parameters")
    scenario_summary: Dict[str, Any] = Field(default_factory=dict, description="Derived scenario parameters")
    assumptions: List[str] = Field(default_factory=list, description="Explicit scenario assumptions (Correction 5)")
    changed_variables: List[ScenarioChange] = Field(default_factory=list, description="Explicit changes applied")
    evaluation_matrix: List[EvaluationMatrixItem] = Field(default_factory=list, description="Structured comparative matrix")
    impacted_metrics: List[MetricImpact] = Field(default_factory=list, description="Evaluated metric impacts")
    synergies: List[ScenarioTradeoff] = Field(default_factory=list, description="Evidence-grounded synergies")
    tradeoffs: List[ScenarioTradeoff] = Field(default_factory=list, description="Evidence-grounded trade-offs")
    tradeoff_summary: Optional[str] = Field(default=None, description="Overall trade-off assessment")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Active multi-metric relationship graphs")
    multi_metric_coverage: str = Field(default="compound (3 variables)", description="Explanation of multi-metric support")
    multi_metric_grounding: bool = Field(default=True, description="Whether >=3 variables are genuinely supported")
    time_horizon: ScenarioTimeHorizon = Field(..., description="Qualitative temporal dynamics")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Grounding literature evidence items")
    limitations: List[str] = Field(default_factory=list, description="Systemic ecological limitations")
    confidence: str = Field(default="medium", description="Overall scenario confidence")
    confidence_factors: Dict[str, Any] = Field(default_factory=dict, description="Measurable driving factors")


class ScenarioAnalysisRequest(BaseModel):
    """Inbound request payload for what-if scenario analysis."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: Optional[str] = Field(default=None, description="Optional dialogue session to inherit baseline from")
    query: Optional[str] = Field(default=None, description="Natural language what-if inquiry")
    changes: Optional[List[ScenarioChange]] = Field(default=None, description="Structured scenario delta list")
    baseline: Optional[Dict[str, Any]] = Field(default=None, description="Explicit baseline parameters if not from session")


class ScenarioAnalysisResponse(BaseModel):
    """Outbound machine-readable response payload for scenario analysis."""
    model_config = ConfigDict(extra="ignore")

    status: str = Field(..., description="'completed', 'needs_clarification', 'insufficient_evidence', 'error'")
    scenario_id: str = Field(..., description="Assigned scenario identifier")
    comparison: Optional[ScenarioComparison] = Field(default=None, description="Complete comparison report if completed")
    clarification_needed: bool = Field(default=False, description="True if scenario inquiry was ambiguous")
    clarification_questions: List[str] = Field(default_factory=list, description="Disambiguating questions")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
