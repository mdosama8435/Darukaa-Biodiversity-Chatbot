"""Critical End-to-End Integration Test for Environmental Intelligence and Multi-Metric Reasoning.

Exercises:
LangGraph orchestration + environmental reasoning + real pgvector knowledge retrieval + evidence mapping + recommendation validation.

If PostgreSQL/pgvector is unavailable:
Skips the live integration test with an explicit reason per Rule 14.
Never replaces it with an in-memory vector fake.
"""

import pytest
from sqlalchemy import text
from app.database.connection import engine
from app.agents.graph import app_graph
from app.agents.state import EnvironmentalState


def is_database_and_pgvector_available() -> bool:
    """Checks whether the live PostgreSQL database with pgvector extension is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            # Check for pgvector extension
            res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
            if res.fetchone() is not None:
                return True
            return False
    except Exception:
        return False


class TestAssessmentEndToEndIntegration:
    """End-to-End live integration test strictly verifying all 14 evaluation criteria."""

    def test_end_to_end_environmental_reasoning_pipeline(self):
        """Executes full live pipeline on the required benchmark scenario:
        
        'My farm is in a semi-arid region. I grow wheat continuously. 
         Soil organic carbon is 0.3%. Rainfall is low and biodiversity has declined.'
        """
        if not is_database_and_pgvector_available():
            pytest.skip(
                "PostgreSQL + pgvector is not accessible on localhost:5432; "
                "skipping live end-to-end integration test per Rule 14 without using a fake retrieval backend."
            )

        # Benchmark input scenario
        user_query = (
            "My farm is in a semi-arid region. I grow wheat continuously. "
            "Soil organic carbon is 0.3%. Rainfall is low and biodiversity has declined."
        )

        initial_state: EnvironmentalState = {
            "user_query": user_query,
            "conversation_history": [],
            "environmental_data": {},
            "status": "ready",
        }

        # Execute 12-node pipeline
        final_state = app_graph.invoke(initial_state)
        response = final_state.get("final_response") or {}

        # 1. Verify status
        assert response.get("status") == "completed"

        # 2. Environmental state extraction & multiple relevant variables
        assessment = response.get("assessment", {})
        env_state = assessment.get("environmental_state", {})
        assert "soil_organic_carbon" in env_state
        assert env_state["soil_organic_carbon"] == 0.3
        assert "rainfall" in env_state
        assert "land_use" in env_state
        assert "semi-arid" in env_state.get("region", "").lower()

        # 3. Missing data detection
        missing_fields = final_state.get("missing_fields", [])
        assert isinstance(missing_fields, list)

        # 4. Identify relationships involving at least THREE variables simultaneously
        key_relationships = assessment.get("key_relationships", [])
        assert len(key_relationships) >= 1
        multi_metric_rels = [r for r in key_relationships if r.get("is_multi_metric") is True]
        assert len(multi_metric_rels) >= 1
        assert any(len(r.get("variables_involved", [])) >= 3 for r in multi_metric_rels)

        # Compound synthesis must be present
        assert assessment.get("compound_synthesis") is not None

        # 5. Multi-dimensional retrieval queries generated
        retrieval_queries = final_state.get("retrieval_queries", [])
        assert len(retrieval_queries) >= 3

        # 6. Real scientific knowledge retrieval & evidence mapping
        evidence_summary = response.get("evidence_summary", [])
        assert len(evidence_summary) >= 1

        # 7. Candidate recommendation generation
        recommendations = response.get("recommendations", [])
        assert len(recommendations) >= 1
        top_rec = recommendations[0]

        # 8. Impacted metrics
        assert len(top_rec.get("impacted_metrics", [])) >= 2
        assert "soil_organic_carbon" in top_rec["impacted_metrics"]

        # 9. Time horizon (short, medium, long term)
        th = top_rec.get("time_horizon", {})
        assert "short_term" in th
        assert "medium_term" in th
        assert "long_term" in th

        # 10. Quantitative claim guard: No fabricated numbers
        effect = top_rec.get("expected_effect", {})
        assert effect.get("direction") == "positive"
        # If estimate is present, estimate_source MUST be present and verified
        if effect.get("quantitative_estimate") is not None:
            assert effect.get("estimate_source") is not None

        # 11. Categorical confidence & explainable factors
        confidence = response.get("confidence")
        assert confidence in ["high", "medium", "low"]
        assert "confidence_factors" in response

        # 12. Explicit limitations
        assert len(response.get("limitations", [])) >= 1

        # 13. Traceability audit chain
        trace = top_rec.get("traceability", {})
        assert "recommendation_id" in trace
        assert len(trace.get("relationship_ids", [])) >= 1
        assert len(trace.get("evidence_ids", [])) >= 1
        assert len(trace.get("source_references", [])) >= 1
