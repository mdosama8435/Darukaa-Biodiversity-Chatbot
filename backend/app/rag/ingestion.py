"""Idempotent ingestion pipeline for registering, chunking, embedding, and storing scientific documents."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import KnowledgeDocument, KnowledgeChunk
from app.rag.loaders import load_document, LoadedSection
from app.rag.chunking import chunk_document
from app.rag.embeddings import BaseEmbeddingService, get_embedding_service
from app.rag.schemas import DocumentMetadata, ProcessedChunk


def compute_file_hash(file_path: Path) -> str:
    """Computes SHA-256 hash of a file's raw byte content for idempotency tracking."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_companion_metadata(source_file: Path, metadata_dir: Optional[Path] = None) -> Optional[DocumentMetadata]:
    """Looks for a corresponding JSON metadata file in metadata/ or adjacent to the source."""
    search_dirs = []
    if metadata_dir and metadata_dir.exists():
        search_dirs.append(metadata_dir)
        search_dirs.append(metadata_dir / source_file.parent.name)
    search_dirs.append(source_file.parent)

    candidate_names = [
        f"{source_file.stem}.json",
        f"{source_file.name}.json",
        "metadata.json",
    ]

    for d in search_dirs:
        for name in candidate_names:
            candidate = d / name
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                    return DocumentMetadata(**data)
                except Exception as e:
                    print(f"Warning: Failed to parse companion metadata '{candidate}': {e}")

    return None


