"""Assessment API router handling natural language and structured environmental assessments."""

import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from app.agents.graph import app_graph
from app.agents.state import EnvironmentalState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessment", tags=["Environmental Assessment"])


class AssessmentRequest(BaseModel):
    """Input payload supporting natural language query, structured parameters, or both."""
    model_config = ConfigDict(extra="allow")

    query: Optional[str] = Field(default=None, description="Natural language ecological inquiry")
    conversation_id: Optional[str] = Field(default=None, description="Session identifier for multi-turn tracking")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Prior dialogue turns for state merging across sessions",
    )

    # Direct environmental parameter support (Requirement 20)
    soil_organic_carbon: Optional[Union[float, str]] = None
    soil_ph: Optional[Union[float, str]] = None
    soil_moisture: Optional[Union[float, str]] = None
    temperature: Optional[Union[float, str]] = None
    rainfall: Optional[Union[float, str]] = None
    land_use: Optional[str] = None
    crop: Optional[str] = None
    crop_type: Optional[str] = None
    cropping_system: Optional[str] = None
    land_cover: Optional[str] = None
    species_richness: Optional[Union[int, str]] = None
    habitat_diversity: Optional[Union[float, str]] = None
    pollution: Optional[str] = None
    deforestation: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.post(
    "",
    summary="Evaluate multi-metric environmental condition and produce evidence-grounded recommendations",
    status_code=status.HTTP_200_OK,
)
def create_assessment(request: AssessmentRequest) -> Dict[str, Any]:
    """Processes an environmental assessment through the 12-node reasoning pipeline."""
    # 1. Parse structured environmental variables from incoming request
    req_dict = request.model_dump(exclude={"query", "conversation_id", "conversation_history"})
    env_payload = {k: v for k, v in req_dict.items() if v is not None}

    # Extract extra fields if passed in request
    for k, v in getattr(request, "__pydantic_extra__", {} or {}).items():
        if v is not None:
            env_payload[k] = v

    # Map crop aliases to land_use if land_use is missing
    if "crop" in env_payload and "land_use" not in env_payload:
        env_payload["land_use"] = env_payload.pop("crop")
    if "crop_type" in env_payload and "land_use" not in env_payload:
        env_payload["land_use"] = env_payload.pop("crop_type")
    if "cropping_system" in env_payload and "land_use" not in env_payload:
        env_payload["land_use"] = env_payload.pop("cropping_system")

    # 2. Build initial LangGraph state
    initial_state: EnvironmentalState = {
        "user_query": request.query or "",
        "conversation_history": request.conversation_history or [],
        "environmental_data": env_payload,
        "status": "ready",
    }

    logger.info(
        "Initiating assessment: query='%s', provided_keys=%s",
        request.query,
        list(env_payload.keys()),
    )

    # 3. Execute reasoning workflow
    try:
        final_state = app_graph.invoke(initial_state)
    except Exception as exc:
        logger.error("LangGraph pipeline execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Environmental reasoning pipeline error: {exc}",
        )

    response_payload = final_state.get("final_response") or {}

    # Check for infrastructure failure (Correction 1)
    if response_payload.get("status") == "error":
        err_msg = response_payload.get("error", "Database or vector retrieval infrastructure unavailable.")
        logger.error("Assessment infrastructure failure: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err_msg,
        )

    return response_payload
