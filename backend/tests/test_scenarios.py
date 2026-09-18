"""Comprehensive test suite for Phase 5: Environmental Scenario Analysis Engine.

Covers all 25 validation criteria and the 10 approval corrections:
1. Model & evaluation matrix validation
2. Tier A user-input relative arithmetic (600 mm - 15% = 510 mm)
3. Absolute numerical transitions (SOC 0.3% -> 0.8%)
4. Categorical land-use transitions (wheat monoculture -> intercropping)
5. Combined multi-variable scenarios
6. Strict baseline immutability
7. Unknown value preservation
8. Ambiguous scenario clarification prompting
9. Invalid physical boundaries rejection (pH = 15, rainfall = -500)
10. Outcome metric guarding (cannot set biodiversity as direct intervention)
11. Multi-metric genuine support check (>=3 variables only when genuinely supported)
12. Evidence-driven trade-offs without hardcoded conclusions
13. Three-tiered quantitative claim guard ("Direction supported; magnitude cannot be reliably estimated...")
14. Source verification: unverified Torralba removed; grounded in verified FAO 2020 & IPCC 2019
15. Structured Scenario Evaluation Matrix generation
16. Multi-turn conversation integration with preserved baseline memory
17. Structured REST API (/api/v1/scenarios/analyze)
18. Natural language REST API
19. Zero fake fallbacks on scenario retrieval
20. Real pgvector integration test (skipped cleanly per Rule 14 when offline)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.scenarios.schemas import (
    ScenarioType,
    ImpactDirection,
    TradeoffType,
    ScenarioChange,
    EvaluationMatrixItem,
    MetricImpact,
    ScenarioTradeoff,
    ScenarioComparison,
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
)
from app.scenarios.parser import ScenarioParser
from app.scenarios.validator import ScenarioValidator
from app.scenarios.state_builder import ScenarioStateBuilder
from app.scenarios.analyzer import ScenarioAnalysisEngine
from app.environmental.relationships import ENVIRONMENTAL_RELATIONSHIPS
from app.conversation.context_manager import EnvironmentalContextManager
from app.conversation.turn_processor import TurnProcessor
from app.conversation.schemas import ChatRequest, MetricStatus, VariableProvenance
from app.database.connection import SessionLocal


client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Model & Matrix Validation
# -----------------------------------------------------------------------------
class TestScenarioSchemasAndMatrix:
    """Verifies Pydantic schema validation and evaluation matrix structure."""

    def test_scenario_change_model(self):
        change = ScenarioChange(
            variable="rainfall",
            baseline_value=600.0,
            scenario_value=510.0,
            unit="mm",
            change_type=ScenarioType.METRIC_CHANGE,
            status="assumed_scenario",
        )
        assert change.variable == "rainfall"
        assert change.scenario_value == 510.0
        assert change.status == "assumed_scenario"

    def test_evaluation_matrix_item_model(self):
        row = EvaluationMatrixItem(
            metric="soil_organic_carbon",
            baseline="0.3%",
            scenario="0.8% (assumed)",
            direction=ImpactDirection.INCREASED,
            evidence_chunk_ids=["fao_c2"],
            confidence="medium",
            limitations="Retention is constrained by clay fraction and temperature.",
        )
        assert row.direction == ImpactDirection.INCREASED
        assert row.confidence == "medium"
        assert len(row.evidence_chunk_ids) == 1


# -----------------------------------------------------------------------------
# 2 & 3 & 4 & 5. Parser Tests (Arithmetic, Absolute, Categorical, Combined)
# -----------------------------------------------------------------------------
class TestScenarioParser:
    """Tests deterministic natural language parsing and delta extraction."""

    def test_relative_arithmetic_tier_a(self):
        """User-input arithmetic: 600 mm - 15% = 510 mm."""
        baseline = {"rainfall": 600.0, "land_use": "wheat monoculture"}
        changes, needs_clarif, questions = ScenarioParser.parse_query("What if rainfall decreases by 15%?", baseline)

        assert not needs_clarif
        assert len(changes) == 1
        ch = changes[0]
        assert ch.variable == "rainfall"
        assert ch.baseline_value == 600.0
        assert ch.scenario_value == 510.0
        assert ch.unit == "mm"
        assert ch.status == "assumed_scenario"

    def test_absolute_numerical_transition(self):
        """Absolute transition: SOC 0.3% -> 0.8%."""
        baseline = {"soil_organic_carbon": 0.3, "land_use": "wheat monoculture"}
        changes, needs_clarif, questions = ScenarioParser.parse_query("What if soil organic carbon increases from 0.3% to 0.8%?", baseline)

        assert not needs_clarif
        assert len(changes) == 1
        ch = changes[0]
        assert ch.variable == "soil_organic_carbon"
        assert ch.baseline_value == 0.3
        assert ch.scenario_value == 0.8
        assert ch.unit == "%"

    def test_categorical_land_use_transition(self):
        """Land use transition: wheat monoculture -> intercropping."""
        baseline = {"land_use": "wheat monoculture", "rainfall": 600.0}
        changes, needs_clarif, questions = ScenarioParser.parse_query("What if I replace wheat monoculture with intercropping?", baseline)

        assert not needs_clarif
        assert len(changes) == 1
        ch = changes[0]
        assert ch.variable == "land_use"
        assert ch.scenario_value == "intercropping"

    def test_combined_multi_variable_scenario(self):
        """Combined scenario: SOC increase + intercropping + rainfall decrease."""
        baseline = {"soil_organic_carbon": 0.3, "land_use": "wheat monoculture", "rainfall": 600.0}
        query = "Increase SOC from 0.3% to 0.8%, introduce intercropping, and assume rainfall decreases by 10%"
        changes, needs_clarif, questions = ScenarioParser.parse_query(query, baseline)

        assert not needs_clarif
        assert len(changes) == 3
        vars_changed = {c.variable for c in changes}
        assert vars_changed == {"soil_organic_carbon", "land_use", "rainfall"}
        for c in changes:
            assert c.change_type == ScenarioType.COMBINED


# -----------------------------------------------------------------------------
# 6 & 7. State Builder & Baseline Immutability
# -----------------------------------------------------------------------------
class TestScenarioStateBuilder:
    """Verifies baseline immutability, assumption reporting, and status tracking."""

    def test_baseline_immutability(self):
        """Hypothetical scenario changes MUST NOT mutate the original baseline."""
        baseline = {"soil_organic_carbon": 0.3, "rainfall": 600.0, "land_use": "wheat monoculture"}
        changes = [
            ScenarioChange(
                variable="land_use",
                baseline_value="wheat monoculture",
                scenario_value="intercropping",
                change_type=ScenarioType.LAND_USE_CHANGE,
            )
        ]

        scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)

        # Baseline remains untouched
        assert baseline["land_use"] == "wheat monoculture"
        assert baseline["rainfall"] == 600.0

        # Scenario state reflects change
        assert scen_state["land_use"] == "intercropping"
        assert scen_state["rainfall"] == 600.0  # preserved unchanged

        # Assumptions include the change and constant variables
        assert any("intercropping" in a for a in assumptions)
        assert any("rainfall" in a for a in assumptions)

    def test_unknown_values_remain_unknown(self):
        """Variables absent or unknown in baseline are not fabricated in scenario."""
        baseline = {"land_use": "wheat monoculture"}
        changes = [
            ScenarioChange(
                variable="land_use",
                scenario_value="agroforestry",
                change_type=ScenarioType.MANAGEMENT_INTERVENTION,
            )
        ]

        scen_state, _ = ScenarioStateBuilder.build_scenario_state(baseline, changes)
        assert "soil_ph" not in scen_state
        assert "rainfall" not in scen_state


# -----------------------------------------------------------------------------
# 8 & 9 & 10. Ambiguity & Validation Boundaries
# -----------------------------------------------------------------------------
class TestScenarioValidationAndAmbiguity:
    """Tests validation of boundaries, impossible values, outcome metrics, and ambiguities."""

    def test_ambiguous_scenario_clarification(self):
        """Vague 'diversify the farm' must trigger clarification question."""
        baseline = {"land_use": "wheat monoculture"}
        changes, needs_clarif, questions = ScenarioParser.parse_query("What if I diversify the farm?", baseline)

        assert needs_clarif
        assert len(questions) == 1
        assert "intercropping" in questions[0]
        assert "agroforestry" in questions[0]

    def test_outcome_metric_guard(self):
        """Rejecting requests to set biodiversity as direct intervention."""
        baseline = {"species_richness": 10}
        changes, needs_clarif, questions = ScenarioParser.parse_query("What if I increase biodiversity by 40%?", baseline)

        assert needs_clarif
        assert "outcome metric" in questions[0].lower()

    def test_invalid_ph_boundary_rejected(self):
        """pH = 15 must be rejected."""
        changes = [
            ScenarioChange(
                variable="soil_ph",
                scenario_value=15.0,
                unit="pH",
                change_type=ScenarioType.METRIC_CHANGE,
            )
        ]
        is_valid, errs = ScenarioValidator.validate_changes(changes)
        assert not is_valid
        assert any("bounded between 0.0 and 14.0" in e for e in errs)

    def test_negative_rainfall_rejected(self):
        """Negative rainfall must be rejected."""
        changes = [
            ScenarioChange(
                variable="rainfall",
                scenario_value=-500.0,
                unit="mm",
                change_type=ScenarioType.METRIC_CHANGE,
            )
        ]
        is_valid, errs = ScenarioValidator.validate_changes(changes)
        assert not is_valid
        assert any("physically impossible" in e for e in errs)


# -----------------------------------------------------------------------------
# 11 & 12 & 13. Multi-Metric, Trade-offs & Claim Guard
# -----------------------------------------------------------------------------
class TestScenarioAnalysisEngine:
    """Tests multi-metric reasoning, evidence-driven trade-offs, and claim guards."""

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_multi_metric_genuine_support_check(self, mock_session, mock_retriever):
        """Verifies >=3 variables flagged when supported, and limited coverage reported when 1-2."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        # Case A: 3 variables genuinely present (land_use, rainfall, soil_organic_carbon)
        baseline = {"land_use": "wheat monoculture", "rainfall": 450.0, "soil_organic_carbon": 0.3}
        scen_state = {"land_use": "intercropping", "rainfall": 450.0, "soil_organic_carbon": 0.8}
        changes = [
            ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE),
            ScenarioChange(variable="soil_organic_carbon", scenario_value=0.8, change_type=ScenarioType.METRIC_CHANGE),
        ]

        comp = ScenarioAnalysisEngine.analyze_scenario(
            baseline=baseline,
            scenario_state=scen_state,
            changes=changes,
            assumptions=["Assume intercropping and SOC 0.8%"],
        )
        assert comp.multi_metric_grounding is True
        assert "compound" in comp.multi_metric_coverage.lower()

        # Case B: Only 1 variable present (no compound relationship possible)
        base_single = {"land_use": "wheat monoculture"}
        scen_single = {"land_use": "maize"}
        ch_single = [ScenarioChange(variable="land_use", scenario_value="maize", change_type=ScenarioType.LAND_USE_CHANGE)]

        comp_single = ScenarioAnalysisEngine.analyze_scenario(
            baseline=base_single,
            scenario_state=scen_single,
            changes=ch_single,
            assumptions=["Assume maize"],
        )
        assert comp_single.multi_metric_grounding is False
        assert "limited" in comp_single.multi_metric_coverage.lower()

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_evidence_driven_tradeoffs_no_hardcoding(self, mock_session, mock_retriever):
        """Trade-offs must not be hardcoded. If evidence does not mention trade-offs, return empty list."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        baseline = {"land_use": "wheat monoculture", "rainfall": 600.0, "soil_organic_carbon": 0.3}
        scen_state = {"land_use": "intercropping", "rainfall": 600.0, "soil_organic_carbon": 0.3}
        changes = [ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE)]

        comp = ScenarioAnalysisEngine.analyze_scenario(
            baseline=baseline,
            scenario_state=scen_state,
            changes=changes,
            assumptions=["Assume intercropping"],
        )

        # Since mock returned no trade-off chunks, trade-offs must be empty (NOT hardcoded)
        assert len(comp.tradeoffs) == 0
        assert "no evidence-backed trade-offs were identified" in comp.tradeoff_summary.lower()

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_three_tier_claim_guard_rejects_hallucinations(self, mock_session, mock_retriever):
        """Derived ecological predictions must not hallucinate numerical percentages."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        baseline = {"land_use": "wheat monoculture", "soil_organic_carbon": 0.3}
        scen_state = {"land_use": "intercropping", "soil_organic_carbon": 0.3}
        changes = [ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE)]

        comp = ScenarioAnalysisEngine.analyze_scenario(
            baseline=baseline,
            scenario_state=scen_state,
            changes=changes,
            assumptions=["Assume intercropping"],
        )

        for impact in comp.impacted_metrics:
            assert impact.magnitude is None
            assert impact.magnitude_supported is False
            assert "Direction supported; magnitude cannot be reliably estimated" in impact.rationale


