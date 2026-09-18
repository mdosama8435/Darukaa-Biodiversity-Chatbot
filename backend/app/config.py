"""Application configuration using Pydantic Settings."""

import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "DARUKAA.EARTH AI Biodiversity Intelligence"
    API_V1_STR: str = "/api/v1"

    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database Configuration (PostgreSQL + pgvector)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "darukaa"
    POSTGRES_PASSWORD: str = "darukaa_password_change_in_production"
    POSTGRES_DB: str = "darukaa_earth"
    DATABASE_URL: Optional[str] = None

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Vector Embedding Configuration (Configurable dimension)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: Optional[int] = 384

    # Knowledge Paths
    KNOWLEDGE_SOURCE_DIR: str = "knowledge/sources"
    KNOWLEDGE_PROCESSED_DIR: str = "knowledge/processed"
    KNOWLEDGE_METADATA_DIR: str = "knowledge/metadata"

    # LLM Provider Configuration
    # Supported: "openai", "anthropic", "ollama"
    # Left unconfigured by default so the application fails explicitly rather than faking outputs.
    LLM_PROVIDER: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"


settings = Settings()
