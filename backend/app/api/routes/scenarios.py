"""REST API endpoints for Environmental Scenario & What-If Simulation Engine."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.conversation.context_manager import EnvironmentalContextManager
from app.scenarios.schemas import (
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
    ScenarioChange,
    ScenarioType,
)
from app.scenarios.parser import ScenarioParser
from app.scenarios.validator import ScenarioValidator
from app.scenarios.state_builder import ScenarioStateBuilder
from app.scenarios.analyzer import ScenarioAnalysisEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post(
    "/analyze",
    response_model=ScenarioAnalysisResponse,
    summary="Analyze hypothetical what-if environmental scenario",
    description="Simulates management interventions, land-use transitions, or metric perturbations against a baseline state.",
)
def analyze_scenario_endpoint(
    request: ScenarioAnalysisRequest,
    db: Session = Depends(get_db),
) -> ScenarioAnalysisResponse:
    """Executes evidence-grounded what-if scenario comparative analysis."""
    # 1. Resolve baseline environmental profile
    baseline: Dict[str, Any] = {}
    if request.baseline:
        baseline = dict(request.baseline)
    elif request.conversation_id:
        context = EnvironmentalContextManager.get_or_create_context(request.conversation_id)
        baseline = EnvironmentalContextManager.get_flat_environmental_data(context)

    # 2. Extract or resolve scenario changes
    changes: List[ScenarioChange] = []
    if request.changes:
        changes = request.changes
    elif request.query:
        parsed_changes, needs_clarif, clarif_q = ScenarioParser.parse_query(request.query, baseline)
        if needs_clarif:
            return ScenarioAnalysisResponse(
                status="needs_clarification",
                scenario_id="scen_clarification",
                clarification_needed=True,
                clarification_questions=clarif_q,
            )
        changes = parsed_changes
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'query' (natural language what-if) or 'changes' (structured delta list) must be provided.",
        )

    # Bind baseline to changes and resolve deterministic relative calculations if baseline known
    for ch in changes:
        if ch.baseline_value is None and ch.variable in baseline and baseline[ch.variable] is not None:
            ch.baseline_value = baseline[ch.variable]
            if ch.change_type == ScenarioType.RELATIVE_CHANGE or ch.unit in ("percent", "%"):
                if ch.change_value is not None and isinstance(ch.baseline_value, (int, float)):
                    pct = float(ch.change_value)
                    base = float(ch.baseline_value)
                    ch.scenario_value = round(base * (1.0 + pct / 100.0), 1)
                    direction_word = "reduction" if pct < 0 else "increase"
                    ch.notes = f"Relative {direction_word} of {abs(pct)}% applied to baseline ({base} → {ch.scenario_value})"

    # 3. Validate changes against physical and ecological boundaries
    is_valid, errs = ScenarioValidator.validate_changes(changes, baseline)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scenario validation error: {'; '.join(errs)}",
        )

    # 4. Build scenario state (immutably without mutating baseline)
    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)

    # 5. Execute comparative analysis engine
    try:
        comparison = ScenarioAnalysisEngine.analyze_scenario(
            baseline=baseline,
            scenario_state=scen_state,
            changes=changes,
            assumptions=assumptions,
            conversation_id=request.conversation_id,
            db_session=db,
        )
    except Exception as exc:
        logger.error("Scenario analysis execution failed: %s", exc, exc_info=True)
        return ScenarioAnalysisResponse(
            status="error",
            scenario_id="scen_error",
            error=str(exc),
        )

    return ScenarioAnalysisResponse(
        status="completed",
        scenario_id=comparison.scenario_id,
        comparison=comparison,
    )
