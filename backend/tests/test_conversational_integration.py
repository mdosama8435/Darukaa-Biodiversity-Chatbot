"""Critical End-to-End Multi-Turn Conversational Integration Test.

Strictly verifies the requested 4-turn demonstration scenario:
- TURN 1: 'My biodiversity has been declining.' -> targeted clarification.
- TURN 2: 'I grow wheat continuously and rainfall is around 600 mm.' -> land_use and rainfall added.
- TURN 3: 'My soil organic carbon is 0.3%.' -> SOC added, merged state retains all 4 metrics, Phase 3 executes.
- TURN 4: 'Actually, I switched from wheat to maize this year.' -> land_use updated to maize, rainfall and SOC retained, reassessment executes.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.conversation.context_manager import EnvironmentalContextManager
from app.rag.schemas import KnowledgeSearchResponse, KnowledgeSearchResultItem

client = TestClient(app)


def get_mock_retrieval_response() -> KnowledgeSearchResponse:
    """Provides authentic literature chunks for isolated retrieval boundary."""
    items = [
        KnowledgeSearchResultItem(
            chunk_id=1,
            document_id=1,
            title="FAO State of Knowledge of Soil Biodiversity (2020)",
            source="FAO",
            doi="10.4060/cb1924en",
            url="https://doi.org/10.4060/cb1924en",
            page_number=2,
            section="2. Soil Organic Carbon Driver",
            content="Scientific evidence syntheses demonstrate that soils with elevated levels of soil organic carbon (SOC > 2.0%) maintain significantly greater total microbial biomass.",
            similarity=0.86,
            variables=["soil_organic_carbon", "species_richness"],
            topics=["soil", "biodiversity"],
        ),
        KnowledgeSearchResultItem(
            chunk_id=2,
            document_id=2,
            title="Agroforestry and Soil Health Meta-Analysis",
            source="Research Paper",
            doi="10.1016/j.agee.2016.06.002",
            url="https://doi.org/10.1016/j.agee.2016.06.002",
            publication_year=2016,
            page_number=1,
            section="Overview",
            content="Compared with conventional monoculture crop production, agroforestry systems increase total soil organic carbon stocks by an average of 19% and enhance species richness.",
            similarity=0.84,
            variables=["land_use", "soil_organic_carbon", "species_richness"],
            topics=["agriculture", "soil", "biodiversity"],
        ),
    ]
    return KnowledgeSearchResponse(query="multi-metric test", results_count=len(items), results=items)


class TestCriticalMultiTurnScenario:
    """Executes the exact 4-turn conversational scenario."""

    def test_four_turn_conversational_lifecycle(self):
        conv_id = "test_critical_4turn_demo"

        # Ensure fresh start
        if conv_id in EnvironmentalContextManager._MEMORY_STORE:
            del EnvironmentalContextManager._MEMORY_STORE[conv_id]

        mock_search_res = get_mock_retrieval_response()

        with patch("app.agents.graph.SessionLocal") as mock_session_local, \
             patch("app.agents.graph.KnowledgeRetriever.search", return_value=mock_search_res):
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session

            # -----------------------------------------------------------------
            # TURN 1: "My biodiversity has been declining."
            # -----------------------------------------------------------------
            t1_res = client.post("/api/v1/chat", json={
                "conversation_id": conv_id,
                "message": "My biodiversity has been declining.",
            })
            assert t1_res.status_code == 200
            t1_data = t1_res.json()

            assert t1_data["status"] == "clarification_needed"
            assert len(t1_data["clarification_questions"]) >= 1
            assert "habitat_diversity" in t1_data["environmental_context"]
            assert t1_data["environmental_context"]["habitat_diversity"]["value"] == "low"

            # -----------------------------------------------------------------
            # TURN 2: "I grow wheat continuously and rainfall is around 600 mm."
            # -----------------------------------------------------------------
            t2_res = client.post("/api/v1/chat", json={
                "conversation_id": conv_id,
                "message": "I grow wheat continuously and rainfall is around 600 mm.",
            })
            assert t2_res.status_code == 200
            t2_data = t2_res.json()

            ctx2 = t2_data["environmental_context"]
            assert "land_use" in ctx2
            assert ctx2["land_use"]["value"] == "wheat continuous cropping"
            assert "rainfall" in ctx2
            assert ctx2["rainfall"]["value"] == 600.0
            # Biodiversity indicator from Turn 1 must still be retained!
            assert "habitat_diversity" in ctx2
            assert ctx2["habitat_diversity"]["value"] == "low"

            # -----------------------------------------------------------------
            # TURN 3: "My soil organic carbon is 0.3%."
            # -----------------------------------------------------------------
            t3_res = client.post("/api/v1/chat", json={
                "conversation_id": conv_id,
                "message": "My soil organic carbon is 0.3%.",
            })
            assert t3_res.status_code == 200
            t3_data = t3_res.json()

            # Merged state must retain all 4 parameters:
            ctx3 = t3_data["environmental_context"]
            assert ctx3["habitat_diversity"]["value"] == "low"
            assert ctx3["land_use"]["value"] == "wheat continuous cropping"
            assert ctx3["rainfall"]["value"] == 600.0
            assert ctx3["soil_organic_carbon"]["value"] == 0.3

            # Status must now be completed with Phase 3 execution!
            assert t3_data["status"] == "completed"
            assert t3_data["assessment"] is not None

            # Verify Phase 3 reasoning elements:
            assessment = t3_data["assessment"]
            # 1. Multi-metric relationship
            recs = assessment.get("recommendations", [])
            assert len(recs) >= 1
            top_rec = recs[0]
            assert len(top_rec.get("environmental_reasoning", [])) >= 1
            # 2. Evidence
            assert len(assessment.get("evidence_summary", [])) >= 1
            # 3. Confidence
            assert t3_data.get("confidence") in ["high", "medium", "low"]
            # 4. Traceability
            assert "traceability" in top_rec
            assert len(top_rec["traceability"]["relationship_ids"]) >= 1

            # -----------------------------------------------------------------
            # TURN 4: "Actually, I switched from wheat to maize this year."
            # -----------------------------------------------------------------
            t4_res = client.post("/api/v1/chat", json={
                "conversation_id": conv_id,
                "message": "Actually, I switched from wheat to maize this year.",
            })
            assert t4_res.status_code == 200
            t4_data = t4_res.json()

            ctx4 = t4_data["environmental_context"]

            # Land use must be updated to maize!
            assert ctx4["land_use"]["value"] == "maize"
            assert ctx4["land_use"]["status"] == "updated"

            # Rainfall and SOC must remain unchanged!
            assert ctx4["rainfall"]["value"] == 600.0
            assert ctx4["soil_organic_carbon"]["value"] == 0.3

            # Detected updates must record the transition
            assert len(t4_data["detected_updates"]) >= 1
            lu_up = next((u for u in t4_data["detected_updates"] if u["variable"] == "land_use"), None)
            assert lu_up is not None
            assert lu_up["old_value"] == "wheat continuous cropping"
            assert lu_up["new_value"] == "maize"

            # Re-assessment completed with updated state
            assert t4_data["status"] == "completed"
            assert t4_data["assessment"] is not None
