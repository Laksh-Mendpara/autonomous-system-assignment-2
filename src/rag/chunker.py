"""
chunker.py — Document chunking strategies for the Academic Helpdesk RAG pipeline.

Strategies:
  - "recursive": Splits text on markdown headings → paragraphs → sentences → words.
                 Preserves semantic context with configurable overlap.
  - "row":       CSV rows are already individual documents; no further chunking needed.

Returns a list of `Chunk` objects with text + metadata (source, category, chunk_index).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from src.config import CHUNK_CONFIGS, DEFAULT_CHUNK_CONFIG, META_CATEGORY, META_CHUNK_INDEX
from src.rag.document_loader import RawDocument


@dataclass
class Chunk:
    """A single embeddable text chunk with metadata."""

    text: str
    metadata: dict = field(default_factory=dict)


class DocumentChunker:
    """
    Splits RawDocuments into Chunks using per-category strategies.

    Usage:
        chunker = DocumentChunker()
        chunks = chunker.chunk_all(raw_docs)
        chunks = chunker.chunk(doc)
    """

    def chunk_all(self, docs: list[RawDocument]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for doc in docs:
            chunks.extend(self.chunk(doc))
        return chunks

    def chunk(self, doc: RawDocument) -> list[Chunk]:
        category = doc.metadata.get(META_CATEGORY, "")
        cfg = CHUNK_CONFIGS.get(category, DEFAULT_CHUNK_CONFIG)
        strategy = cfg.get("strategy", "recursive")

        if strategy == "row":
            # CSV row — already a single meaningful unit
            return [Chunk(text=doc.text.strip(), metadata={**doc.metadata, META_CHUNK_INDEX: 0})]

        # Recursive strategy
        return self._recursive_split(doc, cfg["chunk_size"], cfg["chunk_overlap"])

    # ── Recursive Text Splitter ───────────────────────────────────────────────

    def _recursive_split(
        self,
        doc: RawDocument,
        chunk_size: int,
        overlap: int,
    ) -> list[Chunk]:
        """
        Hierarchical splitter: tries to split on bigger separators first,
        falls back to smaller ones if chunks are still too large.
        """
        # Separator priority: markdown headings → double-newline → single newline → sentence → word
        SEPARATORS = [
            r"\n#{1,4} ",     # Markdown headings
            r"\n\n+",          # Paragraph breaks
            r"\n",             # Line breaks
            r"(?<=[.!?])\s+",  # Sentence boundaries
            r"\s+",            # Whitespace (word boundary)
        ]

        raw_chunks = self._split_recursive(doc.text, chunk_size, SEPARATORS)
        raw_chunks = self._apply_overlap(raw_chunks, overlap)

        return [
            Chunk(
                text=text.strip(),
                metadata={**doc.metadata, META_CHUNK_INDEX: idx},
            )
            for idx, text in enumerate(raw_chunks)
            if text.strip()
        ]

    def _split_recursive(self, text: str, chunk_size: int, separators: list[str]) -> list[str]:
        """Recursively split text, trying each separator until chunks fit chunk_size."""
        if len(text) <= chunk_size or not separators:
            return [text]

        sep = separators[0]
        remaining_seps = separators[1:]

        # Split on this separator
        parts = re.split(sep, text)

        result: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + "\n" + part).strip() if current else part.strip()
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                # If this part alone is too big, recurse with smaller separators
                if len(part) > chunk_size:
                    result.extend(self._split_recursive(part, chunk_size, remaining_seps))
                    current = ""
                else:
                    current = part.strip()

        if current:
            result.append(current)

        return result

    def _apply_overlap(self, chunks: list[str], overlap: int) -> list[str]:
        """
        Add trailing context from the previous chunk to the start of each chunk
        to preserve cross-boundary context.
        """
        if overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            # Take the last `overlap` characters of the previous chunk
            tail = prev[-overlap:].strip() if len(prev) > overlap else prev.strip()
            overlapped.append(tail + "\n" + chunks[i])

        return overlapped

