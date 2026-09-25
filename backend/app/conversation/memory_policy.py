"""Memory Policy governing clarification bounds and Phase 3 invocation."""

from typing import Any, Dict, List, Tuple
from app.conversation.schemas import MetricStatus, EnvironmentalContextModel


class MemoryPolicy:
    """Governs conversational recursion bounds and triggers Phase 3 reasoning."""

    DEFAULT_MAX_CLARIFICATION_DEPTH: int = 3
    DRIVING_VARIABLES = {"soil_organic_carbon", "rainfall", "land_use"}

    @classmethod
    def should_request_clarification(
        cls,
        context: EnvironmentalContextModel,
        clarification_candidates: List[Any],
        max_depth: int = DEFAULT_MAX_CLARIFICATION_DEPTH,
    ) -> Tuple[bool, str]:
        """Determines whether to ask clarification or proceed to Phase 3 reasoning.
        
        Rules adhering to Final Implementation Conditions:
        - 3+ genuinely relevant environmental variables -> full challenge-level multi-metric reasoning.
        - 2 relevant driving variables -> relevant pairwise reasoning may be possible when depth is exhausted
          or user indicates unknown, but clarification should continue if depth allows and missing critical variable exists.
        - < 2 driving variables -> insufficient context; must continue clarification.
        """
        # If no questions remain to ask
        if not clarification_candidates:
            return False, "sufficient_parameters"

        # Check genuinely provided driving variables (SOC, rainfall, land_use/crop)
        provided_driving = [
            v for v in ["soil_organic_carbon", "rainfall"]
            if v in context.variables
            and context.variables[v].value is not None
            and context.variables[v].status != MetricStatus.UNKNOWN
        ]
        if any(
            k in context.variables
            and context.variables[k].value is not None
            and context.variables[k].status != MetricStatus.UNKNOWN
            for k in ["land_use", "crop", "land_cover"]
        ):
            provided_driving.append("land_use")

        # 1. Full 3-variable challenge-level multi-metric threshold met
        if len(provided_driving) >= 3:
            return False, "multi_metric_threshold_met"

        # Check explicit unknowns
        unknown_vars = [
            v for v, p in context.variables.items()
            if p.status == MetricStatus.UNKNOWN
        ]

        # 2. If fewer than 2 driving variables provided, cannot formulate grounded multi-metric reasoning
        if len(provided_driving) < 2:
            if len(provided_driving) >= 1 and len(unknown_vars) >= 2:
                return False, "user_unknown_exhausted"
            if context.clarification_depth >= max_depth:
                return False, "max_clarification_depth_reached"
            return True, "decision_critical_parameters_missing"

        # 3. Exactly 2 driving variables provided
        if context.clarification_depth >= max_depth:
            return False, "max_clarification_depth_reached"

        missing_driving = [v for v in cls.DRIVING_VARIABLES if v not in provided_driving]
        if any(v in unknown_vars for v in missing_driving):
            return False, "user_unknown_exhausted"

        return True, "decision_critical_parameters_missing"
