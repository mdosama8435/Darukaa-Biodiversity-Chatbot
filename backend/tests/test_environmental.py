"""Unit tests for Environmental Intelligence models, relationship graph, and multi-metric analyzer."""

import pytest
from app.models.environmental import EnvironmentalData
from app.environmental.schemas import RelationshipType, RelationshipDirection
from app.environmental.relationships import ENVIRONMENTAL_RELATIONSHIPS
from app.environmental.relationship_graph import EnvironmentalRelationshipGraph
from app.environmental.metric_rules import classify_metric
from app.environmental.analyzer import EnvironmentalRelationshipAnalyzer
from app.agents.graph import _extract_from_text, extract_environmental_state


class TestEnvironmentalStateAndExtraction:
    """Tests for state extraction, missing data detection, and multi-turn merging."""

    def test_unknown_not_coerced_to_zero(self):
        """Crucial test: UNKNOWN != ZERO. Missing values must remain None."""
        data = {"soil_organic_carbon": 0.3}
        env = EnvironmentalData.from_flat_or_nested(data)
        flat = env.to_flat_dict()

        assert flat["soil_organic_carbon"] == 0.3
        assert flat["soil_ph"] is None
        assert flat["rainfall"] is None
        assert flat["soil_moisture"] is None

        # Ensure missing fields correctly detected
        missing = env.get_missing_fields()
        assert "soil_ph" in missing
        assert "rainfall" in missing
        assert "soil_organic_carbon" not in missing

    def test_text_extraction_deterministic(self):
        """Tests deterministic variable extraction from natural language."""
        text = (
            "My farm is in a semi-arid region. I grow wheat continuously. "
            "Soil organic carbon is 0.3%. Rainfall is low and biodiversity has declined."
        )
        extracted = _extract_from_text(text)

        assert extracted["soil_organic_carbon"] == 0.3
        assert extracted["land_use"] == "continuous wheat cropping"
        assert extracted["rainfall"] == 400.0  # Heuristic low rainfall
        assert "semi-arid" in extracted["region"]

    def test_multi_turn_state_merge(self):
        """Tests that state across dialogue turns merges cleanly without resetting prior parameters."""
        history = [
            {"environmental_data": {"soil_organic_carbon": 0.4, "region": "semi-arid Bihar"}},
            {"environmental_data": {"land_use": "wheat monoculture"}},
        ]
        state = {
            "conversation_history": history,
            "environmental_data": {"rainfall": 500.0},
            "user_query": "",
        }
        res = extract_environmental_state(state)
        merged = res["environmental_data"]

        assert merged["soil_organic_carbon"] == 0.4
        assert merged["region"] == "semi-arid Bihar"
        assert merged["land_use"] == "wheat monoculture"
        assert merged["rainfall"] == 500.0


class TestRelationshipGraphAndHeuristics:
    """Tests for relationship registry, structured provenance, and heuristic classifications."""

    def test_all_relationships_have_structured_provenance(self):
        """Verification of Correction 3: Every relationship must have structured literature provenance."""
        for rel_id, rel in ENVIRONMENTAL_RELATIONSHIPS.items():
            assert rel.relationship_id == rel_id
            assert len(rel.variables) >= 2
            assert len(rel.evidence_document_ids) >= 1, f"Missing evidence_document_ids in {rel_id}"
            assert len(rel.source_urls) >= 1, f"Missing source_urls in {rel_id}"
            assert len(rel.doi) >= 1, f"Missing DOI in {rel_id}"

    def test_metric_classification_is_heuristic(self):
        """Verification of Correction 4: Metric classification must be labeled as heuristic with limitations."""
        soc_cls = classify_metric("soil_organic_carbon", 0.3)
        assert soc_cls is not None
        assert soc_cls.classification == "depleted_low"
        assert soc_cls.basis == "context-dependent heuristic"
        assert len(soc_cls.limitations) >= 1

        rain_cls = classify_metric("rainfall", 450.0)
        assert rain_cls is not None
        assert "water_limited" in rain_cls.classification
        assert rain_cls.basis == "context-dependent heuristic"

        # None value returns None (UNKNOWN != ZERO)
        assert classify_metric("soil_ph", None) is None


class TestMultiMetricReasoning:
    """Tests for multi-metric compound reasoning over at least 3 environmental variables simultaneously."""

    def test_three_variable_compound_relationship_detected(self):
        """Verification of Correction 7: Analyzes compound interaction of SOC + Rainfall + Land Use."""
        payload = {
            "soil_organic_carbon": 0.3,
            "rainfall": 450.0,
            "land_use": "wheat monoculture",
            "region": "semi-arid",
        }
        analyzer = EnvironmentalRelationshipAnalyzer()
        active_rels, classifications, summary = analyzer.analyze(payload)

        # Must detect multi-metric relationships
        assert summary["multi_metric_relationships_count"] >= 1

        # Check for the specific 3-variable compound interaction
        soc_rain_monoculture = next(
            (r for r in active_rels if r.relationship_id == "soc_rainfall_monoculture_stress"),
            None,
        )
        assert soc_rain_monoculture is not None
        assert soc_rain_monoculture.is_multi_metric is True
        assert set(soc_rain_monoculture.variables_involved) == {"soil_organic_carbon", "rainfall", "land_use"}

        # Check that compound synthesis text was generated
        assert summary["compound_synthesis"] is not None
        assert "COMPOUND MULTI-METRIC INTERACTION" in summary["compound_synthesis"]
        assert "depleted soil carbon" in summary["compound_synthesis"].lower()
        assert "monoculture" in summary["compound_synthesis"].lower()
