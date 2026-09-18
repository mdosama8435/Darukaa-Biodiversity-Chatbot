"""Unit tests for recommendation generation, quantitative claim guard, language softening, and confidence ranking."""

import pytest
from app.recommendations.generator import RecommendationGenerator
from app.recommendations.validator import RecommendationEvidenceValidator
from app.recommendations.ranking import calculate_explainable_confidence, rank_and_score_recommendations
from app.recommendations.schemas import RecommendationItem, TimeHorizon, ExpectedEffect, EnvironmentalReasoningStep
from app.evidence.schemas import EvidenceItem


class TestRecommendationGenerator:
    """Tests constraint-aware candidate generation."""

    def test_no_hardcoded_universal_species(self):
        """Validates Correction 5: does not hardcode Faidherbia albida as a universal species."""
        env_data = {
            "soil_organic_carbon": 0.3,
            "rainfall": 400.0,
            "land_use": "wheat monoculture",
            "region": "semi-arid",
        }
        candidates = RecommendationGenerator.generate_candidates(
            environmental_data=env_data,
            active_relationships=[],
            evidence_items=[],
        )

        assert len(candidates) >= 1
        top_action = candidates[0].action

        # Should recommend broad agroforestry / crop diversification rather than a specific hardcoded species name
        assert "Faidherbia" not in top_action
        assert "Drought-Compatible" in top_action or "Agroforestry" in top_action

        # Should document limitation that local species selection is required
        all_limitations = " ".join(candidates[0].limitations)
        assert "local agronomic" in all_limitations.lower()


class TestGenericQuantitativeClaimGuard:
    """Rigorous tests for Correction 2: Generic Quantitative Claim Guard without hardcoded numbers."""

    @pytest.fixture
    def sample_recommendation(self) -> RecommendationItem:
        return RecommendationItem(
            action="Agroforestry Integration",
            why=["Improves soil health"],
            environmental_reasoning=[
                EnvironmentalReasoningStep(
                    variables=["soil_organic_carbon", "rainfall", "land_use"],
                    relationship="soc_rainfall_monoculture_stress",
                    explanation="Causal monoculture causes soil degradation and will increase erosion.",
                )
            ],
            impacted_metrics=["soil_organic_carbon"],
            time_horizon=TimeHorizon(
                short_term="0-1 years: mulching",
                medium_term="1-3 years: roots",
                long_term="3-5 years: carbon",
            ),
            expected_effect=ExpectedEffect(
                description="Promotes carbon accrual",
                direction="positive",
                quantitative_estimate=None,
                estimate_source=None,
            ),
        )

    def test_claim_guard_case_a_unsupported_percentage_rejected(self, sample_recommendation):
        """Test A: Unsupported '+30% biodiversity' must be rejected to None."""
        sample_recommendation.expected_effect.quantitative_estimate = "+30% biodiversity"

        evidence = [
            EvidenceItem(
                claim="Continuous organic inputs enhance microbial respiration and aggregate stability.",
                source_title="FAO Soil Report",
                source_organization="FAO",
                verified_source=True,
                doi="10.4060/cb1924en",
                matched_variables=["soil_organic_carbon"],
            )
        ]

        val_rec = RecommendationEvidenceValidator.validate_recommendation(sample_recommendation, evidence)
        assert val_rec.expected_effect.quantitative_estimate is None
        assert val_rec.expected_effect.estimate_source is None
        assert "cannot be estimated" in val_rec.expected_effect.description

    def test_claim_guard_case_b_number_absent_from_evidence_rejected(self, sample_recommendation):
        """Test B: Claimed number absent from evidence text must be rejected."""
        sample_recommendation.expected_effect.quantitative_estimate = "15% increase"

        evidence = [
            EvidenceItem(
                claim="Agroforestry increases macrofauna diversity significantly across multiple regions.",
                source_title="IPCC Report",
                source_organization="IPCC",
                verified_source=True,
                doi="10.1017/9781009157988.006",
                matched_variables=["soil_organic_carbon"],
            )
        ]

        val_rec = RecommendationEvidenceValidator.validate_recommendation(sample_recommendation, evidence)
        assert val_rec.expected_effect.quantitative_estimate is None

    def test_claim_guard_case_c_number_present_but_unverified_source_rejected(self, sample_recommendation):
        """Test C: Numerical claim present in evidence text, but source is unverified (missing DOI/authentic org)."""
        sample_recommendation.expected_effect.quantitative_estimate = "19%"

        evidence = [
            EvidenceItem(
                claim="An unverified study suggests an increase of 19% under some conditions.",
                source_title="Unverified Blog",
                source_organization="Unknown",
                verified_source=False,  # Unverified!
                doi=None,
                url=None,
                matched_variables=["soil_organic_carbon"],
            )
        ]

        val_rec = RecommendationEvidenceValidator.validate_recommendation(sample_recommendation, evidence)
        assert val_rec.expected_effect.quantitative_estimate is None
        assert val_rec.expected_effect.estimate_source is None

    def test_claim_guard_case_d_number_present_in_verified_evidence_retained(self, sample_recommendation):
        """Test D: Numerical claim verbatim present in verified source is retained with source attribution."""
        sample_recommendation.expected_effect.quantitative_estimate = "19%"
        sample_recommendation.impacted_metrics = ["soil_organic_carbon"]

        evidence = [
            EvidenceItem(
                claim="Agroforestry systems increase total soil organic carbon stocks by an average of 19% relative to monocultures.",
                source_title="Agriculture, Ecosystems & Environment",
                source_organization="Research Paper",
                publication_year=2016,
                verified_source=True,
                doi="10.1016/j.agee.2016.06.002",
                matched_variables=["soil_organic_carbon"],
            )
        ]

        # Attach evidence to recommendation
        sample_recommendation.evidence = evidence

        val_rec = RecommendationEvidenceValidator.validate_recommendation(sample_recommendation, evidence)
        assert val_rec.expected_effect.quantitative_estimate == "19%"
        assert val_rec.expected_effect.estimate_source is not None
        assert "10.1016/j.agee.2016.06.002" in val_rec.expected_effect.estimate_source

    def test_associative_language_softening(self, sample_recommendation):
        """Validates softening of deterministic language ('causes', 'will increase')."""
        sample_recommendation.action = "Intervention causes improved yields and will increase biodiversity"
        evidence = []

        val_rec = RecommendationEvidenceValidator.validate_recommendation(sample_recommendation, evidence)
        assert "causes" not in val_rec.action.lower()
        assert "will increase" not in val_rec.action.lower()
        assert "associated with" in val_rec.action.lower() or "contribute" in val_rec.action.lower()


class TestExplainableConfidence:
    """Tests categorical confidence derivation and factor breakdown (Correction 9)."""

    def test_confidence_factors_breakdown(self):
        """Validates explainable confidence ratings."""
        evidence = [
            EvidenceItem(
                claim="Grounding claim 1",
                source_title="FAO",
                source_organization="FAO",
                relevance_score=0.85,
                verified_source=True,
            ),
            EvidenceItem(
                claim="Grounding claim 2",
                source_title="IPCC",
                source_organization="IPCC",
                relevance_score=0.80,
                verified_source=True,
            ),
        ]

        level, factors = calculate_explainable_confidence(
            completeness_score=0.60,
            evidence_items=evidence,
            conflicting_evidence_count=0,
            has_multi_metric_reasoning=True,
        )

        assert level == "high"
        assert factors["input_completeness"] == 0.60
        assert factors["supporting_chunks"] == 2
        assert factors["evidence_quality"] >= 0.80
        assert "Strong input completeness" in factors["rationale"]
