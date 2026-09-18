"""Tests for environmental models, LangGraph skeleton, database schema, and LLM abstraction."""

import pytest
from pydantic import ValidationError

from app.models.environmental import (
    SoilData,
    ClimateData,
    LandData,
    BiodiversityData,
    HumanImpactData,
    LocationData,
    EnvironmentalData,
)
from app.agents.graph import app_graph
from app.database.models import (
    User,
    Conversation,
    Message,
    EnvironmentalAssessment,
    KnowledgeDocument,
    KnowledgeChunk,
    Evidence,
    Recommendation,
    get_vector_type,
)
from app.services.llm_service import get_llm_service


class TestEnvironmentalModels:
    """Validation test suite for environmental parameters."""

    def test_soil_validation(self):
        """Validates soil pH bounds (0 to 14) and moisture constraints."""
        valid_soil = SoilData(soil_ph=6.5, soil_organic_carbon=2.4, soil_moisture=28.0)
        assert valid_soil.soil_ph == 6.5

        # Invalid pH > 14 should raise ValidationError
        with pytest.raises(ValidationError):
            SoilData(soil_ph=14.5)

        # Invalid negative pH should raise ValidationError
        with pytest.raises(ValidationError):
            SoilData(soil_ph=-0.5)

    def test_climate_validation(self):
        """Validates climate boundaries."""
        valid_climate = ClimateData(temperature=24.5, rainfall=1200.0)
        assert valid_climate.temperature == 24.5

        # Negative rainfall must fail
        with pytest.raises(ValidationError):
            ClimateData(rainfall=-10.0)

    def test_location_validation(self):
        """Validates geographic coordinates."""
        valid_loc = LocationData(region="Western Ghats", latitude=11.25, longitude=75.78)
        assert valid_loc.region == "Western Ghats"

        with pytest.raises(ValidationError):
            LocationData(latitude=95.0)  # Exceeds +90

        with pytest.raises(ValidationError):
            LocationData(longitude=-185.0)  # Exceeds -180

    def test_missing_fields_and_completeness(self):
        """Verifies missing fields detection for conversational clarification."""
        env = EnvironmentalData(
            soil=SoilData(soil_ph=6.2),
            climate=ClimateData(temperature=26.0),
        )

        flat = env.to_flat_dict()
        assert flat["soil_ph"] == 6.2
        assert flat["temperature"] == 26.0
        assert flat["rainfall"] is None

        provided = env.get_provided_fields()
        assert "soil_ph" in provided
        assert "temperature" in provided
        assert "rainfall" not in provided

        missing = env.get_missing_fields(["soil_ph", "rainfall", "soil_moisture"])
        assert "rainfall" in missing
        assert "soil_moisture" in missing
        assert "soil_ph" not in missing

        score = env.completeness_score(["soil_ph", "rainfall"])
        assert score == 0.5


class TestLangGraphSkeleton:
    """Verifies that LangGraph compiles and runs the initial skeleton."""

    def test_graph_execution(self):
        """Runs the initial 3-node graph skeleton."""
        initial_state = {
            "user_query": "What is the recommended cover crop for acidic soil?",
            "environmental_data": {"soil_ph": 5.2, "temperature": 22.0},
        }

        result = app_graph.invoke(initial_state)

        assert result["user_query"] == "What is the recommended cover crop for acidic soil?"
        assert result["environmental_data"]["soil_ph"] == 5.2
        assert isinstance(result["missing_fields"], list)
        assert "rainfall" in result["missing_fields"]


class TestDatabaseSchema:
    """Verifies conceptual entities and dynamic vector column."""

    def test_vector_column_dimension_configurability(self):
        """Ensures vector dimension is configurable and not locked to 384."""
        v_dynamic = get_vector_type(None)
        assert str(v_dynamic) == "VECTOR"

        v_custom = get_vector_type(768)
        assert str(v_custom) == "VECTOR(768)"

    def test_entities_instantiation(self):
        """Verifies that all 8 required entities instantiate cleanly."""
        user = User(email="scientist@darukaa.earth", full_name="Dr. Aranya")
        conv = Conversation(title="Ecosystem Assessment")
        msg = Message(role="user", content="Analyzing Western Ghats plot")
        assessment = EnvironmentalAssessment(soil_ph=5.8, temperature=24.0)
        doc = KnowledgeDocument(title="Soil Microbiome Restoration in Tropical Forests", doi="10.1000/182")
        chunk = KnowledgeChunk(chunk_index=0, content="Restoring native mycorrhizae...")
        evidence = Evidence(claim_summary="Mycorrhizal inoculation boosts SOC", scientific_fact="Fact text")
        rec = Recommendation(action_title="Apply biochar and mycorrhizae", action_description="Detail")

        assert user.email == "scientist@darukaa.earth"
        assert assessment.soil_ph == 5.8
        assert rec.action_title == "Apply biochar and mycorrhizae"


class TestLLMServiceAbstraction:
    """Verifies provider-agnostic LLM abstraction behavior."""

    def test_unconfigured_provider_fails_explicitly(self):
        """Ensures that omitting provider configuration raises a ValueError without fake output."""
        with pytest.raises(ValueError, match="No LLM provider configured"):
            get_llm_service(provider="")

    def test_unsupported_provider_fails_explicitly(self):
        """Ensures unsupported provider names fail cleanly."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            get_llm_service(provider="unknown_provider")
