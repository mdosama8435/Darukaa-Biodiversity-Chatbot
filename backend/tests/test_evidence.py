"""Unit tests for multi-dimensional query building, evidence scoring, mapping, and validation."""

import pytest
from app.rag.query_builder import MultiDimensionalQueryBuilder
from app.environmental.analyzer import EnvironmentalRelationshipAnalyzer
from app.evidence.scoring import (
    compute_evidence_score,
    WEIGHT_SEMANTIC,
    WEIGHT_METADATA,
    WEIGHT_RELATIONSHIP,
    WEIGHT_SOURCE_QUALITY,
)
from app.evidence.mapper import EvidenceMapper
from app.evidence.validator import EvidenceValidator
from app.evidence.schemas import EvidenceItem


class TestMultiDimensionalQueryBuilder:
    """Tests that retrieval queries reflect multi-variable ecological relationships."""

    def test_query_builder_avoids_naive_concatenation(self):
        """Query builder should produce focused, scientific queries rather than blind concatenation."""
        env_data = {
            "soil_organic_carbon": 0.3,
            "rainfall": 450.0,
            "land_use": "wheat monoculture",
            "region": "semi-arid",
        }
        analyzer = EnvironmentalRelationshipAnalyzer()
        active_rels, _, _ = analyzer.analyze(env_data)

        queries = MultiDimensionalQueryBuilder.build_queries(
            environmental_data=env_data,
            active_relationships=active_rels,
            max_queries=6,
        )

        assert len(queries) >= 3
        # Should not be a single giant string of all variables
        for q in queries:
            assert len(q.split()) >= 4
            assert len(q) < 150

        # Check for meaningful multi-variable themes
        has_soc_query = any("soil organic carbon" in q.lower() for q in queries)
        has_rain_query = any("rainfall" in q.lower() or "water" in q.lower() or "moisture" in q.lower() for q in queries)
        has_crop_query = any("cropping" in q.lower() or "monoculture" in q.lower() or "agroforestry" in q.lower() for q in queries)

        assert has_soc_query is True
        assert has_rain_query is True
        assert has_crop_query is True


class TestEvidenceScoringAndMapping:
    """Tests for transparent scoring weights and evidence mapping."""

    def test_evidence_scoring_formula(self):
        """Validates explicit mathematical weighting for evidence scoring."""
        sem = 0.80
        chunk_vars = ["soil_organic_carbon", "species_richness"]
        query_vars = ["soil_organic_carbon", "rainfall"]
        rel_vars = ["soil_organic_carbon", "species_richness"]
        source_name = "FAO"
        doi = "10.4060/cb1924en"

        breakdown = compute_evidence_score(
            semantic_similarity=sem,
            chunk_variables=chunk_vars,
            query_variables=query_vars,
            active_relationship_variables=rel_vars,
            source_name=source_name,
            doi=doi,
        )

        # Expected components:
        # sem = 0.80
        # meta = 1 / 2 = 0.50 (soc in chunk & query)
        # rel = 2 / 2 = 1.0 (both in chunk & rel)
        # source = 0.95 (FAO)
        expected = (
            WEIGHT_SEMANTIC * 0.80
            + WEIGHT_METADATA * 0.50
            + WEIGHT_RELATIONSHIP * 1.0
            + WEIGHT_SOURCE_QUALITY * 0.95
        )
        assert breakdown.overall_score == pytest.approx(expected, abs=1e-3)

    def test_evidence_mapping_verifies_source_authenticity(self):
        """Validates Correction 11: source verification based on authoritative organization and DOI/URL."""
        # Verified chunk
        chunk_verified = {
            "chunk_id": 101,
            "document_id": 1,
            "title": "FAO Soil Biodiversity Report",
            "source": "FAO",
            "doi": "10.4060/cb1924en",
            "url": "https://doi.org/10.4060/cb1924en",
            "content": "Soils with elevated SOC maintain higher microbial biomass carbon.",
            "similarity": 0.88,
            "variables": ["soil_organic_carbon"],
            "topics": ["soil"],
        }
        assert EvidenceMapper.verify_source(chunk_verified) is True

        # Unverified chunk (missing DOI and unknown source)
        chunk_unverified = {
            "chunk_id": 102,
            "title": "Random Blog Post",
            "source": "Anonymous",
            "doi": None,
            "url": None,
            "content": "Biodiversity is great for soil.",
            "similarity": 0.60,
            "variables": [],
            "topics": [],
        }
        assert EvidenceMapper.verify_source(chunk_unverified) is False


class TestEvidenceValidation:
    """Tests for evidence validation threshold checks."""

    def test_empty_evidence_fails_validation(self):
        """No retrieved evidence must return is_sufficient = False."""
        is_sufficient, msgs, qualified = EvidenceValidator.validate_evidence([], min_relevance=0.5)
        assert is_sufficient is False
        assert any("No scientific documents retrieved" in m for m in msgs)
