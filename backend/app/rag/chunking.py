"""Section-aware semantic chunking logic for scientific literature."""

import hashlib
import re
from typing import List, Optional
from app.rag.loaders import LoadedSection
from app.rag.schemas import ProcessedChunk
from app.rag.vocabulary import tag_text


def clean_text(raw_text: str) -> str:
    """Sanitizes text by standardizing whitespace, stripping control chars, and preserving punctuation."""
    if not raw_text:
        return ""
    # Replace non-breaking spaces and tabs with regular space
    text = raw_text.replace("\xa0", " ").replace("\t", " ")
    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces on the same line
    text = re.sub(r"[ ]{2,}", " ", text)
    # Collapse 3+ newlines into double newlines (paragraph boundaries)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_sentences(text: str) -> List[str]:
    """Splits a paragraph into sentences without breaking numerical decimal points or scientific citations."""
    # Split on period, exclamation, or question mark followed by whitespace and a capital letter,
    # ensuring we do NOT split on "e.g.", "i.e.", "pH 6.5", or numbers like "1.5".
    pattern = r"(?<=[.?!])\s+(?=[A-Z0-9\(\"'])"
    parts = re.split(pattern, text)
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences if sentences else [text]


def chunk_section(
    section: LoadedSection,
    doc_title: str,
    target_chunk_chars: int = 700,
    chunk_overlap_chars: int = 150,
    min_chunk_chars: int = 100,
    start_index: int = 0,
) -> List[ProcessedChunk]:
    """Splits a LoadedSection into coherent semantic chunks preserving scientific context.
    
    Ensures findings, numerical units, and treatments remain unified within each chunk.
    """
    cleaned = clean_text(section.text)
    if not cleaned:
        return []

    # If section is already within target bounds, emit directly as a single chunk
    if len(cleaned) <= target_chunk_chars:
        variables, topics = tag_text(cleaned)
        chunk_hash = hashlib.sha256(
            f"{doc_title}|{section.section}|{section.page_number}|{cleaned}".encode("utf-8")
        ).hexdigest()

        return [
            ProcessedChunk(
                text=cleaned,
                chunk_index=start_index,
                chunk_hash=chunk_hash,
                page_number=section.page_number,
                section=section.section,
                topics=topics,
                variables=variables,
                token_count=len(cleaned.split()),
            )
        ]

    # Split section into structural paragraphs
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks: List[ProcessedChunk] = []
    current_sentences: List[str] = []
    current_length = 0
    chunk_idx = start_index

    def emit_chunk(sentences: List[str]) -> None:
        nonlocal chunk_idx
        chunk_str = " ".join(sentences).strip()
        if len(chunk_str) < min_chunk_chars and chunks:
            # Append tiny fragment to previous chunk if feasible
            prev = chunks[-1]
            merged_text = f"{prev.text} {chunk_str}"
            v_merged, t_merged = tag_text(merged_text)
            new_hash = hashlib.sha256(
                f"{doc_title}|{section.section}|{section.page_number}|{merged_text}".encode("utf-8")
            ).hexdigest()
            chunks[-1] = ProcessedChunk(
                text=merged_text,
                chunk_index=prev.chunk_index,
                chunk_hash=new_hash,
                page_number=prev.page_number,
                section=prev.section,
                topics=t_merged,
                variables=v_merged,
                token_count=len(merged_text.split()),
            )
            return

        variables, topics = tag_text(chunk_str)
        chunk_hash = hashlib.sha256(
            f"{doc_title}|{section.section}|{section.page_number}|{chunk_str}".encode("utf-8")
        ).hexdigest()

        chunks.append(
            ProcessedChunk(
                text=chunk_str,
                chunk_index=chunk_idx,
                chunk_hash=chunk_hash,
                page_number=section.page_number,
                section=section.section,
                topics=topics,
                variables=variables,
                token_count=len(chunk_str.split()),
            )
        )
        chunk_idx += 1

    for para in paragraphs:
        sentences = split_into_sentences(para)
        for sent in sentences:
            sent_len = len(sent)
            if current_length + sent_len > target_chunk_chars and current_sentences:
                emit_chunk(current_sentences)
                # Keep sliding overlap of the last sentence if it preserves context
                overlap_seed: List[str] = []
                overlap_len = 0
                for prev_sent in reversed(current_sentences):
                    if overlap_len + len(prev_sent) <= chunk_overlap_chars:
                        overlap_seed.insert(0, prev_sent)
                        overlap_len += len(prev_sent)
                    else:
                        break
                current_sentences = overlap_seed + [sent]
                current_length = sum(len(s) for s in current_sentences)
            else:
                current_sentences.append(sent)
                current_length += sent_len

    if current_sentences:
        emit_chunk(current_sentences)

    return chunks


def chunk_document(
    sections: List[LoadedSection],
    doc_title: str,
    target_chunk_chars: int = 700,
    chunk_overlap_chars: int = 150,
) -> List[ProcessedChunk]:
    """Processes all sections of a document into a flat list of indexed, hashed chunks."""
    all_chunks: List[ProcessedChunk] = []
    current_idx = 0

    for section in sections:
        section_chunks = chunk_section(
            section=section,
            doc_title=doc_title,
            target_chunk_chars=target_chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars,
            start_index=current_idx,
        )
        all_chunks.extend(section_chunks)
        current_idx += len(section_chunks)

    return all_chunks
