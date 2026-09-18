"""Regression tests for DARUKAA.EARTH Live Behavior Correction Audit.

Verifies:
- Bug 1: Incomplete context must not trigger recommendations (land use alone continues clarification).
- Bug 2: Measurement lookup ("What is my current soil moisture?") returns missing measurement message; rainfall != soil moisture.
- Bug 3: Scenario baseline declarations do not become scenario changes; no no-op SOC error.
- Bug 4: Rainfall must never be displayed as soil moisture in Evaluation Matrix.
- Bug 5: 600 mm rainfall is not classified as "low" without context.
- Bug 6: Intent routing properly separates turn types.
- Bug 7: Unsupported species quantification is refused without invented numbers or old recommendations.
- Bug 8: Confidence semantics distinguish computational confidence from scientific evidence confidence.
"""

import pytest
from app.conversation.schemas import ChatRequest, MetricStatus
from app.conversation.turn_processor import TurnProcessor
from app.conversation.context_manager import EnvironmentalContextManager
from app.scenarios.parser import ScenarioParser
from app.scenarios.validator import ScenarioValidator
from app.scenarios.state_builder import ScenarioStateBuilder
from app.scenarios.analyzer import ScenarioAnalysisEngine
from app.scenarios.schemas import ScenarioType, ImpactDirection, ScenarioChange
from app.environmental.metric_rules import classify_metric
from app.environmental.analyzer import EnvironmentalRelationshipAnalyzer


# =============================================================================
# BUG 1: Incomplete context must not trigger recommendations
# =============================================================================
def test_bug1_incomplete_context_does_not_trigger_recommendations():
    """Turn 1: Biodiversity declining -> clarification asked.
    Turn 2: Land use provided alone -> clarification MUST continue, NO recommendations.
    """
    conv_id = "test_conv_bug1"
    # Reset in-memory context
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    # Turn 1: User says biodiversity is declining
    req1 = ChatRequest(conversation_id=conv_id, message="My biodiversity is declining on my farm.")
    resp1 = TurnProcessor.process_turn(req1)
    assert resp1.status == "clarification_needed"
    assert resp1.clarification_questions is not None
    assert len(resp1.clarification_questions) > 0
    assert "recommendations" not in (resp1.assessment or {})

    # Turn 2: User provides ONLY land use
    req2 = ChatRequest(conversation_id=conv_id, message="I grow wheat continuously.")
    resp2 = TurnProcessor.process_turn(req2)

    # Must continue clarification!
    assert resp2.status == "clarification_needed", f"Expected clarification_needed but got {resp2.status}"
    assert resp2.clarification_questions is not None
    assert len(resp2.clarification_questions) > 0
    # Must NOT generate recommendations
    assert resp2.assessment is None or "recommendations" not in resp2.assessment
    assert "Agroforestry" not in resp2.message


# =============================================================================
# BUG 2: Measurement questions must not trigger old recommendations
# =============================================================================
def test_bug2_measurement_lookup_soil_moisture_not_provided():
    """Asking 'What is my current soil moisture?' when moisture is missing
    must state it has not been provided, not infer from rainfall, and not trigger recommendations.
    """
    conv_id = "test_conv_bug2"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    # Setup context with rainfall = 600 mm, but NO soil moisture
    req_setup = ChatRequest(conversation_id=conv_id, message="Annual rainfall is around 600 mm.")
    TurnProcessor.process_turn(req_setup)

    # Verify rainfall is recorded
    ctx = EnvironmentalContextManager.get_or_create_context(conv_id)
    assert "rainfall" in ctx.variables
    assert ctx.variables["rainfall"].value == 600.0
    # Crucially: rainfall != soil_moisture!
    assert "soil_moisture" not in ctx.variables

    # User asks for soil moisture
    req_query = ChatRequest(conversation_id=conv_id, message="My biodiversity is declining. What is my current soil moisture?")
    resp = TurnProcessor.process_turn(req_query)

    assert resp.status == "completed"
    assert "Soil moisture has not been provided" in resp.message
    assert "share it and I can use it in the assessment" in resp.message
    # Must NOT run recommendations
    assert resp.assessment is None
    # Must not infer 600 mm as soil moisture
    assert "600" not in resp.message