# -----------------------------------------------------------------------------
# 14. Source Verification Test
# -----------------------------------------------------------------------------
class TestSourceVerification:
    """Verifies that unverified research metadata was eliminated from the active relationship registry."""

    def test_unverified_torralba_not_in_active_registry(self):
        """Unverified repository Torralba 2016 metadata must not be present in verified relationships."""
        for rel_id, rel_def in ENVIRONMENTAL_RELATIONSHIPS.items():
            assert "torralba_2016_agroforestry_biodiversity" not in rel_def.evidence_document_ids
            # Verified sources must be FAO or IPCC
            for doc_id in rel_def.evidence_document_ids:
                assert any(k in doc_id for k in ["fao", "ipcc"])


# -----------------------------------------------------------------------------
# 15 & 16. Evaluation Matrix & Conversational Memory Integration
# -----------------------------------------------------------------------------
class TestConversationalScenarioIntegration:
    """Tests multi-turn scenario simulation and memory isolation."""

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_turn_scenario_preserves_baseline_memory(self, mock_session, mock_retriever):
        """Turn 4 what-if query must NOT mutate the established conversational context."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        conv_id = "test_scen_session_001"
        context = EnvironmentalContextManager.get_or_create_context(conv_id)

        # Establish baseline: wheat monoculture, 600 mm, 0.3% SOC
        context.variables["land_use"] = VariableProvenance(
            variable="land_use", value="wheat monoculture", source="user_statement", turn_id=1, timestamp="2026-09-17T00:00:00Z", status=MetricStatus.PROVIDED
        )
        context.variables["rainfall"] = VariableProvenance(
            variable="rainfall", value=600.0, unit="mm", source="user_statement", turn_id=2, timestamp="2026-09-17T00:00:00Z", status=MetricStatus.PROVIDED
        )
        context.variables["soil_organic_carbon"] = VariableProvenance(
            variable="soil_organic_carbon", value=0.3, unit="%", source="user_statement", turn_id=3, timestamp="2026-09-17T00:00:00Z", status=MetricStatus.PROVIDED
        )

        # What-if Turn: "What if I switch from wheat monoculture to intercropping?"
        req = ChatRequest(conversation_id=conv_id, message="What if I switch from wheat monoculture to intercropping?")
        resp = TurnProcessor.process_turn(req)

        assert resp.status == "completed"
        assert "What-If Scenario Analysis" in resp.message
        assert "intercropping" in resp.message.lower()

        # Baseline memory remains wheat monoculture!
        assert context.variables["land_use"].value == "wheat monoculture"
        assert context.variables["rainfall"].value == 600.0
        assert context.variables["soil_organic_carbon"].value == 0.3


# -----------------------------------------------------------------------------
# 17 & 18. REST API Endpoints
# -----------------------------------------------------------------------------
class TestScenarioAPI:
    """Tests /api/v1/scenarios endpoints."""

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_structured_scenario_api(self, mock_session, mock_retriever):
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        payload = {
            "baseline": {"land_use": "wheat monoculture", "rainfall": 600.0, "soil_organic_carbon": 0.3},
            "changes": [
                {
                    "variable": "land_use",
                    "baseline_value": "wheat monoculture",
                    "scenario_value": "intercropping",
                    "change_type": "land_use_change",
                    "status": "assumed_scenario",
                }
            ],
        }
        res = client.post("/api/v1/scenarios/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert len(data["comparison"]["evaluation_matrix"]) > 0

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_natural_language_scenario_api(self, mock_session, mock_retriever):
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        payload = {
            "baseline": {"rainfall": 600.0, "land_use": "wheat monoculture"},
            "query": "What if rainfall decreases by 15%?",
        }
        res = client.post("/api/v1/scenarios/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        matrix = data["comparison"]["evaluation_matrix"]
        assert any(row["metric"] == "soil_moisture" for row in matrix)


# -----------------------------------------------------------------------------
# 19 & 20. Real DB & Zero Fake Fallback Protocol
# -----------------------------------------------------------------------------
@pytest.mark.integration
class TestScenarioZeroFakeFallbackAndRealDB:
    """Verifies that retrieval does not use fake in-memory fallbacks and adheres to Rule 14."""

    def test_real_pgvector_scenario_integration(self):
        """Exercises real PostgreSQL + pgvector + knowledge_chunks + semantic retrieval + scenario analysis."""
        from sqlalchemy import text
        from app.database.connection import engine
        from app.database.models import KnowledgeChunk

        # Verify DB connection and schema explicitly
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                ext = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")).scalar()
                if not ext:
                    pytest.fail("PostgreSQL is reachable but pgvector extension is not installed.")
        except Exception as exc:
            pytest.fail(f"PostgreSQL/pgvector database is not accessible for integration test: {exc}")

        db = SessionLocal()
        try:
            chunk_count = db.query(KnowledgeChunk).count()
            assert chunk_count > 0, "knowledge_chunks must contain ingested embeddings for scenario integration test"

            baseline = {"land_use": "wheat monoculture", "rainfall": 600.0, "soil_organic_carbon": 0.3}
            changes = [
                ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE)
            ]
            comp = ScenarioAnalysisEngine.analyze_scenario(
                baseline=baseline,
                scenario_state={"land_use": "intercropping", "rainfall": 600.0, "soil_organic_carbon": 0.3},
                changes=changes,
                assumptions=["Assume intercropping"],
                db_session=db,
            )
            # Verify confidence is scientifically supported and real evidence was retrieved from PostgreSQL
            assert comp.confidence in ["high", "medium"]
            assert len(comp.evaluation_matrix) > 0
            # Confirm that real grounding evidence was retrieved and utilized
            has_retrieved_evidence = any(
                len(row.evidence_chunk_ids) > 0 for row in comp.evaluation_matrix
            )
            assert has_retrieved_evidence, "Scenario analysis must retrieve and cite real knowledge chunks from PostgreSQL"
        finally:
            db.close()


# -----------------------------------------------------------------------------
# Regression Tests: Scenario Value Loss & Multi-Metric Grounding (Tests A-H)
# -----------------------------------------------------------------------------
class TestScenarioRegressionValueLossAndMultiMetric:
    """Regression test suite for Phase 5 scenario change value preservation and multi-metric grounding."""

    def test_a_numeric_relative_scenario_change(self):
        """TEST A: Numeric relative scenario change preserves -15%, percent unit, relative_change type, no invented absolute rainfall."""
        raw_change = {
            "variable": "rainfall",
            "value": -15,
            "unit": "percent",
            "status": "assumed_scenario",
        }
        change = ScenarioChange(**raw_change)
        assert change.variable == "rainfall"
        assert change.change_value == -15
        assert change.value == -15
        assert change.unit == "percent"
        assert change.status == "assumed_scenario"
        assert change.change_type == ScenarioType.RELATIVE_CHANGE
        # No invented absolute rainfall when baseline is unknown
        assert change.scenario_value is None
        assert change.baseline_value is None
        assert "cannot be calculated without a baseline" in change.notes

    def test_b_categorical_scenario_change(self):
        """TEST B: Categorical scenario change preserves intercropping, categorical_change type, assumed_scenario status."""
        raw_change = {
            "variable": "land_use",
            "value": "intercropping",
            "status": "assumed_scenario",
        }
        change = ScenarioChange(**raw_change)
        assert change.variable == "land_use"
        assert change.scenario_value == "intercropping"
        assert change.value == "intercropping"
        assert change.status == "assumed_scenario"
        assert change.change_type in (ScenarioType.CATEGORICAL_CHANGE, ScenarioType.LAND_USE_CHANGE)

    def test_c_combined_scenario_preserves_both_values(self):
        """TEST C: Combined scenario preserves both rainfall -15% and land_use = intercropping end-to-end."""
        payload = {
            "query": "What if rainfall decreases by 15% and we transition to intercropping?",
            "changes": [
                {
                    "variable": "rainfall",
                    "value": -15,
                    "unit": "percent",
                    "status": "assumed_scenario",
                },
                {
                    "variable": "land_use",
                    "value": "intercropping",
                    "status": "assumed_scenario",
                },
            ],
        }
        req = ScenarioAnalysisRequest(**payload)
        assert len(req.changes) == 2

        rain_ch = next(c for c in req.changes if c.variable == "rainfall")
        land_ch = next(c for c in req.changes if c.variable == "land_use")

        assert rain_ch.change_value == -15
        assert rain_ch.unit == "percent"
        assert rain_ch.scenario_value is None

        assert land_ch.scenario_value == "intercropping"
        assert land_ch.status == "assumed_scenario"

        # Check state builder output
        scen_state, assumptions = ScenarioStateBuilder.build_scenario_state({}, req.changes)
        assert scen_state.get("land_use") == "intercropping"
        assert scen_state.get("rainfall") is None
        # Assumptions must not contain None percent
        assert not any("None percent" in a for a in assumptions)
        assert any("decreases by 15%" in a or "-15%" in a for a in assumptions)
        assert any("intercropping" in a for a in assumptions)

    def test_d_baseline_plus_relative_change_calculates_deterministic_scenario_value(self):
        """TEST D: Baseline 600 mm + relative change -15% calculates deterministic scenario value 510 mm."""
        payload = {
            "baseline": {"rainfall": 600.0},
            "changes": [
                {
                    "variable": "rainfall",
                    "value": -15,
                    "unit": "percent",
                    "status": "assumed_scenario",
                }
            ],
        }
        with patch("app.scenarios.analyzer.KnowledgeRetriever") as mock_retriever, \
             patch("app.scenarios.analyzer.SessionLocal") as mock_session:
            mock_retriever_inst = MagicMock()
            mock_retriever.return_value = mock_retriever_inst
            mock_res = MagicMock()
            mock_res.results = []
            mock_retriever_inst.search.return_value = mock_res

            res = client.post("/api/v1/scenarios/analyze", json=payload)
            assert res.status_code == 200
            data = res.json()
            comp = data["comparison"]
            rain_ch = next(c for c in comp["changed_variables"] if c["variable"] == "rainfall")
            assert rain_ch["baseline_value"] == 600.0
            assert rain_ch["scenario_value"] == 510.0
            assert comp["scenario_summary"]["rainfall"] == 510.0

    def test_e_unknown_baseline_does_not_invent_absolute_rainfall(self):
        """TEST E: Unknown baseline with -15% rainfall does NOT invent absolute scenario rainfall."""
        payload = {
            "changes": [
                {
                    "variable": "rainfall",
                    "value": -15,
                    "unit": "percent",
                    "status": "assumed_scenario",
                }
            ],
        }
        with patch("app.scenarios.analyzer.KnowledgeRetriever") as mock_retriever, \
             patch("app.scenarios.analyzer.SessionLocal") as mock_session:
            mock_retriever_inst = MagicMock()
            mock_retriever.return_value = mock_retriever_inst
            mock_res = MagicMock()
            mock_res.results = []
            mock_retriever_inst.search.return_value = mock_res

            res = client.post("/api/v1/scenarios/analyze", json=payload)
            assert res.status_code == 200
            data = res.json()
            comp = data["comparison"]
            rain_ch = next(c for c in comp["changed_variables"] if c["variable"] == "rainfall")
            assert rain_ch["baseline_value"] is None
            assert rain_ch["scenario_value"] is None
            assert rain_ch["change_value"] == -15
            assert comp["scenario_summary"].get("rainfall") is None

    @pytest.mark.integration
    def test_f_evidence_grounding_consumes_real_pgvector_without_fallback(self):
        """TEST F: Scenario reasoning consumes retrieved evidence from PostgreSQL/pgvector without fallback."""
        from app.database.connection import SessionLocal
        from app.database.models import KnowledgeChunk
        db = SessionLocal()
        try:
            assert db.query(KnowledgeChunk).count() > 0
            changes = [
                ScenarioChange(variable="rainfall", value=-15, change_value=-15, unit="percent", change_type=ScenarioType.RELATIVE_CHANGE),
                ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE),
            ]
            comp = ScenarioAnalysisEngine.analyze_scenario(
                baseline={},
                scenario_state={"rainfall": None, "land_use": "intercropping"},
                changes=changes,
                assumptions=["Assume rainfall decreases by 15%", "Assume land use is intercropping"],
                db_session=db,
            )
            assert len(comp.evidence) > 0
            # Confirm chunks come from real database
            retrieved_chunk_ids = [e["chunk_id"] for e in comp.evidence if "chunk_id" in e]
            assert len(retrieved_chunk_ids) > 0
            # Relationships are discovered and mapped
            assert len(comp.relationships) > 0
        finally:
            db.close()

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_g_no_false_three_variable_claim(self, mock_session, mock_retriever):
        """TEST G: If state/changes support only two variables (rainfall and land_use), multi_metric_grounding must remain False."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        changes = [
            ScenarioChange(variable="rainfall", value=-15, change_value=-15, unit="percent", change_type=ScenarioType.RELATIVE_CHANGE),
            ScenarioChange(variable="land_use", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE),
        ]
        comp = ScenarioAnalysisEngine.analyze_scenario(
            baseline={},
            scenario_state={"rainfall": None, "land_use": "intercropping"},
            changes=changes,
            assumptions=["Assume rainfall decreases by 15%", "Assume land use is intercropping"],
        )
        assert comp.multi_metric_grounding is False
        assert "limited" in comp.multi_metric_coverage.lower()

    @patch("app.scenarios.analyzer.KnowledgeRetriever")
    @patch("app.scenarios.analyzer.SessionLocal")
    def test_h_supported_multi_variable_relationship(self, mock_session, mock_retriever):
        """TEST H: When 3 variables (soil_organic_carbon, rainfall, land_use) are genuinely present, engine reports compound multi-metric grounding."""
        mock_retriever_inst = MagicMock()
        mock_retriever.return_value = mock_retriever_inst
        mock_res = MagicMock()
        mock_res.results = []
        mock_retriever_inst.search.return_value = mock_res

        baseline = {"land_use": "wheat monoculture", "rainfall": 600.0, "soil_organic_carbon": 0.3}
        scen_state = {"land_use": "intercropping", "rainfall": 510.0, "soil_organic_carbon": 0.8}
        changes = [
            ScenarioChange(variable="rainfall", baseline_value=600.0, scenario_value=510.0, change_value=-15, unit="percent", change_type=ScenarioType.RELATIVE_CHANGE),
            ScenarioChange(variable="land_use", baseline_value="wheat monoculture", scenario_value="intercropping", change_type=ScenarioType.LAND_USE_CHANGE),
            ScenarioChange(variable="soil_organic_carbon", baseline_value=0.3, scenario_value=0.8, change_type=ScenarioType.METRIC_CHANGE),
        ]
        comp = ScenarioAnalysisEngine.analyze_scenario(
            baseline=baseline,
            scenario_state=scen_state,
            changes=changes,
            assumptions=["Assume 3 variables present"],
        )
        assert comp.multi_metric_grounding is True
        assert "compound" in comp.multi_metric_coverage.lower()

    def test_i_live_three_variable_scenario_request_no_name_error(self):
        """TEST I: Verifies that 3-variable baseline payload (SOC, rainfall, land_use) executes without NameError."""
        payload = {
            "query": "What if rainfall decreases by 15% and we transition from wheat monoculture to intercropping?",
            "baseline": {
                "soil_organic_carbon": 0.3,
                "rainfall": 600,
                "land_use": "wheat monoculture"
            },
            "changes": [
                {
                    "variable": "rainfall",
                    "value": -15,
                    "unit": "percent",
                    "status": "assumed_scenario"
                },
                {
                    "variable": "land_use",
                    "value": "intercropping",
                    "status": "assumed_scenario"
                }
            ]
        }
        with patch("app.scenarios.analyzer.KnowledgeRetriever") as mock_retriever, \
             patch("app.scenarios.analyzer.SessionLocal") as mock_session:
            mock_retriever_inst = MagicMock()
            mock_retriever.return_value = mock_retriever_inst
            mock_res = MagicMock()
            mock_res.results = []
            mock_retriever_inst.search.return_value = mock_res

            res = client.post("/api/v1/scenarios/analyze", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "completed"
            comp = data["comparison"]

            rain_ch = next(c for c in comp["changed_variables"] if c["variable"] == "rainfall")
            assert rain_ch["baseline_value"] == 600
            assert rain_ch["scenario_value"] == 510.0
            assert rain_ch["change_value"] == -15
            assert rain_ch["unit"] == "percent"
            assert rain_ch["change_type"] == "relative_change"

            land_ch = next(c for c in comp["changed_variables"] if c["variable"] == "land_use")
            assert land_ch["baseline_value"] == "wheat monoculture"
            assert land_ch["scenario_value"] == "intercropping"
            assert land_ch["change_type"] == "categorical_change"

            assert comp["baseline_summary"]["soil_organic_carbon"] == 0.3
            assert comp["scenario_summary"]["soil_organic_carbon"] == 0.3
            assert comp["scenario_summary"]["rainfall"] == 510.0
            assert comp["scenario_summary"]["land_use"] == "intercropping"
            assert comp["multi_metric_grounding"] is True
            assert "compound" in comp["multi_metric_coverage"].lower()
