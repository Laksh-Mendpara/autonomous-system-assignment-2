"""
indexer.py — Orchestrates the full document indexing pipeline.

This script:
  1. Checks if the persistent ChromaDB store already exists and is populated.
  2. If so, skips rebuilding (persistent index reuse).
  3. If not (or if --rebuild flag is given), runs the full pipeline:
       Load → Chunk → Embed → Upsert into ChromaDB

Run as:
    uv run python -m src.indexer            # smart rebuild (skip if already indexed)
    uv run python -m src.indexer --rebuild  # force full rebuild
    uv run python -m src.indexer --category policies  # reindex a specific category only
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src.config import DOCUMENT_SOURCES
from src.rag.chunker import DocumentChunker
from src.rag.document_loader import DocumentLoader
from src.rag.embedder import EmbeddingModel
from src.rag.vector_store import VectorStore


def build_index(
    category: str | None = None,
    rebuild: bool = False,
    verbose: bool = True,
) -> VectorStore:
    """
    Main indexing entry point. Returns a ready VectorStore.

    Args:
        category: If set, only reindex documents from this category.
        rebuild:  If True, drop and recreate the collection.
        verbose:  Print progress messages.
    """
    embedder = EmbeddingModel()
    store = VectorStore(embedder)

    # Skip indexing if already populated and no rebuild requested
    if not rebuild and not category and not store.needs_rebuild():
        if verbose:
            print(f"[Indexer] Vector store already populated ({store.count} chunks). Skipping rebuild.")
            print("[Indexer] Use --rebuild to force re-indexing.")
        return store

    loader = DocumentLoader()
    chunker = DocumentChunker()

    if category:
        if verbose:
            print(f"[Indexer] Re-indexing category: {category}")
        raw_docs = loader.load(category)
    else:
        if verbose:
            print("[Indexer] Loading all documents…")
        raw_docs = loader.load_all()

    if verbose:
        print(f"[Indexer] Loaded {len(raw_docs)} raw documents.")

    t0 = time.time()
    chunks = chunker.chunk_all(raw_docs)
    if verbose:
        elapsed = time.time() - t0
        print(f"[Indexer] Generated {len(chunks)} chunks in {elapsed:.1f}s")

        # Show breakdown by category
        from collections import Counter
        counts = Counter(c.metadata.get("category", "?") for c in chunks)
        for cat, n in sorted(counts.items()):
            print(f"          {cat:20s}: {n} chunks")

    t1 = time.time()
    store.build_index(chunks, reset=rebuild and not category)
    if verbose:
        elapsed = time.time() - t1
        print(f"[Indexer] Indexing complete in {elapsed:.1f}s")

    return store


def main() -> None:
    parser = argparse.ArgumentParser(description="Academic Helpdesk — Document Indexer")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force a full rebuild of the vector store (drops existing data).",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=list(DOCUMENT_SOURCES.keys()),
        default=None,
        help="Only re-index documents from this category.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Academic Helpdesk — Document Indexer")
    print("=" * 60)

    t_start = time.time()
    store = build_index(category=args.category, rebuild=args.rebuild)
    total = time.time() - t_start
    print(f"\n[Indexer] Total time: {total:.1f}s | Chunks in store: {store.count}")


if __name__ == "__main__":
    main()

