"""
document_loader.py — Loads documents from disk (PDF, Markdown, CSV, TXT).

Each loader returns a list of `RawDocument` objects:
    {
        "text": str,
        "metadata": dict,   # pre-populated with file-level metadata
    }
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from src.config import (
    DATA_DIR,
    DOCUMENT_SOURCES,
    META_CATEGORY,
    META_COURSE_CODE,
    META_DEPT,
    META_DOCTYPE,
    META_FILENAME,
    META_SEMESTER,
    META_SOURCE,
    SUPPORTED_EXTENSIONS,
)


@dataclass
class RawDocument:
    """Represents a single loaded document before chunking."""

    text: str
    metadata: dict = field(default_factory=dict)


class DocumentLoader:
    """
    Discovers and loads all source documents from `data/` subdirectories.

    Usage:
        loader = DocumentLoader()
        docs = loader.load_all()          # load every category
        docs = loader.load(category="policies")   # single category
    """

    def load_all(self) -> list[RawDocument]:
        docs: list[RawDocument] = []
        for category in DOCUMENT_SOURCES:
            docs.extend(self.load(category))
        return docs

    def load(self, category: str) -> list[RawDocument]:
        category_path = DOCUMENT_SOURCES.get(category)
        if category_path is None:
            raise ValueError(f"Unknown category: {category!r}")
        docs: list[RawDocument] = []
        for path in sorted(category_path.iterdir()):
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            docs.extend(self._dispatch(path, category))
        return docs

    # ── dispatch ─────────────────────────────────────────────────────────────

    def _dispatch(self, path: Path, category: str) -> list[RawDocument]:
        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._load_pdf(path, category)
        if ext in {".md", ".txt"}:
            return self._load_text(path, category)
        if ext == ".csv":
            return self._load_csv(path, category)
        return []

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _load_pdf(self, path: Path, category: str) -> list[RawDocument]:
        """Extract text from PDF using pdftotext CLI (fast, no python deps for binary PDFs)."""
        import subprocess

        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        text = result.stdout.strip()
        if not text:
            # Fallback: try PyPDF2 if pdftotext yields empty (image-based PDFs)
            text = self._pypdf_fallback(path)

        if not text:
            print(f"[WARN] Could not extract text from {path.name}")
            return []

        return [
            RawDocument(
                text=text,
                metadata=self._base_meta(path, category, "pdf"),
            )
        ]

    def _pypdf_fallback(self, path: Path) -> str:
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception:
            return ""

    # ── Markdown / TXT ────────────────────────────────────────────────────────

    def _load_text(self, path: Path, category: str) -> list[RawDocument]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return []
        return [
            RawDocument(
                text=text,
                metadata=self._base_meta(path, category, "md" if path.suffix == ".md" else "txt"),
            )
        ]

    # ── CSV ───────────────────────────────────────────────────────────────────

    def _load_csv(self, path: Path, category: str) -> list[RawDocument]:
        """
        Load CSV files.
        Each non-empty row becomes its own RawDocument with rich metadata
        so that ChromaDB can filter on course_code, dept, semester etc.
        """
        docs: list[RawDocument] = []
        base = self._base_meta(path, category, "csv")

        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Clean up the row — strip whitespace from values
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

                # Build human-readable text for the chunk
                text = self._csv_row_to_text(row, path.stem)
                if not text.strip():
                    continue

                # Enrich metadata with structured CSV fields
                meta = {**base, "row_index": i}
                for field_key, meta_key in [
                    ("course_code", META_COURSE_CODE),
                    ("dept", META_DEPT),
                    ("semester", META_SEMESTER),
                ]:
                    val = row.get(field_key, "").strip()
                    if val:
                        meta[meta_key] = val.lower() if meta_key in {META_DEPT, META_SEMESTER} else val

                docs.append(RawDocument(text=text, metadata=meta))
        return docs

    def _csv_row_to_text(self, row: dict, source_stem: str) -> str:
        """Convert a CSV row dict to natural-language text for embedding."""
        if "course_code" in row:
            # Timetable / Course-instructor rows
            parts = [
                f"Course: {row.get('course_code', '')} — {row.get('course_name', row.get('course_code', ''))}",
                f"Instructor: {row.get('instructor', row.get('Course Instructor', ''))}",
                f"Slot: {row.get('slot', '')}",
            ]
            if row.get("email"):
                parts.append(f"Email: {row.get('email')}")
            if row.get("ltp"):
                parts.append(f"LTP: {row.get('ltp')}")
            if row.get("credits"):
                parts.append(f"Credits: {row.get('credits')}")
            if row.get("dept"):
                parts.append(f"Department: {row.get('dept')}")
            if row.get("semester"):
                parts.append(f"Semester: {row.get('semester')}")
            if row.get("notes"):
                parts.append(f"Notes: {row.get('notes')}")
            return "\n".join(p for p in parts if p.split(": ", 1)[-1])
        elif "instructor_name" in row:
            # Faculty directory rows
            return (
                f"Instructor: {row.get('instructor_name', '')}\n"
                f"Department: {row.get('dept', '')}\n"
                f"Email: {row.get('email', '')}"
            )
        else:
            # Generic CSV: key=value pairs
            return " | ".join(f"{k}: {v}" for k, v in row.items() if v)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_meta(self, path: Path, category: str, doc_type: str) -> dict:
        return {
            META_SOURCE: str(path.relative_to(DATA_DIR)),
            META_CATEGORY: category,
            META_DOCTYPE: doc_type,
            META_FILENAME: path.name,
        }

