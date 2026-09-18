"""Schemas for multi-turn conversation, provenance tracking, and clarification."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class MetricStatus(str, Enum):
    """Categorical status of an environmental metric in conversation memory."""
    PROVIDED = "provided"        # Explicitly stated by user with measurement/value
    UNKNOWN = "unknown"          # Explicitly stated by user as unknown ("I don't know my SOC")
    UPDATED = "updated"          # Overridden in a subsequent turn (e.g. wheat -> maize)
    INFERRED = "inferred"        # Qualitative context without measurement (Correction 2)
    NOT_MENTIONED = "not_mentioned"


class VariableProvenance(BaseModel):
    """Detailed audit provenance for an environmental metric (Step 2)."""
    model_config = ConfigDict(extra="ignore")

    variable: str = Field(..., description="Environmental parameter key")
    value: Optional[Any] = Field(default=None, description="Measured or qualitative value (None if unknown)")
    unit: Optional[str] = Field(default=None, description="Measurement unit (e.g. '%', 'mm', 'pH')")
    source: str = Field(
        default="user_statement",
        description="Origin: 'user_statement', 'structured_input', 'clarification_reply', 'inferred'",
    )
    turn_id: int = Field(default=1, description="Sequence ID of dialogue turn where variable was recorded/updated")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of record creation or update",
    )
    status: MetricStatus = Field(default=MetricStatus.PROVIDED)
    notes: Optional[str] = Field(default=None, description="Optional explanatory context or previous value")


class ContextUpdateRecord(BaseModel):
    """Audit log of a variable overridden or changed in conversation (Step 3)."""
    model_config = ConfigDict(extra="ignore")

    variable: str
    old_value: Any
    new_value: Any
    turn_id: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = Field(default="User explicit correction or update")


class EnvironmentalContextModel(BaseModel):
    """Persistent environmental context across multi-turn dialogue."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    variables: Dict[str, VariableProvenance] = Field(default_factory=dict)
    detected_updates: List[ContextUpdateRecord] = Field(default_factory=list)
    clarification_depth: int = Field(default=0, ge=0)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClarificationQuestionItem(BaseModel):
    """Structured targeted clarification question item (Step 5)."""
    model_config = ConfigDict(extra="ignore")

    question: str
    target_variable: str
    priority: int = 1
    rationale: str


class ChatRequest(BaseModel):
    """Input payload for multi-turn chat endpoint."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: Optional[str] = Field(default=None, description="Conversation session ID; creates new if omitted")
    message: str = Field(..., min_length=1, description="User conversational message")
    user_id: Optional[str] = Field(default=None, description="User identifier for authorization boundary (Correction 4)")


class ChatResponse(BaseModel):
    """Output payload for multi-turn chat dialogue."""
    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    turn_id: int
    role: str = "assistant"
    message: str
    status: str = Field(
        default="completed",
        description="'clarification_needed' | 'completed' | 'insufficient_evidence' | 'error'",
    )
    clarification_questions: List[str] = Field(default_factory=list)
    environmental_context: Dict[str, Any] = Field(default_factory=dict)
    detected_updates: List[Dict[str, Any]] = Field(default_factory=list)
    assessment: Optional[Dict[str, Any]] = None
    confidence: Optional[str] = None
