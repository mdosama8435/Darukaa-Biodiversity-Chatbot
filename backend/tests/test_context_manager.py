"""Unit tests for EnvironmentalContextManager: provenance, state merging, value overrides, and safety rules."""

import pytest
from app.conversation.schemas import MetricStatus, EnvironmentalContextModel, VariableProvenance
from app.conversation.context_manager import EnvironmentalContextManager


class TestContextManagerProvenanceAndMerging:
    """Tests for variable provenance, state accumulation, and value overriding."""

    def test_variable_provenance_structure(self):
        """Verifies full audit provenance on every extracted variable (Step 2)."""
        text = "Rainfall is around 600 mm and SOC is 0.3%."
        extracted, unknowns, ambiguity = EnvironmentalContextManager.extract_from_message(
            text=text,
            turn_id=1,
        )

        assert "rainfall" in extracted
        rain_prov = extracted["rainfall"]
        assert rain_prov.value == 600.0
        assert rain_prov.unit == "mm"
        assert rain_prov.source == "user_statement"
        assert rain_prov.turn_id == 1
        assert rain_prov.status == MetricStatus.PROVIDED
        assert rain_prov.timestamp is not None

        assert "soil_organic_carbon" in extracted
        soc_prov = extracted["soil_organic_carbon"]
        assert soc_prov.value == 0.3
        assert soc_prov.unit == "%"
        assert soc_prov.turn_id == 1

    def test_state_merging_preserves_unmentioned_variables(self):
        """Turn 2 adds rainfall without dropping region and land_use from Turn 1 (Step 3)."""
        ctx = EnvironmentalContextModel(conversation_id="test_merge_1")

        # Turn 1: Region and Land Use
        t1_vars, _, _ = EnvironmentalContextManager.extract_from_message(
            text="My farm is in Bihar and I grow wheat continuously.",
            turn_id=1,
        )
        ctx, _ = EnvironmentalContextManager.merge_context(ctx, t1_vars, turn_id=1)

        assert "region" in ctx.variables
        assert "land_use" in ctx.variables
        assert ctx.variables["land_use"].value == "wheat continuous cropping"

        # Turn 2: Rainfall only
        t2_vars, _, _ = EnvironmentalContextManager.extract_from_message(
            text="Rainfall is around 600 mm.",
            turn_id=2,
        )
        ctx, _ = EnvironmentalContextManager.merge_context(ctx, t2_vars, turn_id=2)

        # Region and land_use must still be active!
        assert "region" in ctx.variables
        assert "land_use" in ctx.variables
        assert ctx.variables["land_use"].value == "wheat continuous cropping"
        assert "rainfall" in ctx.variables
        assert ctx.variables["rainfall"].value == 600.0

    def test_value_overriding_wheat_to_maize(self):
        """Turn 3 overrides land_use from wheat to maize, logging updates and unseating old wheat (Step 3)."""
        ctx = EnvironmentalContextModel(conversation_id="test_override_1")

        # Turn 1: Wheat monoculture + rainfall
        t1_vars, _, _ = EnvironmentalContextManager.extract_from_message(
            text="I grow wheat continuously and rainfall is around 600 mm.",
            turn_id=1,
        )
        ctx, _ = EnvironmentalContextManager.merge_context(ctx, t1_vars, turn_id=1)
        assert ctx.variables["land_use"].value == "wheat continuous cropping"

        # Turn 2: Explicit override to maize
        t2_vars, _, _ = EnvironmentalContextManager.extract_from_message(
            text="Actually, I switched from wheat to maize this year.",
            turn_id=2,
        )
        ctx, updates = EnvironmentalContextManager.merge_context(ctx, t2_vars, turn_id=2)

        # Land use must now be maize!
        assert ctx.variables["land_use"].value == "maize"
        assert ctx.variables["land_use"].status == MetricStatus.UPDATED

        # Rainfall must remain unchanged!
        assert ctx.variables["rainfall"].value == 600.0
        assert ctx.variables["rainfall"].status == MetricStatus.PROVIDED

        # Update log must record the transition
        assert len(updates) >= 1
        lu_update = next((u for u in updates if u.variable == "land_use"), None)
        assert lu_update is not None
        assert lu_update.old_value == "wheat continuous cropping"
        assert lu_update.new_value == "maize"
        assert lu_update.turn_id == 2


class TestSafetyAndClarificationRules:
    """Tests for UNKNOWN != ZERO, inferred measurements guard, and ambiguity resolution."""

    def test_explicit_unknown_does_not_coerce_to_zero(self):
        """User stating 'I don't know my SOC' must store UNKNOWN status with value=None, never 0 (Step 4)."""
        text = "I don't know my soil organic carbon, but rainfall is 500 mm."
        extracted, unknowns, _ = EnvironmentalContextManager.extract_from_message(text=text, turn_id=1)

        assert "soil_organic_carbon" in unknowns
        assert "soil_organic_carbon" in extracted
        soc_prov = extracted["soil_organic_carbon"]
        assert soc_prov.value is None  # UNKNOWN != ZERO
        assert soc_prov.status == MetricStatus.UNKNOWN
        assert soc_prov.value != 0

        # Flattened environmental data must NOT contain None/0
        ctx = EnvironmentalContextModel(conversation_id="test_unknown")
        ctx, _ = EnvironmentalContextManager.merge_context(ctx, extracted, turn_id=1)
        flat = EnvironmentalContextManager.get_flat_environmental_data(ctx)

        assert "soil_organic_carbon" not in flat
        assert flat["rainfall"] == 500.0

    def test_inferred_values_never_treated_as_numeric_measurements(self):
        """Correction 2: 'My area is very dry' must NOT create rainfall = 400."""
        text = "My area is very dry and biodiversity has declined."
        extracted, _, _ = EnvironmentalContextManager.extract_from_message(text=text, turn_id=1)

        # Must NOT infer numeric rainfall = 400
        if "rainfall" in extracted:
            assert extracted["rainfall"].value is None
            assert extracted["rainfall"].status == MetricStatus.INFERRED
            assert extracted["rainfall"].source == "inferred"

    def test_ambiguous_reference_prompts_clarification(self):
        """Correction 3: Ambiguous reference 'It is 0.3%' prompts clarification instead of guessing."""
        ctx = EnvironmentalContextModel(conversation_id="test_ambiguity")
        ctx.variables["soil_organic_carbon"] = VariableProvenance(
            variable="soil_organic_carbon",
            value=None,
            status=MetricStatus.UNKNOWN,
            turn_id=1,
        )
        ctx.variables["soil_moisture"] = VariableProvenance(
            variable="soil_moisture",
            value=None,
            status=MetricStatus.UNKNOWN,
            turn_id=1,
        )

        extracted, unknowns, ambiguity_q = EnvironmentalContextManager.extract_from_message(
            text="It is 0.3%.",
            turn_id=2,
            active_context=ctx,
        )

        assert ambiguity_q is not None
        assert "soil organic carbon" in ambiguity_q.lower() or "soc" in ambiguity_q.lower()

    def test_access_control_boundary(self):
        """Correction 4: Verifies access boundary between conversation owner and caller."""
        # Same user -> allowed
        assert EnvironmentalContextManager.verify_access_boundary("user_123", "user_123") is True
        # Different user -> rejected
        assert EnvironmentalContextManager.verify_access_boundary("user_123", "user_999") is False
        # Owned conversation accessed anonymously -> rejected
        assert EnvironmentalContextManager.verify_access_boundary("user_123", None) is False
        # Unowned conversation accessed anonymously -> allowed
        assert EnvironmentalContextManager.verify_access_boundary(None, None) is True