# =============================================================================
# BUG 3: Scenario baseline declarations must not become changes
# =============================================================================
def test_bug3_preamble_baseline_extraction_and_no_op_guard():
    """Query with explicit baseline preamble declarations followed by what-if clause.
    Preamble variables must populate baseline; changes must contain only what-if modifications;
    no no-op change error for SOC.
    """
    query = (
        "SOC = 0.3%\n"
        "Rainfall = 600 mm\n"
        "Land use = wheat monoculture\n\n"
        "What if rainfall decreases by 15% and I switch from wheat monoculture to intercropping?"
    )

    baseline = {}
    changes, needs_clarif, clarif_q = ScenarioParser.parse_query(query, baseline)

    assert not needs_clarif
    assert len(clarif_q) == 0

    # Verify baseline was extracted from preamble
    assert baseline.get("soil_organic_carbon") == 0.3
    assert baseline.get("rainfall") == 600.0
    assert "wheat monoculture" in str(baseline.get("land_use")).lower()

    # Verify changes list
    changed_vars = [c.variable for c in changes]
    assert "soil_organic_carbon" not in changed_vars, "SOC must NOT be a scenario change!"
    assert "rainfall" in changed_vars
    assert "land_use" in changed_vars

    # Check relative rainfall change
    rain_change = next(c for c in changes if c.variable == "rainfall")
    assert rain_change.baseline_value == 600.0
    assert rain_change.scenario_value == 510.0
    assert rain_change.change_value == -15.0
    assert rain_change.change_type in (ScenarioType.RELATIVE_CHANGE, "relative_change")

    # Check categorical land-use change
    land_change = next(c for c in changes if c.variable == "land_use")
    assert land_change.baseline_value == "wheat monoculture"
    assert land_change.scenario_value == "intercropping"
    assert land_change.change_type in (ScenarioType.LAND_USE_CHANGE, ScenarioType.CATEGORICAL_CHANGE, "land_use_change", "categorical_change")

    # Verify validator accepts without no-op error
    is_valid, errs = ScenarioValidator.validate_changes(changes, baseline)
    assert is_valid, f"Validation failed with errors: {errs}"


def test_bug3_multiple_baseline_declarations():
    """Multiple baseline declarations before scenario clause."""
    query = (
        "Baseline: SOC is 0.5%, annual rainfall is 800 mm, pH is 6.5, land use is continuous wheat.\n"
        "What if rainfall decreases by 20%?"
    )
    baseline = {}
    changes, needs_clarif, _ = ScenarioParser.parse_query(query, baseline)
    assert not needs_clarif
    assert baseline["soil_organic_carbon"] == 0.5
    assert baseline["rainfall"] == 800.0
    assert baseline["soil_ph"] == 6.5
    assert len(changes) == 1
    assert changes[0].variable == "rainfall"
    assert changes[0].scenario_value == 640.0


# =============================================================================
# BUG 4: Rainfall must never be displayed as soil moisture
# =============================================================================
def test_bug4_rainfall_must_never_be_displayed_as_soil_moisture():
    """In Evaluation Matrix:
    Rainfall Baseline = 600 mm, Scenario = 510 mm.
    Soil Moisture must remain Unknown / Not provided.
    Assert rainfall -> rainfall and rainfall != soil_moisture.
    """
    baseline = {
        "soil_organic_carbon": 0.3,
        "rainfall": 600.0,
        "land_use": "wheat monoculture",
    }
    # Notice: soil_moisture is NOT in baseline!

    changes, _, _ = ScenarioParser.parse_query(
        "What if rainfall decreases by 15% and I switch to intercropping?",
        baseline,
    )
    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)
    comparison = ScenarioAnalysisEngine.analyze_scenario(
        baseline=baseline,
        scenario_state=scen_state,
        changes=changes,
        assumptions=assumptions,
    )

    # Inspect Evaluation Matrix
    matrix_metrics = {row.metric: row for row in comparison.evaluation_matrix}

    # 1. Rainfall row MUST exist and label rainfall
    assert "rainfall" in matrix_metrics, "Evaluation matrix must contain 'rainfall' row!"
    rain_row = matrix_metrics["rainfall"]
    assert "600" in str(rain_row.baseline)
    assert "510" in str(rain_row.scenario)

    # 2. Soil Moisture row MUST NOT show 600 mm or 510 mm!
    if "soil_moisture" in matrix_metrics:
        moist_row = matrix_metrics["soil_moisture"]
        assert "600 mm" not in str(moist_row.baseline), "Rainfall baseline must NEVER be mapped to soil moisture!"
        assert "510 mm" not in str(moist_row.scenario), "Rainfall scenario must NEVER be mapped to soil moisture!"
        assert "Unknown" in str(moist_row.baseline) or "Not provided" in str(moist_row.baseline)

    # 3. Assert rainfall != soil_moisture
    assert rain_row.metric != "soil_moisture"
    assert scen_state.get("rainfall") == 510.0
    assert scen_state.get("soil_moisture") is None


