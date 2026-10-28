"""
retriever.py — High-level RAG retriever combining semantic search + metadata filtering.

This is the main interface used by the agent to retrieve relevant chunks.
It adds:
  - Query routing (detect what type of query it is and apply appropriate filters)
  - Citation formatting
  - Score thresholding to suppress irrelevant results
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config import DEFAULT_TOP_K, DISTANCE_THRESHOLD, META_CATEGORY, META_SOURCE
from src.rag.vector_store import VectorStore


@dataclass
class RetrievalResult:
    """A single retrieved chunk with metadata and citation."""

    text: str
    source: str
    category: str
    score: float
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        """Human-readable citation string."""
        filename = self.metadata.get("filename", self.source)
        return f"[Source: {filename} | Category: {self.category} | Relevance: {self.score:.2f}]"


class Retriever:
    """
    Smart retriever that:
      1. Detects query intent to determine which document categories to search.
      2. Runs ChromaDB semantic search with optional metadata filters.
      3. Filters results by score threshold.
      4. Returns ranked RetrievalResult objects with citations.

    Usage:
        retriever = Retriever(vector_store)
        results = retriever.retrieve("What is the attendance requirement for Major exam?")
        results = retriever.retrieve("Slot for CSL7570", top_k=3)
        results = retriever.retrieve("email for Autonomous Systems instructor",
                                     force_categories=["faculty"])
    """

    # Intent patterns: maps regex patterns → preferred categories
    INTENT_ROUTING: list[tuple[re.Pattern, list[str]]] = [
        # Timetable / schedule queries
        (re.compile(r"\b(slot|schedule|timing|when|timetable|class|time)\b", re.I),
         ["timetable", "course_details"]),
        # Instructor / email queries
        (re.compile(r"\b(instructor|professor|faculty|email|contact|who teaches|taught by)\b", re.I),
         ["faculty", "timetable"]),
        # Policy / regulation queries
        (re.compile(r"\b(attendance|absent|leave|sick|makeup|make.up|exam|grading|grade|cgpa|sgpa|credit|regulation|rule|policy|registration|withdraw|drop|backlog|branch.change)\b", re.I),
         ["policies", "office_orders"]),
        # Curriculum / degree queries
        (re.compile(r"\b(curriculum|syllabus|btech|b\.tech|mtech|degree|elective|open elective|oe|core|programme|program|department)\b", re.I),
         ["curriculum", "policies", "course_details"]),
        # Email drafting
        (re.compile(r"\b(draft|write|compose|send|email to)\b", re.I),
         ["faculty", "office_orders", "policies"]),
        # Count / enumerate queries
        (re.compile(r"\b(how many|count|list|enumerate|floated|offered)\b", re.I),
         ["timetable", "course_details"]),
    ]

    def __init__(self, vector_store: VectorStore):
        self._store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        force_categories: list[str] | None = None,
        force_filters: dict | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query:            Natural language query.
            top_k:            Max number of results to return.
            force_categories: Override auto-routing with specific categories.
            force_filters:    Additional metadata filters (merged with category filter).
            score_threshold:  Minimum relevance score (0-1). Defaults to config value.

        Returns:
            List of RetrievalResult sorted by score descending.
        """
        threshold = score_threshold if score_threshold is not None else (1.0 - DISTANCE_THRESHOLD)

        # Build filters
        filters = {}
        categories = force_categories or self._route_query(query)
        if categories:
            filters[META_CATEGORY] = categories if len(categories) > 1 else categories[0]
        if force_filters:
            filters.update(force_filters)

        # Run semantic search
        raw = self._store.query(query, top_k=top_k * 2, filters=filters or None)

        # If no results with category filter, retry without to avoid empty responses
        if not raw and categories:
            raw = self._store.query(query, top_k=top_k, filters=force_filters or None)

        # Filter by threshold and deduplicate
        seen_texts: set[str] = set()
        results: list[RetrievalResult] = []
        for item in raw:
            if item["score"] < threshold:
                continue
            text_key = item["text"][:100]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            results.append(
                RetrievalResult(
                    text=item["text"],
                    source=item["metadata"].get(META_SOURCE, ""),
                    category=item["metadata"].get(META_CATEGORY, ""),
                    score=item["score"],
                    metadata=item["metadata"],
                )
            )

        return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        **kwargs,
    ) -> str:
        """
        Retrieve chunks and format them as a context string for LLM prompting.
        Includes inline citations.
        """
        results = self.retrieve(query, top_k=top_k, **kwargs)
        if not results:
            return "No relevant documents found."

        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"[{i}] {r.citation}\n{r.text}"
            )
        return "\n\n---\n\n".join(parts)

    def retrieve_by_course_code(self, course_code: str, top_k: int = 5) -> list[RetrievalResult]:
        """Targeted retrieval for a specific course code."""
        return self.retrieve(
            query=course_code,
            top_k=top_k,
            force_filters={"course_code": course_code},
        )

    # ── Query Routing ─────────────────────────────────────────────────────────

    def _route_query(self, query: str) -> list[str]:
        """
        Detect which document categories are most relevant for this query.
        Returns a list of category names (empty = search all).
        """
        matched_categories: list[str] = []
        for pattern, categories in self.INTENT_ROUTING:
            if pattern.search(query):
                for cat in categories:
                    if cat not in matched_categories:
                        matched_categories.append(cat)

        return matched_categories

