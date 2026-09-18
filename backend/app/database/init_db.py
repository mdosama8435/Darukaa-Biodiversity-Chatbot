"""Database initialization module ensuring pgvector extension and core schema creation."""

import logging
import sys
from pathlib import Path
from typing import Dict, Set, Any, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import engine, Base, SessionLocal
import app.database.models  # Required so all models are registered on Base.metadata

logger = logging.getLogger("darukaa.database.init")


def get_expected_tables() -> Set[str]:
    """Dynamically derives the authoritative set of expected table names from SQLAlchemy metadata."""
    return {table.name for table in Base.metadata.sorted_tables}


def ensure_pgvector_extension(db_engine: Engine) -> str:
    """Enables and verifies the pgvector extension in PostgreSQL."""
    logger.info("Enabling pgvector extension if not exists...")
    with db_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

        result = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).scalar()
        if not result:
            raise RuntimeError(
                "pgvector extension could not be verified in pg_extension. "
                "Ensure PostgreSQL was started with pgvector support (e.g. pgvector/pgvector:pg16)."
            )
        logger.info("pgvector extension verified: version %s", result)
        return str(result)


def create_schema_and_indexes(db_engine: Engine) -> Set[str]:
    """Creates all application tables and specialized vector indexes idempotently."""
    expected_tables = get_expected_tables()
    logger.info("Creating application tables for %d models: %s", len(expected_tables), sorted(list(expected_tables)))

    # Create all tables defined on Base.metadata
    Base.metadata.create_all(bind=db_engine)

    # Create HNSW index matching pgvector cosine distance operator (<=>)
    # The retriever uses KnowledgeChunk.embedding.cosine_distance() with EMBEDDING_DIMENSION (384)
    logger.info("Creating HNSW cosine distance index on knowledge_chunks.embedding...")
    with db_engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw "
            "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);"
        ))
        conn.commit()

    return expected_tables


def verify_schema(db_engine: Engine, expected_tables: Set[str]) -> Set[str]:
    """Verifies that all expected tables exist in the target database."""
    inspector = inspect(db_engine)
    existing_tables = set(inspector.get_table_names())
    missing = expected_tables - existing_tables

    if missing:
        error_msg = (
            f"Database schema verification failed! Missing {len(missing)} required tables: {sorted(list(missing))}. "
            f"Existing tables in database: {sorted(list(existing_tables))}."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info("Database schema verification passed: all %d tables present.", len(expected_tables))
    return existing_tables


def seed_knowledge_base(db_session: Session, force: bool = False) -> Dict[str, Any]:
    """Optionally ingests verified authoritative scientific literature (FAO & IPCC) if the knowledge base is empty."""
    from app.database.models import KnowledgeDocument
    from app.rag.ingestion import IngestionPipeline

    doc_count = db_session.query(KnowledgeDocument).count()
    if doc_count > 0 and not force:
        logger.info("Knowledge base already contains %d documents; skipping initial seed.", doc_count)
        return {"seeded": False, "document_count": doc_count}

    logger.info("Seeding verified scientific knowledge base (FAO & IPCC)...")
    source_path = Path(settings.KNOWLEDGE_SOURCE_DIR)
    metadata_path = Path(settings.KNOWLEDGE_METADATA_DIR)

    verified_files = [
        source_path / "fao" / "fao_soil_biodiversity_report_2020.md",
        source_path / "ipcc" / "ipcc_srccl_land_degradation_2019.md",
    ]
    

    pipeline = IngestionPipeline(db_session=db_session)
    total_chunks = 0
    ingested_docs = []
    for f in verified_files:
        if f.exists():
            is_new, count = pipeline.ingest_file(
                file_path=f,
                metadata_dir=metadata_path if metadata_path.exists() else None,
                force_reindex=force,
            )
            total_chunks += count
            ingested_docs.append({"file": f.name, "chunks": count, "is_new": is_new})

    logger.info("Knowledge base seeding complete: %d chunks ingested across %d verified documents.", total_chunks, len(ingested_docs))
    return {"seeded": True, "total_chunks": total_chunks, "documents": ingested_docs}


def init_db(
    engine_to_use: Optional[Engine] = None,
    seed: bool = False,
    force_reindex: bool = False,
) -> Dict[str, Any]:
    """Deterministic and repeatable database initialization function.

    1. Connects to DATABASE_URL.
    2. Enables the pgvector extension.
    3. Creates all application tables from the project's actual model definitions.
    4. Creates the HNSW cosine index.
    5. Verifies all expected tables exist.
    6. Optionally seeds scientific documents.
    """
    target_engine = engine_to_use or engine
    logger.info("Starting database initialization against %s...", target_engine.url.render_as_string(hide_password=True))

    try:
        # Step 1: Probe connectivity
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))

        # Step 2: pgvector extension
        pgvector_version = ensure_pgvector_extension(target_engine)

        # Step 3: Tables & indexes
        expected_tables = create_schema_and_indexes(target_engine)

        # Step 4: Verification
        verified_tables = verify_schema(target_engine, expected_tables)

        # Step 5: Optional seeding
        seed_result = None
        if seed:
            db = SessionLocal()
            try:
                seed_result = seed_knowledge_base(db, force=force_reindex)
            finally:
                db.close()

        logger.info("Database initialization completed successfully.")
        return {
            "status": "ok",
            "pgvector_version": pgvector_version,
            "tables": sorted(list(verified_tables)),
            "seed": seed_result,
        }

    except Exception as exc:
        logger.error("FATAL: Database initialization failed: %s", exc)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    should_seed = "--seed" in sys.argv
    force = "--force" in sys.argv
    try:
        summary = init_db(seed=should_seed, force_reindex=force)
        print("\n=== Database Initialization Successful ===")
        print(f"pgvector version: {summary['pgvector_version']}")
        print(f"Verified tables ({len(summary['tables'])}): {', '.join(summary['tables'])}")
        if summary.get("seed"):
            print(f"Seed status: {summary['seed']}")
    except Exception as e:
        print(f"\n=== Database Initialization Failed: {e} ===", file=sys.stderr)
        sys.exit(1)