# =============================================================================
# BUG 5: Do not classify 600 mm as "low" without context
# =============================================================================
def test_bug5_rainfall_600mm_not_classified_as_low_without_context():
    """600 mm annual rainfall must not automatically be classified as 'low' or 'water-limited'
    without regional or seasonal aridity context.
    """
    # 1. Metric classification test
    cls_600 = classify_metric("rainfall", 600.0)
    assert cls_600 is not None
    assert cls_600.classification == "sub_humid_moderate"
    assert "water_limited" not in cls_600.classification
    assert any("whether this represents water stress depends on regional and seasonal context" in lim for lim in cls_600.limitations)

    # 2. Environmental analyzer compound synthesis test
    analyzer = EnvironmentalRelationshipAnalyzer()
    env_data = {
        "soil_organic_carbon": 0.3,
        "rainfall": 600.0,
        "land_use": "continuous wheat cropping",
    }
    _, _, summary = analyzer.analyze(env_data)
    compound = summary.get("compound_synthesis") or ""

    assert "low precipitation (600.0)" not in compound
    assert "whether this represents water stress depends on regional and seasonal context" in compound


# =============================================================================
# BUG 6: Intent routing controls response
# =============================================================================
def test_bug6_intent_routing():
    """Different user intents must receive distinct deterministic handling,
    not repeatedly receiving the previous recommendations.
    """
    conv_id = "test_conv_bug6"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    # Turn 1: State update with land use
    resp1 = TurnProcessor.process_turn(ChatRequest(conversation_id=conv_id, message="I grow wheat continuously."))
    assert resp1.status == "clarification_needed"

    # Turn 2: Measurement lookup
    resp2 = TurnProcessor.process_turn(ChatRequest(conversation_id=conv_id, message="What is my current soil moisture?"))
    assert resp2.status == "completed"
    assert "Soil moisture has not been provided" in resp2.message
    assert "recommendations" not in (resp2.assessment or {})

    # Turn 3: State update with crop switch
    resp3 = TurnProcessor.process_turn(ChatRequest(conversation_id=conv_id, message="I switched to maize."))
    assert resp3.status == "clarification_needed"
    assert "maize" in resp3.message.lower()

    # Turn 4: Unsupported quantification
    resp4 = TurnProcessor.process_turn(ChatRequest(conversation_id=conv_id, message="How many species will increase if SOC changes from 0.3% to 0.6%?"))
    assert resp4.status == "completed"
    assert "Exact species increase cannot be determined" in resp4.message


# =============================================================================
# BUG 7: Unsupported species quantification refused
# =============================================================================
def test_bug7_unsupported_species_quantification_refusal():
    """User asking for exact species count prediction must be refused with
    an explanation of required studies, without invented numbers.
    """
    conv_id = "test_conv_bug7"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    msg = "My soil organic carbon is 0.3%. Tell me exactly how many species will increase if I improve it to 0.6%."
    resp = TurnProcessor.process_turn(ChatRequest(conversation_id=conv_id, message=msg))

    assert resp.status == "completed"
    assert "Exact species increase cannot be determined from the available evidence" in resp.message
    assert "eDNA metabarcoding" in resp.message or "taxonomic baseline" in resp.message
    # Must NOT invent species count or percentage
    import re
    # Should not say "increase by X species" or "X% more species"
    assert not re.search(r"increase by [0-9]+ species", resp.message, re.IGNORECASE)
    assert not re.search(r"[0-9]+% more species", resp.message, re.IGNORECASE)
    # Context must have recorded SOC = 0.3%
    ctx = EnvironmentalContextManager.get_or_create_context(conv_id)
    assert "soil_organic_carbon" in ctx.variables
    assert ctx.variables["soil_organic_carbon"].value == 0.3


# =============================================================================
# BUG 8: Confidence semantics
# =============================================================================
def test_bug8_confidence_semantics_distinguish_computational_from_scientific():
    """Deterministic arithmetic (600 * 0.85 = 510) carries high computational confidence,
    but does NOT elevate overall ecological scenario confidence to HIGH.
    """
    baseline = {
        "soil_organic_carbon": 0.3,
        "rainfall": 600.0,
        "land_use": "wheat monoculture",
    }
    changes, _, _ = ScenarioParser.parse_query(
        "What if rainfall decreases by 15% and I switch to intercropping?",
        baseline,
    )
    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)
    comparison = ScenarioAnalysisEngine.analyze_scenario(
        baseline=baseline,
        scenario_state=scen_state,
        changes=changes,
        assumptions=assumptions,
    )

    factors = comparison.confidence_factors
    assert "computational_confidence" in factors
    assert factors["computational_confidence"] == "high"  # Exact arithmetic

    assert "scientific_evidence_confidence" in factors
    assert factors["scientific_evidence_confidence"] == "medium"  # Ecological evidence

    # Overall scenario confidence reflects scientific evidence, not arithmetic
    assert comparison.confidence == "medium"

    # Evaluation Matrix: rainfall row has high computational confidence, ecological rows have medium
    matrix = {row.metric: row for row in comparison.evaluation_matrix}
    assert matrix["rainfall"].confidence == "high"
    if "soil_moisture" in matrix:
        assert matrix["soil_moisture"].confidence == "medium"
    if "soil_organic_carbon" in matrix:
        assert matrix["soil_organic_carbon"].confidence == "medium"
    if "species_richness" in matrix:
        assert matrix["species_richness"].confidence == "medium"


