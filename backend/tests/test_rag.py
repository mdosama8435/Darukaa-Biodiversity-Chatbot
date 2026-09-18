"""Test suite for scientific document loading, chunking, vocabulary tagging, embeddings, and retrieval."""

import hashlib
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.rag.schemas import (
    DocumentMetadata,
    ProcessedChunk,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.rag.vocabulary import tag_text
from app.rag.loaders import load_document, load_pdf, load_markdown, load_txt
from app.rag.chunking import clean_text, split_into_sentences, chunk_document
from app.rag.embeddings import (
    BaseEmbeddingService,
    SentenceTransformerEmbeddingService,
    get_embedding_service,
)
from app.rag.retriever import KnowledgeRetriever
from app.rag.ingestion import compute_file_hash, find_companion_metadata, IngestionPipeline
from app.database.models import KnowledgeDocument, KnowledgeChunk
from app.database.connection import get_db

client = TestClient(app)


class TestDocumentLoaders:
    """Tests for PDF, Markdown, and plain text loading."""

    def test_markdown_loading_with_headings(self, tmp_path):
        """Verifies Markdown loader detects headers and parses sections."""
        md_file = tmp_path / "test_doc.md"
        md_file.write_text(
            "# Forest Soil Dynamics\n\nForest soils maintain high organic matter.\n\n"
            "## Soil Microbes\n\nMycorrhizal fungi facilitate phosphorus uptake.",
            encoding="utf-8",
        )

        sections = load_document(md_file)
        assert len(sections) == 2
        assert sections[0].section == "Forest Soil Dynamics"
        assert "Forest soils maintain" in sections[0].text
        assert sections[1].section == "Soil Microbes"
        assert "Mycorrhizal fungi" in sections[1].text

    def test_txt_loading(self, tmp_path):
        """Verifies plain text document loading."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text("Long-term agroforestry increases soil carbon stocks.", encoding="utf-8")

        sections = load_document(txt_file)
        assert len(sections) == 1
        assert "agroforestry increases soil carbon" in sections[0].text

    def test_pdf_loading_real_document(self):
        """Verifies real PDF loader extracts pages and preserves page numbers."""
        pdf_path = Path("knowledge/sources/research/torralba_2016_agroforestry_biodiversity.pdf")
        if not pdf_path.exists():
            pytest.skip("Torralba research PDF not present on disk.")

        sections = load_document(pdf_path)
        assert len(sections) >= 2
        pages = [s.page_number for s in sections]
        assert 1 in pages
        assert 2 in pages
        assert any("Agroforestry" in s.text for s in sections)

    def test_empty_file_fails_explicitly(self, tmp_path):
        """Verifies empty documents fail with explicit ValueError."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="empty"):
            load_document(empty_file)

    def test_unsupported_format_fails_explicitly(self, tmp_path):
        """Verifies unsupported extensions raise ValueError."""
        doc = tmp_path / "unknown.docx"
        doc.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported document format"):
            load_document(doc)


class TestControlledVocabulary:
    """Tests for deterministic environmental variable and topic tagging."""

    def test_variable_detection_rules(self):
        """Verifies regex/keyword tagging for environmental variables."""
        text_1 = "Measured soil organic carbon content was 2.4% with optimal soil pH 6.8."
        vars_1, topics_1 = tag_text(text_1)
        assert "soil_organic_carbon" in vars_1
        assert "soil_ph" in vars_1
        assert "soil" in topics_1

        text_2 = "Annual rainfall deficit triggered severe drought and forest clearance."
        vars_2, topics_2 = tag_text(text_2)
        assert "rainfall" in vars_2
        assert "deforestation" in vars_2
        assert "climate" in topics_2

    def test_no_false_positive_tagging(self):
        """Ensures text without relevant keywords does not receive ungrounded tags."""
        text = "The laboratory protocol was established in September."
        variables, topics = tag_text(text)
        assert variables == []
        assert topics == []


class TestChunking:
    """Tests for section-aware semantic chunking."""

    def test_clean_text(self):
        """Verifies text sanitization."""
        raw = "Line 1\r\nLine 2   with   extra  spaces\n\n\n\nLine 3"
        cleaned = clean_text(raw)
        assert "\r" not in cleaned
        assert "Line 2 with extra spaces" in cleaned
        assert "\n\n\n" not in cleaned

    def test_section_aware_chunking_deterministic_hash(self):
        """Verifies that chunking generates consistent SHA-256 hashes for identical text."""
        sections = load_document("knowledge/sources/fao/fao_soil_biodiversity_report_2020.md")
        chunks_1 = chunk_document(sections, doc_title="FAO Soil Biodiversity")
        chunks_2 = chunk_document(sections, doc_title="FAO Soil Biodiversity")

        assert len(chunks_1) == len(chunks_2)
        assert len(chunks_1) > 0
        for c1, c2 in zip(chunks_1, chunks_2):
            assert c1.chunk_hash == c2.chunk_hash
            assert len(c1.chunk_hash) == 64  # SHA-256 hexdigest length


class TestEmbeddingService:
    """Tests for embedding generation and strict dimension validation."""

    def test_embedding_generation(self):
        """Generates real embeddings using the configured sentence-transformer model."""
        service = get_embedding_service()
        assert service.dimension == 384

        texts = ["Soil biodiversity supports terrestrial carbon cycling.", "Rainfall variability."]
        vectors = service.embed_texts(texts)
        assert len(vectors) == 2
        assert len(vectors[0]) == 384
        assert len(vectors[1]) == 384

    def test_dimension_mismatch_fails_explicitly(self):
        """Ensures that configuring a mismatched dimension raises an explicit ValueError without padding."""
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            SentenceTransformerEmbeddingService(
                model_name=settings.EMBEDDING_MODEL,
                expected_dimension=512,  # Deliberate mismatch
            )


class TestSearchSchemasAndApiValidation:
    """Tests for Pydantic search schemas and validation."""

    def test_search_request_validation(self):
        """Validates query bounds and top_k ranges."""
        valid_req = KnowledgeSearchRequest(query="soil carbon", top_k=10, min_similarity=0.5)
        assert valid_req.query == "soil carbon"
        assert valid_req.top_k == 10

        with pytest.raises(ValueError):
            KnowledgeSearchRequest(query="   ")  # Empty query

        with pytest.raises(ValueError):
            KnowledgeSearchRequest(query="valid", top_k=0)  # ge=1

        with pytest.raises(ValueError):
            KnowledgeSearchRequest(query="valid", min_similarity=1.5)  # le=1.0

    def test_empty_knowledge_api_search(self):
        """Verifies POST /api/v1/knowledge/search returns honest response when database is empty."""
        # Using dependency override to simulate empty DB query without hardcoding
        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        app.dependency_overrides[get_db] = lambda: mock_session
        try:
            resp = client.post(
                "/api/v1/knowledge/search",
                json={"query": "non-existent concept", "top_k": 5},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "non-existent concept"
            assert data["results_count"] == 0
            assert data["results"] == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_documents_api_endpoint(self):
        """Verifies GET /api/v1/knowledge/documents returns structured list."""
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.title = "FAO Report"
        mock_doc.source = "FAO"
        mock_doc.document_type = "report"
        mock_doc.publication_year = 2020
        mock_doc.authors = ["FAO"]
        mock_doc.source_url = "https://doi.org/10.4060/cb1924en"
        mock_doc.doi = "10.4060/cb1924en"
        mock_doc.license = "CC BY-NC-SA 3.0"
        mock_doc.variables = ["soil_organic_carbon"]
        mock_doc.topics = ["soil"]

        mock_session = MagicMock()
        mock_session.query.return_value.order_by.return_value.all.return_value = [mock_doc]
        mock_session.query.return_value.filter.return_value.count.return_value = 9

        app.dependency_overrides[get_db] = lambda: mock_session
        try:
            resp = client.get("/api/v1/knowledge/documents")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["title"] == "FAO Report"
            assert data[0]["source"] == "FAO"
            assert data[0]["chunk_count"] == 9
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestIdempotency:
    """Tests for content hash idempotency."""

    def test_file_hash_consistency(self, tmp_path):
        """Verifies that identical files produce identical content hashes."""
        f1 = tmp_path / "doc1.txt"
        f2 = tmp_path / "doc2.txt"
        f1.write_text("Scientific content on soil biodiversity.", encoding="utf-8")
        f2.write_text("Scientific content on soil biodiversity.", encoding="utf-8")

        h1 = compute_file_hash(f1)
        h2 = compute_file_hash(f2)
        assert h1 == h2
        assert len(h1) == 64


@pytest.mark.integration
class TestPostgreSQLPgvectorIntegration:
    """Integration test suite executing the complete RAG path:
    REAL DOCUMENT -> REAL EMBEDDINGS -> REAL POSTGRESQL -> REAL PGVECTOR -> REAL COSINE RETRIEVAL.
    """

    def test_semantic_retrieval_integration(self):
        """Full integration test requiring live PostgreSQL with pgvector extension.
        
        Per Critical Rule 14:
        - If PostgreSQL is unavailable, skips cleanly without substituting an in-memory fake.
        - When running against PostgreSQL, validates genuine cosine similarity and source traceability.
        """
        import psycopg2
        from sqlalchemy import text
        from app.database.connection import engine, SessionLocal

        # Probe if PostgreSQL is reachable
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            pytest.skip(f"PostgreSQL + pgvector is not available ({e}); skipping live integration test per Rule 14.")

        # If PostgreSQL is reachable, run the full pipeline
        db = SessionLocal()
        try:
            pipeline = IngestionPipeline(db_session=db)
            fao_file = Path("knowledge/sources/fao/fao_soil_biodiversity_report_2020.md")
            meta_dir = Path("knowledge/metadata")
            is_new, count = pipeline.ingest_file(fao_file, metadata_dir=meta_dir, force_reindex=False)
            assert count > 0

            retriever = KnowledgeRetriever()
            req = KnowledgeSearchRequest(
                query="How does soil organic carbon affect soil biodiversity and microbial biomass?",
                top_k=3,
                min_similarity=0.2,
            )
            response = retriever.search(db=db, request=req)

            assert response.results_count > 0
            top_hit = response.results[0]
            assert top_hit.similarity > 0.0
            assert top_hit.source == "FAO"
            assert "doi.org" in (top_hit.url or "")
            assert "soil" in top_hit.content.lower()
        finally:
            db.close()
