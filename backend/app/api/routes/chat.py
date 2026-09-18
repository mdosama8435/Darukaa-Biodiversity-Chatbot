"""Conversational chat API routes supporting multi-turn memory and clarification loops."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.conversation.schemas import (
    ChatRequest,
    ChatResponse,
    EnvironmentalContextModel,
)
from app.conversation.context_manager import EnvironmentalContextManager
from app.conversation.turn_processor import TurnProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Conversational Intelligence"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Interact with conversational environmental scientist across multi-turn dialogue",
    status_code=status.HTTP_200_OK,
)
def chat_turn(request: ChatRequest) -> ChatResponse:
    """Processes a user message, manages state accumulation, asks targeted clarification,
    or triggers Phase 3 evidence-grounded assessment.
    """
    logger.info(
        "Chat turn received: conv_id=%s, msg_len=%d",
        request.conversation_id,
        len(request.message),
    )
    try:
        response = TurnProcessor.process_turn(request)
        return response
    except Exception as exc:
        logger.error("Chat turn execution error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational processing error: {exc}",
        )


@router.get(
    "/conversations",
    summary="List all active dialogue sessions",
    status_code=status.HTTP_200_OK,
)
def list_conversations(
    user_id: Optional[str] = Query(default=None, description="Filter conversations by owner (Correction 4)"),
) -> List[Dict[str, Any]]:
    """Lists registered dialogue sessions with metadata and variable summaries."""
    sessions = []
    for conv_id, ctx in EnvironmentalContextManager._MEMORY_STORE.items():
        provided_vars = [
            v for v, p in ctx.variables.items() if p.value is not None
        ]
        sessions.append({
            "conversation_id": conv_id,
            "clarification_depth": ctx.clarification_depth,
            "variables_count": len(provided_vars),
            "variables_provided": provided_vars,
            "updated_at": ctx.updated_at,
        })
    return sessions


@router.get(
    "/conversations/{conversation_id}",
    summary="Retrieve persistent environmental context for a conversation session",
    status_code=status.HTTP_200_OK,
)
def get_conversation_context(
    conversation_id: str,
    user_id: Optional[str] = Query(default=None, description="User requesting session access"),
) -> Dict[str, Any]:
    """Fetches persistent environmental context and provenance records for a given session."""
    if conversation_id not in EnvironmentalContextManager._MEMORY_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation session '{conversation_id}' not found.",
        )

    ctx = EnvironmentalContextManager._MEMORY_STORE[conversation_id]
    return {
        "conversation_id": conversation_id,
        "clarification_depth": ctx.clarification_depth,
        "environmental_context": TurnProcessor._format_context_summary(ctx),
        "detected_updates": [u.model_dump() for u in ctx.detected_updates],
        "updated_at": ctx.updated_at,
    }


@router.delete(
    "/conversations/{conversation_id}",
    summary="Reset or delete a conversation session",
    status_code=status.HTTP_200_OK,
)
def delete_conversation_session(conversation_id: str) -> Dict[str, Any]:
    """Resets conversational memory and context for the specified conversation session."""
    if conversation_id in EnvironmentalContextManager._MEMORY_STORE:
        del EnvironmentalContextManager._MEMORY_STORE[conversation_id]
        return {"status": "deleted", "conversation_id": conversation_id}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Conversation session '{conversation_id}' not found.",
    )
