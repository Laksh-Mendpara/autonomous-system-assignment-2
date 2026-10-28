"""
embedder.py — Local embedding model wrapper using sentence-transformers.

Model: all-MiniLM-L6-v2
  - 384-dimensional dense embeddings
  - Loads from local cache directly with zero network requests
  - Fast on CPU (~14k tokens/sec on laptop)
  - Normalized for cosine similarity search in ChromaDB
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

# Enforce offline mode before importing ML libraries
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from src.config import EMBEDDING_BATCH_SIZE, EMBEDDING_CACHE_DIR, EMBEDDING_MODEL_NAME

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Wraps sentence-transformers for generating text embeddings locally."""

    _instance: "SentenceTransformer | None" = None

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model: "SentenceTransformer | None" = None

    @property
    def model(self) -> "SentenceTransformer":
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> "SentenceTransformer":
        from sentence_transformers import SentenceTransformer

        # Check for cached snapshot first for instantaneous offline load
        snapshot_parent = EMBEDDING_CACHE_DIR / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
        if snapshot_parent.exists():
            snapshots = list(snapshot_parent.glob("*"))
            if snapshots:
                print(f"[Embedder] Loading from local snapshot: {snapshots[0].name}")
                return SentenceTransformer(str(snapshots[0]))

        # Standard cache folder fallback
        return SentenceTransformer(
            self.model_name,
            cache_folder=str(EMBEDDING_CACHE_DIR),
            model_kwargs={"local_files_only": True},
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings. Returns a list of float vectors."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=True,  # L2-normalize for cosine similarity
            convert_to_numpy=True,
        )
        return embeddings.tolist()
