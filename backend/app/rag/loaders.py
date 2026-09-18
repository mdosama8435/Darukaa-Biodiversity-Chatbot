"""Document loading utilities for PDF, Markdown, and plain text files.

Preserves page numbers, section headers, and metadata without silent failures.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LoadedSection(BaseModel):
    """An extracted section or page from a document with structural provenance."""
    text: str = Field(..., min_length=1)
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def load_pdf(file_path: Path) -> List[LoadedSection]:
    """Loads a PDF file page-by-page using pypdf, preserving page numbers and heading cues."""
    import pypdf

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    sections: List[LoadedSection] = []
    try:
        reader = pypdf.PdfReader(str(file_path))
        num_pages = len(reader.pages)
        if num_pages == 0:
            raise ValueError(f"PDF document is empty (0 pages): {file_path}")

        current_section = "Introduction"
        for page_idx, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            text = extracted.strip()
            if not text:
                continue

            # Detect heading lines (e.g. all caps or numbered sections)
            lines = text.split("\n")
            first_non_empty = next((line.strip() for line in lines if line.strip()), "")
            if first_non_empty and len(first_non_empty) < 100 and (
                first_non_empty.isupper() or re.match(r"^(?:[0-9]+\.|\bChapter|\bSection)\s+", first_non_empty)
            ):
                current_section = first_non_empty

            sections.append(
                LoadedSection(
                    text=text,
                    page_number=page_idx,
                    section=current_section,
                    metadata={"total_pages": num_pages, "format": "pdf"},
                )
            )

        if not sections:
            raise ValueError(f"No extractable text found in PDF: {file_path}. Document may be scanned/image-only.")

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise e
        raise RuntimeError(f"Failed to read and parse PDF file '{file_path}': {str(e)}") from e

    return sections


def load_markdown(file_path: Path) -> List[LoadedSection]:
    """Loads a Markdown document, parsing headers into structural sections and extracting frontmatter."""
    if not file_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Unable to read Markdown file '{file_path}': {str(e)}") from e

    if not content.strip():
        raise ValueError(f"Markdown file is empty: {file_path}")

    # Parse optional YAML frontmatter
    frontmatter: Dict[str, Any] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1]
            body = parts[2]
            for line in raw_fm.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip("\"'")

    sections: List[LoadedSection] = []
    lines = body.split("\n")
    current_heading = frontmatter.get("title", "Document Overview")
    current_block: List[str] = []

    for line in lines:
        header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if header_match:
            # Commit preceding section if non-empty
            block_text = "\n".join(current_block).strip()
            if block_text:
                sections.append(
                    LoadedSection(
                        text=block_text,
                        page_number=None,
                        section=current_heading,
                        metadata={**frontmatter, "format": "markdown"},
                    )
                )
                current_block = []
            current_heading = header_match.group(2).strip()
        else:
            current_block.append(line)

    remaining_text = "\n".join(current_block).strip()
    if remaining_text:
        sections.append(
            LoadedSection(
                text=remaining_text,
                page_number=None,
                section=current_heading,
                metadata={**frontmatter, "format": "markdown"},
            )
        )

    if not sections:
        raise ValueError(f"No textual content extracted from Markdown: {file_path}")

    return sections


def load_txt(file_path: Path) -> List[LoadedSection]:
    """Loads a plain text document, preserving content and paragraphs."""
    if not file_path.exists():
        raise FileNotFoundError(f"Text file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Unable to read text file '{file_path}': {str(e)}") from e

    trimmed = content.strip()
    if not trimmed:
        raise ValueError(f"Text file is empty: {file_path}")

    return [
        LoadedSection(
            text=trimmed,
            page_number=None,
            section="General Text",
            metadata={"format": "txt"},
        )
    ]


def load_document(file_path: Path | str) -> List[LoadedSection]:
    """Dispatches to the appropriate loader based on file suffix.
    
    Fails explicitly with clear diagnostic error on unsupported or corrupted files.
    """
    path = Path(file_path).resolve()
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(path)
    elif suffix in (".md", ".markdown"):
        return load_markdown(path)
    elif suffix in (".txt", ".text"):
        return load_txt(path)
    else:
        raise ValueError(
            f"Unsupported document format '{suffix}' for file '{path}'. "
            "Supported formats: .pdf, .md, .txt"
        )
