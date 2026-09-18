"""API route tests for POST /api/v1/assessment."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAssessmentAPIEndpoints:
    """Tests for API endpoint /api/v1/assessment."""

    def test_clarification_response_when_critical_metrics_missing(self):
        """When query lacks all critical variables, returns needs_clarification with questions (Requirement 21)."""
        payload = {
            "query": "My biodiversity is declining. What should I do?"
        }
        response = client.post("/api/v1/assessment", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "needs_clarification"
        assert len(data["questions"]) >= 2
        assert "missing_fields" in data
        assert any("rainfall" in q.lower() or "cropping" in q.lower() or "soil" in q.lower() for q in data["questions"])

    @patch("app.agents.graph.KnowledgeRetriever")
    def test_infrastructure_error_on_db_unavailable(self, mock_retriever_class):
        """Correction 1: When PostgreSQL/pgvector is unavailable, fails explicitly with HTTP 503."""
        mock_retriever = mock_retriever_class.return_value
        mock_retriever.search.side_effect = RuntimeError("Connection refused")

        payload = {
            "soil_organic_carbon": 0.3,
            "rainfall": 500.0,
            "land_use": "wheat monoculture",
            "region": "semi-arid",
        }

        # Verify 503 is returned when DB retrieval fails per Correction 1
        response = client.post("/api/v1/assessment", json=payload)
        assert response.status_code == 503
        assert "retrieval failed" in response.json()["detail"] or "Connection refused" in response.json()["detail"]

    def test_structured_json_assessment_successful_with_mocked_db_boundary(self):
        """Tests that structured environmental JSON payload executes through the pipeline and produces valid assessment."""
        from app.rag.schemas import KnowledgeSearchResponse, KnowledgeSearchResultItem
        from unittest.mock import MagicMock

        payload = {
            "soil_organic_carbon": 0.3,
            "rainfall": 500.0,
            "land_use": "wheat monoculture",
            "region": "semi-arid",
        }

        mocked_items = [
            KnowledgeSearchResultItem(
                chunk_id=1,
                document_id=1,
                title="FAO Soil Biodiversity Report 2020",
                source="FAO",
                doi="10.4060/cb1924en",
                url="https://doi.org/10.4060/cb1924en",
                page_number=2,
                section="2. Soil Organic Carbon Driver",
                content="Soils with depleted SOC beneath 0.8% trigger cascading microflora starvation.",
                similarity=0.85,
                variables=["soil_organic_carbon", "species_richness"],
                topics=["soil", "biodiversity"],
            ),
            KnowledgeSearchResultItem(
                chunk_id=2,
                document_id=2,
                title="Agroforestry Meta-Analysis",
                source="Research Paper",
                doi="10.1016/j.agee.2016.06.002",
                url="https://doi.org/10.1016/j.agee.2016.06.002",
                page_number=1,
                section="Overview",
                content="Agroforestry systems create heterogeneous ecological niches and improve water infiltration.",
                similarity=0.82,
                variables=["land_use", "soil_moisture", "species_richness"],
                topics=["agriculture", "biodiversity"],
            ),
        ]

        mock_response = KnowledgeSearchResponse(
            query="test",
            results_count=len(mocked_items),
            results=mocked_items,
        )

        with patch("app.agents.graph.SessionLocal") as mock_session_local, \
             patch("app.agents.graph.KnowledgeRetriever.search", return_value=mock_response):
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session

            response = client.post("/api/v1/assessment", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert "assessment" in data
            assert len(data["recommendations"]) >= 1
            assert "confidence" in data
            assert data["confidence"] in ["high", "medium", "low"]
            assert "confidence_factors" in data

            # Verify multi-metric compound reasoning in recommendations
            top_rec = data["recommendations"][0]
            assert "environmental_reasoning" in top_rec
            assert len(top_rec["environmental_reasoning"]) >= 1

            # Verify traceability chain
            assert "traceability" in top_rec
            assert len(top_rec["traceability"]["relationship_ids"]) >= 1
            assert len(top_rec["traceability"]["evidence_ids"]) >= 1
