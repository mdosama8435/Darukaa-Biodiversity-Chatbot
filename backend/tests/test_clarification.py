"""Unit tests for topic-targeted clarification engine and memory policy."""

import pytest
from app.conversation.schemas import MetricStatus, VariableProvenance, EnvironmentalContextModel
from app.conversation.clarification import ClarificationEngine
from app.conversation.memory_policy import MemoryPolicy


class TestClarificationEngineTopicTargeting:
    """Tests that clarification questions are scoped to the user's specific problem domain."""

    def test_biodiversity_decline_prioritizes_cropping_and_climate(self):
        """User asking about biodiversity decline should be asked about land use, rainfall, SOC."""
        msg = "My biodiversity is declining. What should I do?"
        ctx = EnvironmentalContextModel(conversation_id="test_clarify_bio")

        questions = ClarificationEngine.generate_clarification_questions(
            user_message=msg,
            active_context=ctx,
            max_questions=3,
        )

        assert len(questions) <= 3
        target_vars = [q.target_variable for q in questions]

        assert "land_use" in target_vars
        assert "rainfall" in target_vars
        # Should NOT ask for irrelevant variables like pollution or deforestation
        assert "pollution" not in target_vars
        assert "deforestation" not in target_vars

    def test_soil_carbon_inquiry_prioritizes_soc_and_tillage(self):
        """User asking about soil carbon loss should be asked about SOC and management, not pollution."""
        msg = "My soil organic carbon has been declining severely. How can I restore it?"
        ctx = EnvironmentalContextModel(conversation_id="test_clarify_soc")

        questions = ClarificationEngine.generate_clarification_questions(
            user_message=msg,
            active_context=ctx,
            max_questions=3,
        )

        target_vars = [q.target_variable for q in questions]
        assert "soil_organic_carbon" in target_vars or "land_use" in target_vars
        assert "pollution" not in target_vars
        assert "deforestation" not in target_vars

    def test_does_not_reask_already_provided_or_unknown_variables(self):
        """Variables already provided or already marked UNKNOWN are not re-asked."""
        ctx = EnvironmentalContextModel(conversation_id="test_no_reask")
        # Land use provided
        ctx.variables["land_use"] = VariableProvenance(
            variable="land_use",
            value="wheat monoculture",
            turn_id=1,
            status=MetricStatus.PROVIDED,
        )
        # SOC explicitly unknown
        ctx.variables["soil_organic_carbon"] = VariableProvenance(
            variable="soil_organic_carbon",
            value=None,
            turn_id=1,
            status=MetricStatus.UNKNOWN,
        )

        msg = "My biodiversity is declining."
        questions = ClarificationEngine.generate_clarification_questions(
            user_message=msg,
            active_context=ctx,
            max_questions=3,
        )

        target_vars = [q.target_variable for q in questions]
        assert "land_use" not in target_vars
        assert "soil_organic_carbon" not in target_vars
        # Rainfall and region should be asked instead!
        assert "rainfall" in target_vars or "region" in target_vars


class TestMemoryPolicyBounds:
    """Tests for clarification depth limits and Correction 1 rules."""

    def test_clarification_depth_bound_prevents_infinite_loop(self):
        """Reaching max clarification depth stops asking questions and proceeds to Phase 3."""
        ctx = EnvironmentalContextModel(
            conversation_id="test_depth",
            clarification_depth=2,  # Max depth reached!
        )
        ctx.variables["land_use"] = VariableProvenance(
            variable="land_use",
            value="wheat monoculture",
            turn_id=1,
        )

        should_clarify, reason = MemoryPolicy.should_request_clarification(
            context=ctx,
            clarification_candidates=[{"q": "sample"}],
            max_depth=2,
        )

        assert should_clarify is False
        assert "max_clarification_depth_reached" in reason

    def test_sufficient_variables_proceeds_immediately(self):
        """When 3 or more variables are present, clarification is bypassed to execute Phase 3."""
        ctx = EnvironmentalContextModel(conversation_id="test_sufficient")
        for v in ["soil_organic_carbon", "rainfall", "land_use"]:
            ctx.variables[v] = VariableProvenance(
                variable=v,
                value=0.3 if v == "soil_organic_carbon" else (500 if v == "rainfall" else "wheat"),
                turn_id=1,
                status=MetricStatus.PROVIDED,
            )

        should_clarify, reason = MemoryPolicy.should_request_clarification(
            context=ctx,
            clarification_candidates=[{"q": "sample"}],
            max_depth=2,
        )

        assert should_clarify is False
        assert "multi_metric_threshold_met" in reason
