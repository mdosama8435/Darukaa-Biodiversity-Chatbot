"""SQLAlchemy ORM models representing the core relational and vector schema."""

import uuid
from typing import Any, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Table,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.config import settings
from app.database.connection import Base

_UNSET = object()


def get_vector_type(dimension: Any = _UNSET):
    """Returns a pgvector Vector type with a configurable dimension.
    
    - If dimension is explicitly passed as None, returns Vector() (unconstrained).
    - If dimension is an integer, returns Vector(dimension).
    - If dimension is omitted, defaults to settings.EMBEDDING_DIMENSION.
    """
    dim = settings.EMBEDDING_DIMENSION if dimension is _UNSET else dimension
    return Vector(dim) if dim is not None else Vector()


# Many-to-many relationship linking Evidence to Recommendations
recommendation_evidence = Table(
    "recommendation_evidence",
    Base.metadata,
    Column("recommendation_id", Integer, ForeignKey("recommendations.id"), primary_key=True),
    Column("evidence_id", Integer, ForeignKey("evidence.id"), primary_key=True),
)


class User(Base):
    """System user or researcher profile."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="researcher", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """Multi-turn dialogue session."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    assessments = relationship("EnvironmentalAssessment", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual dialogue message within a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class EnvironmentalAssessment(Base):
    """Snapshot of multi-variable environmental observations tied to an inquiry."""
    __tablename__ = "environmental_assessments"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)

    # Soil variables
    soil_ph = Column(Float, nullable=True)
    soil_organic_carbon = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)

    # Climate variables
    temperature = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)

    # Land variables
    land_use = Column(String(100), nullable=True)
    land_cover = Column(String(100), nullable=True)

    # Biodiversity variables
    species_richness = Column(Integer, nullable=True)
    habitat_diversity = Column(String(100), nullable=True)

    # Human impact variables
    pollution = Column(String(100), nullable=True)
    deforestation = Column(String(100), nullable=True)

    # Spatial location
    region = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="assessments")
    recommendations = relationship("Recommendation", back_populates="assessment", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    """Scientific literature or technical source document."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False, default="Unknown", index=True)  # e.g., "FAO", "IPCC", "Research"
    document_type = Column(String(50), nullable=False, default="report")  # e.g., "report", "paper", "summary"
    publication_year = Column(Integer, nullable=True)
    authors = Column(JSON, nullable=True)  # List of author names or author string
    doi = Column(String(255), unique=True, index=True, nullable=True)
    journal = Column(String(255), nullable=True)
    source_url = Column(String(1000), nullable=True)
    license = Column(String(255), nullable=True)
    geographic_scope = Column(String(100), nullable=True, default="global")
    topics = Column(JSON, nullable=True)  # Categorized topics
    variables = Column(JSON, nullable=True)  # Associated environmental variables
    content_hash = Column(String(64), unique=True, index=True, nullable=True)  # SHA-256 for idempotency
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "url" in kwargs and "source_url" not in kwargs:
            kwargs["source_url"] = kwargs.pop("url")
        super().__init__(*args, **kwargs)

    @property
    def url(self) -> Optional[str]:
        return self.source_url

    @url.setter
    def url(self, value: Optional[str]) -> None:
        self.source_url = value


class KnowledgeChunk(Base):
    """Chunk of text extracted from a scientific document with vector embedding support."""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    chunk_hash = Column(String(64), unique=True, index=True, nullable=True)  # SHA-256 for chunk deduplication
    topics = Column(JSON, nullable=True)  # Tagged topics
    variables = Column(JSON, nullable=True)  # Tagged environmental variables
    
    # Vector embedding column with configurable dimension support
    embedding = Column(get_vector_type(), nullable=True)

    token_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")
    evidence_items = relationship("Evidence", back_populates="chunk", cascade="all, delete-orphan")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "content" in kwargs and "chunk_text" not in kwargs:
            kwargs["chunk_text"] = kwargs.pop("content")
        super().__init__(*args, **kwargs)

    @property
    def content(self) -> str:
        return self.chunk_text

    @content.setter
    def content(self, value: str) -> None:
        self.chunk_text = value


class Evidence(Base):
    """Grounding factual evidence extracted from scientific chunks."""
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("knowledge_chunks.id"), nullable=True)
    claim_summary = Column(Text, nullable=False)
    scientific_fact = Column(Text, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunk = relationship("KnowledgeChunk", back_populates="evidence_items")
    recommendations = relationship(
        "Recommendation",
        secondary=recommendation_evidence,
        back_populates="grounding_evidence",
    )


class Recommendation(Base):
    """Evidence-backed ecological recommendation."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("environmental_assessments.id"), nullable=True)
    action_title = Column(String(255), nullable=False)
    action_description = Column(Text, nullable=False)
    targeted_metrics = Column(JSON, nullable=True)  # List of environmental variables impacted
    time_horizon = Column(String(50), nullable=True)  # "immediate", "short-term", "medium-term", "long-term"
    confidence = Column(Float, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assessment = relationship("EnvironmentalAssessment", back_populates="recommendations")
    grounding_evidence = relationship(
        "Evidence",
        secondary=recommendation_evidence,
        back_populates="recommendations",
    )


class Scenario(Base):
    """Hypothetical what-if environmental scenario and comparative simulation record."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    baseline_assessment_id = Column(Integer, ForeignKey("environmental_assessments.id"), nullable=True)
    scenario_name = Column(String(255), nullable=True)
    changes_json = Column(JSON, nullable=False)
    baseline_state_json = Column(JSON, nullable=False)
    scenario_state_json = Column(JSON, nullable=False)
    evaluation_matrix_json = Column(JSON, nullable=True)
    impacts_json = Column(JSON, nullable=True)
    tradeoffs_json = Column(JSON, nullable=True)
    confidence = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation")
    baseline_assessment = relationship("EnvironmentalAssessment")