# =============================================================================
# ISSUE 1 & 2: Soil Moisture Unknown & Source Terminology
# =============================================================================
def test_issue1_soil_moisture_remains_unknown_in_scenarios():
    """Soil moisture must remain Unknown / Not provided for both baseline and scenario
    when not explicitly provided by the user. Rainfall drop (-15%) must NOT convert
    into an inferred soil_moisture = decreased measurement.
    """
    baseline = {
        "land_use": "wheat monoculture",
        "rainfall": 600.0,
        "soil_organic_carbon": 0.3,
    }
    changes = [
        ScenarioChange(
            variable="rainfall",
            change_type=ScenarioType.RELATIVE_CHANGE,
            change_value=-15.0,
            unit="percent",
            baseline_value=600.0,
            scenario_value=510.0,
        ),
        ScenarioChange(
            variable="land_use",
            change_type=ScenarioType.CATEGORICAL_CHANGE,
            value="intercropping",
            baseline_value="wheat monoculture",
            scenario_value="intercropping",
        ),
    ]
    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)
    comparison = ScenarioAnalysisEngine.analyze_scenario(
        baseline=baseline,
        scenario_state=scen_state,
        changes=changes,
        assumptions=assumptions,
    )

    matrix = {row.metric: row for row in comparison.evaluation_matrix}
    assert "soil_moisture" in matrix
    moist_row = matrix["soil_moisture"]

    # Must be Unknown for both baseline and scenario
    assert moist_row.baseline == "Unknown / Not provided"
    assert moist_row.scenario == "Unknown / Not provided"
    assert moist_row.direction.value == "uncertain"
    assert "Reduced rainfall may increase soil-water stress or desiccation risk" in moist_row.limitations
    assert "validated hydrological model" in moist_row.limitations

    # In impacted_metrics: soil_moisture must NOT be "decreased"
    moist_impact = next((m for m in comparison.impacted_metrics if m.metric == "soil_moisture"), None)
    assert moist_impact is not None
    assert moist_impact.direction.value == "uncertain", "soil_moisture must NOT be 'decreased' from rainfall drop alone!"

    # Potential implication for soil-water stress is represented separately
    stress_impact = next((m for m in comparison.impacted_metrics if m.metric == "soil_water_stress"), None)
    assert stress_impact is not None
    assert stress_impact.direction.value == "increased"
    assert any("not a measured soil-moisture value" in lim for lim in stress_impact.limitations)


def test_issue2_source_terminology_accurate():
    """Ensure technical sources like FAO/IPCC reports are not falsely claimed as
    'peer-reviewed literature', but rather 'verified scientific and technical sources'.
    """
    baseline = {
        "land_use": "wheat monoculture",
        "rainfall": 600.0,
        "soil_organic_carbon": 0.3,
    }
    changes = [
        ScenarioChange(
            variable="rainfall",
            change_type=ScenarioType.RELATIVE_CHANGE,
            change_value=-15.0,
            unit="percent",
            baseline_value=600.0,
            scenario_value=510.0,
        ),
    ]
    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)
    comparison = ScenarioAnalysisEngine.analyze_scenario(
        baseline=baseline,
        scenario_state=scen_state,
        changes=changes,
        assumptions=assumptions,
    )

    # 1. Rationale in confidence factors
    rationale = comparison.confidence_factors.get("rationale", "")
    assert "peer-reviewed literature" not in rationale.lower()
    assert "verified scientific and technical sources" in rationale.lower()

    # 2. Limitations
    for lim in comparison.limitations:
        assert "peer-reviewed literature" not in lim.lower()

    # 3. Unsupported species quantification turn processor response
    resp = TurnProcessor.process_turn(
        ChatRequest(
            conversation_id="test_terminology_conv",
            message="My SOC is 0.3%. If I improve it to 0.6%, exactly how many species will increase?",
        )
    )
    assert "peer-reviewed literature" not in resp.message.lower()
    assert "authoritative scientific and technical sources" in resp.message.lower()

