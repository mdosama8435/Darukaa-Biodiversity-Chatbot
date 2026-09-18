"""Verification script running semantic retrieval queries against the ingested scientific corpus."""

import sys
from pathlib import Path
import numpy as np

# Ensure backend directory is in python search path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.rag.loaders import load_document
from app.rag.chunking import chunk_document
from app.rag.embeddings import get_embedding_service
from app.rag.ingestion import find_companion_metadata


def run_retrieval_verification() -> None:
    embedding_service = get_embedding_service()
    docs = [
        Path("knowledge/sources/fao/fao_soil_biodiversity_report_2020.md"),
        Path("knowledge/sources/ipcc/ipcc_srccl_land_degradation_2019.md"),
        Path("knowledge/sources/research/torralba_2016_agroforestry_biodiversity.pdf"),
    ]

    all_chunks = []
    meta_dir = Path("knowledge/metadata")

    print("--- 1. Document Loading and Chunking Verification ---")
    for doc_path in docs:
        sections = load_document(doc_path)
        meta = find_companion_metadata(doc_path, meta_dir)
        doc_title = meta.title if meta else doc_path.stem
        chunks = chunk_document(sections, doc_title=doc_title)
        texts = [c.text for c in chunks]
        embeddings = embedding_service.embed_texts(texts)
        for c, emb in zip(chunks, embeddings):
            all_chunks.append({
                "chunk": c,
                "embedding": np.array(emb, dtype=np.float32),
                "meta": meta,
            })
        print(f"Loaded '{doc_path.name}': {len(sections)} sections, {len(chunks)} chunks.")

    print(f"\nTotal Corpus: {len(all_chunks)} chunks across {len(docs)} documents.")
    print(f"Embedding Model: {embedding_service.model_name} (dim={embedding_service.dimension})\n")

    queries = [
        "How does soil organic carbon relate to soil biodiversity?",
        "How can agricultural land use affect biodiversity?",
        "How does rainfall variability affect ecosystems and land degradation?",
        "What is the relationship between soil pH and soil processes?",
    ]

    print("--- 2. Semantic Retrieval Query Results ---")
    for idx, q in enumerate(queries, 1):
        q_vec = np.array(embedding_service.embed_query(q), dtype=np.float32)
        scored = []
        for item in all_chunks:
            # Cosine similarity between normalized vectors = dot product
            sim = float(np.dot(q_vec, item["embedding"]))
            scored.append((sim, item))
        scored.sort(key=lambda x: x[0], reverse=True)

        top_sim, top_item = scored[0]
        c = top_item["chunk"]
        m = top_item["meta"]
        print(f"\n[Query {idx}]: \"{q}\"")
        print(f"  • Top Cosine Similarity: {top_sim:.4f}")
        print(f"  • Source Organization:  {m.source if m else 'Unknown'}")
        print(f"  • Document Title:       {m.title if m else 'Unknown'}")
        print(f"  • Source URL:           {m.url if m else 'Unknown'}")
        print(f"  • Page / Section:       Page {c.page_number} | Section: {c.section}")
        print(f"  • Tagged Variables:     {c.variables}")
        print(f"  • Tagged Topics:        {c.topics}")
        print(f"  • Content Excerpt:      \"{c.text[:240]}...\"")


if __name__ == "__main__":
    run_retrieval_verification()