class IngestionPipeline:
    """Pipeline coordinating document loading, chunking, embedding generation, and database upserts."""

    def __init__(
        self,
        db_session: Session,
        embedding_service: Optional[BaseEmbeddingService] = None,
    ) -> None:
        self.db = db_session
        self.embedding_service = embedding_service or get_embedding_service()

    def ingest_file(
        self,
        file_path: Path,
        metadata_dir: Optional[Path] = None,
        force_reindex: bool = False,
    ) -> Tuple[bool, int]:
        """Ingests a single document idempotently.
        
        Returns:
            Tuple[is_new_or_updated (bool), chunk_count (int)]
        """
        path = file_path.resolve()
        content_hash = compute_file_hash(path)

        # 1. Check if document with this exact content hash already exists in PostgreSQL
        existing_doc = (
            self.db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.content_hash == content_hash)
            .first()
        )

        if existing_doc and not force_reindex:
            chunk_count = (
                self.db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == existing_doc.id)
                .count()
            )
            return False, chunk_count

        # 2. Extract sections using format-aware loader
        sections = load_document(path)

        # 3. Read metadata from companion file or derive from loaded section frontmatter
        meta = find_companion_metadata(path, metadata_dir)
        title = meta.title if meta else path.stem.replace("_", " ").title()
        source = meta.source if meta else "Authoritative Source"
        doc_type = meta.document_type if meta else "report"
        year = meta.publication_year if meta else None
        authors = meta.authors if meta else []
        doi = meta.doi if meta else None
        url = meta.url if meta else None
        license_str = meta.license if meta else None
        scope = meta.geographic_scope if meta else "global"
        topics = meta.topics if meta else []
        variables = meta.variables if meta else []

        # 4. Chunk document into section-aware semantic chunks
        chunks = chunk_document(sections=sections, doc_title=title)
        if not chunks:
            raise ValueError(f"Ingestion produced 0 chunks for document: {path}")

        # 5. Generate embeddings in batch
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts)

        # Validate vector dimension
        expected_dim = self.embedding_service.dimension
        if len(embeddings) > 0 and len(embeddings[0]) != expected_dim:
            raise ValueError(
                f"Generated embedding dimension {len(embeddings[0])} does not match "
                f"service dimension {expected_dim}"
            )

        # 6. Database record creation
        if existing_doc and force_reindex:
            # Delete old chunks
            self.db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == existing_doc.id).delete()
            doc_record = existing_doc
            doc_record.title = title
            doc_record.source = source
            doc_record.document_type = doc_type
            doc_record.publication_year = year
            doc_record.authors = authors
            doc_record.doi = doi
            doc_record.source_url = url
            doc_record.license = license_str
            doc_record.geographic_scope = scope
            doc_record.topics = topics
            doc_record.variables = variables
        else:
            doc_record = KnowledgeDocument(
                title=title,
                source=source,
                document_type=doc_type,
                publication_year=year,
                authors=authors,
                doi=doi,
                source_url=url,
                license=license_str,
                geographic_scope=scope,
                topics=topics,
                variables=variables,
                content_hash=content_hash,
            )
            self.db.add(doc_record)
            self.db.flush()

        # Insert chunks
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_record = KnowledgeChunk(
                document_id=doc_record.id,
                chunk_index=idx,
                chunk_text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                chunk_hash=chunk.chunk_hash,
                topics=chunk.topics,
                variables=chunk.variables,
                embedding=emb,
                token_count=chunk.token_count,
            )
            self.db.add(chunk_record)

        self.db.commit()
        return True, len(chunks)

    def ingest_directory(
        self,
        source_dir: Path,
        metadata_dir: Optional[Path] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """Recursively discovers and ingests all supported documents in a directory."""
        if not source_dir.exists():
            raise FileNotFoundError(f"Knowledge source directory does not exist: {source_dir}")

        supported_exts = {".pdf", ".md", ".markdown", ".txt"}
        discovered_files = [
            p for p in source_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in supported_exts
            and not p.name.startswith(".")
            and p.name.lower() != "readme.md"
        ]

        results = {
            "total_discovered": len(discovered_files),
            "ingested_new": 0,
            "skipped_duplicates": 0,
            "total_chunks": 0,
            "processed_documents": [],
        }

        for file_path in discovered_files:
            try:
                is_new, count = self.ingest_file(
                    file_path=file_path,
                    metadata_dir=metadata_dir,
                    force_reindex=force_reindex,
                )
                if is_new:
                    results["ingested_new"] += 1
                else:
                    results["skipped_duplicates"] += 1

                results["total_chunks"] += count
                results["processed_documents"].append({
                    "file": str(file_path.name),
                    "status": "new" if is_new else "skipped_duplicate",
                    "chunks": count,
                })
            except Exception as e:
                print(f"Error ingesting '{file_path}': {e}")
                raise e

        return results


def main() -> None:
    """CLI runner for ingesting scientific documents into the PostgreSQL + pgvector store."""
    parser = argparse.ArgumentParser(description="Ingest scientific literature into DARUKAA.EARTH pgvector store.")
    parser.add_argument(
        "--source",
        type=str,
        default=settings.KNOWLEDGE_SOURCE_DIR,
        help="Path to directory containing source documents (PDF, MD, TXT)",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        default=settings.KNOWLEDGE_METADATA_DIR,
        help="Path to directory containing JSON metadata",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if document hash already exists",
    )

    args = parser.parse_args()
    source_path = Path(args.source)
    metadata_path = Path(args.metadata)

    print(f"Initializing Scientific Ingestion Pipeline...")
    print(f"Source Directory:   {source_path.resolve()}")
    print(f"Metadata Directory: {metadata_path.resolve()}")
    print(f"Embedding Model:    {settings.EMBEDDING_MODEL} (dim={settings.EMBEDDING_DIMENSION})")

    db = SessionLocal()
    try:
        pipeline = IngestionPipeline(db_session=db)
        summary = pipeline.ingest_directory(
            source_dir=source_path,
            metadata_dir=metadata_path,
            force_reindex=args.force,
        )

        print("\n--- Ingestion Complete ---")
        print(f"Discovered Files:    {summary['total_discovered']}")
        print(f"New Ingested:        {summary['ingested_new']}")
        print(f"Skipped Duplicates:  {summary['skipped_duplicates']}")
        print(f"Total Chunks:        {summary['total_chunks']}")
        for doc in summary["processed_documents"]:
            print(f"  • {doc['file']}: {doc['status']} ({doc['chunks']} chunks)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
