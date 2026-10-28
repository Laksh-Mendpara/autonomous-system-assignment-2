"""
vector_store.py — Persistent ChromaDB vector store for the Academic Helpdesk Agent.

Design decisions:
  - Single ChromaDB collection ("academic_helpdesk") with rich metadata per chunk.
  - Persistent storage at `vectorstore/chroma_db/` — survives process restarts.
  - Uses a custom SentenceTransformer embedding function (not the default OpenAI one).
  - Supports incremental upsert: existing chunks (by ID) are updated, not re-inserted.
  - Provides filtered queries: caller can restrict retrieval to specific categories,
    departments, semesters, file types, or course codes.
"""

from __future__ import annotations

import hashlib
from typing import Any

import chromadb
from chromadb.config import Settings

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    DEFAULT_TOP_K,
    META_CATEGORY,
    META_COURSE_CODE,
    META_DEPT,
    META_DOCTYPE,
    META_FILENAME,
    META_SEMESTER,
    META_SOURCE,
)
from src.rag.chunker import Chunk
from src.rag.embedder import EmbeddingModel


class _ChromaEmbeddingFunction(chromadb.EmbeddingFunction):
    """Adapter that lets ChromaDB use our SentenceTransformer EmbeddingModel."""

    def __init__(self, embedder: EmbeddingModel):
        self._embedder = embedder

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return self._embedder.embed(input)


class VectorStore:
    """
    Persistent ChromaDB vector store.

    Usage:
        store = VectorStore()
        store.build_index(chunks)          # initial ingestion
        store.upsert(chunks)               # incremental updates
        results = store.query("attendance requirement", top_k=5)
        results = store.query("slot for autonomous systems",
                              filters={"category": "timetable"})
    """

    def __init__(self, embedder: EmbeddingModel | None = None):
        self._embedder = embedder or EmbeddingModel()
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self._ef = _ChromaEmbeddingFunction(self._embedder)
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )
        count = self._collection.count()
        print(
            f"[VectorStore] Collection '{CHROMA_COLLECTION_NAME}' — "
            f"{count} chunks stored."
        )
        if count == 0:
            self._auto_ingest()

    def _auto_ingest(self) -> None:
        """Automatically index documents from data/ if the database is uninitialized."""
        try:
            from src.rag.document_loader import DocumentLoader
            from src.rag.chunker import Chunker
            print("[VectorStore] Initializing vector index from data/ documents...")
            loader = DocumentLoader()
            docs = loader.load_all()
            chunker = Chunker()
            chunks = chunker.chunk_all(docs)
            self.upsert(chunks)
            print(f"[VectorStore] Ingestion complete: {self._collection.count()} chunks indexed.")
        except Exception as e:
            print(f"[VectorStore] Note: Could not auto-ingest ({e}).")

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def build_index(self, chunks: list[Chunk], reset: bool = False) -> None:
        """
        Full index build from a list of Chunk objects.

        Args:
            chunks: All chunks to index.
            reset:  If True, drop and recreate the collection before indexing.
                    Set to True only when you want to completely rebuild the index.
        """
        if reset:
            print("[VectorStore] Resetting collection…")
            self._client.delete_collection(CHROMA_COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                embedding_function=self._ef,
                metadata={"hnsw:space": "cosine"},
            )

        self.upsert(chunks)

    def upsert(self, chunks: list[Chunk], batch_size: int = 256) -> None:
        """
        Upsert (insert-or-update) chunks into the vector store.
        Chunk IDs are deterministic hashes of (source + chunk_index) so re-indexing
        the same file updates existing entries rather than creating duplicates.
        """
        if not chunks:
            return

        ids, texts, metadatas = [], [], []
        for chunk in chunks:
            if not chunk.text.strip():
                continue
            chunk_id = self._make_id(chunk)
            ids.append(chunk_id)
            texts.append(chunk.text)
            metadatas.append(self._sanitize_metadata(chunk.metadata))

        # Batch upserts
        total = len(ids)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            self._collection.upsert(
                ids=ids[start:end],
                documents=texts[start:end],
                metadatas=metadatas[start:end],
            )
            pct = int(end / total * 100)
            print(f"\r[VectorStore] Upserted {end}/{total} chunks ({pct}%)", end="", flush=True)

        print(f"\n[VectorStore] Done. Total stored: {self._collection.count()}")

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """
        Semantic search with optional metadata filtering.

        Args:
            query_text: Natural language query string.
            top_k:      Number of results to return.
            filters:    Dict of metadata key-value pairs for pre-filtering.
                        Supported keys: "category", "dept", "semester",
                                        "doc_type", "course_code", "filename"
                        Example: {"category": "timetable", "semester": "sem1"}
                        Supports $in for multi-value:
                        Example: {"category": {"$in": ["timetable", "faculty"]}}

        Returns:
            List of dicts with keys: text, metadata, distance, score
        """
        where = self._build_where_clause(filters) if filters else None

        results = self._collection.query(
            query_texts=[query_text],
            n_results=min(top_k, self._collection.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return self._format_results(results)

    def query_by_ids(self, ids: list[str]) -> list[dict]:
        """Fetch specific chunks by their IDs."""
        results = self._collection.get(ids=ids, include=["documents", "metadatas"])
        out = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            out.append({"text": doc, "metadata": meta, "distance": 0.0, "score": 1.0})
        return out

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return self._collection.count()

    def get_stored_sources(self) -> set[str]:
        """Return the set of source file paths already indexed."""
        result = self._collection.get(include=["metadatas"])
        return {m.get(META_SOURCE, "") for m in result["metadatas"]}

    def needs_rebuild(self) -> bool:
        """True if the vector store is empty and needs indexing."""
        return self._collection.count() == 0

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _make_id(chunk: Chunk) -> str:
        """Deterministic chunk ID from source path + chunk index."""
        source = chunk.metadata.get(META_SOURCE, "")
        idx = chunk.metadata.get("chunk_index", chunk.metadata.get("row_index", 0))
        raw = f"{source}::{idx}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _sanitize_metadata(meta: dict) -> dict:
        """ChromaDB metadata values must be str, int, float, or bool."""
        sanitized = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                sanitized[k] = v
            else:
                sanitized[k] = str(v)
        return sanitized

    @staticmethod
    def _build_where_clause(filters: dict) -> dict:
        """
        Build a ChromaDB `where` clause from a flat filters dict.

        Single value:   {"category": "policies"}         → {"category": {"$eq": "policies"}}
        Multi-value:    {"category": ["policies","timetable"]} → {"category": {"$in": [...]}}
        Already clause: {"category": {"$in": [...]}}     → passed through as-is
        Multiple keys:  {"category": "timetable", "semester": "sem1"} → {"$and": [...]}
        """
        clauses = []
        for key, val in filters.items():
            if isinstance(val, dict):
                clauses.append({key: val})
            elif isinstance(val, (list, tuple)):
                clauses.append({key: {"$in": list(val)}})
            else:
                clauses.append({key: {"$eq": str(val)}})

        if not clauses:
            return {}
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @staticmethod
    def _format_results(raw: dict) -> list[dict]:
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        dists = raw.get("distances", [[]])[0]

        out = []
        for doc, meta, dist in zip(docs, metas, dists):
            # Convert cosine distance → similarity score (0 to 1, higher = better)
            score = max(0.0, 1.0 - dist)
            out.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "distance": round(dist, 4),
                    "score": round(score, 4),
                }
            )
        return out

