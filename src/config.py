"""
config.py — Centralized configuration for the Academic Helpdesk RAG pipeline.
All paths, chunking parameters, embedding settings, and ChromaDB settings live here.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from pathlib import Path

# ─── Project Root ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── Data Paths ──────────────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"

DOCUMENT_SOURCES = {
    "policies": DATA_DIR / "policies",
    "curriculum": DATA_DIR / "curriculum",
    "timetable": DATA_DIR / "timetable",
    "faculty": DATA_DIR / "faculty",
    "course_details": DATA_DIR / "course_details",
    "office_orders": DATA_DIR / "office_orders",
}

# ─── ChromaDB Persistent Store ────────────────────────────────────────────────
CHROMA_PERSIST_DIR = PROJECT_ROOT / "vectorstore" / "chroma_db"
CHROMA_COLLECTION_NAME = "academic_helpdesk"

# ─── Embedding Model ─────────────────────────────────────────────────────────
# Using a lightweight, fast, sentence-transformer model (runs locally, no network at query time)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"   # 80MB, 384-dim, fast on CPU, good semantic quality
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "vectorstore" / "model_cache"
EMBEDDING_BATCH_SIZE = 64

# ─── Chunking Parameters ─────────────────────────────────────────────────────
CHUNK_CONFIGS = {
    # Policy docs (prose-heavy): medium chunks with sentence-aware splits
    "policies": {
        "chunk_size": 600,         # characters
        "chunk_overlap": 120,
        "strategy": "recursive",   # splits on paragraphs → sentences → words
    },
    # Curriculum PDFs: table-heavy, smaller chunks to isolate table rows
    "curriculum": {
        "chunk_size": 400,
        "chunk_overlap": 80,
        "strategy": "recursive",
    },
    # Timetable CSVs: row-by-row (each row is its own chunk with rich metadata)
    "timetable": {
        "chunk_size": 0,           # 0 = treat each row as individual chunk
        "chunk_overlap": 0,
        "strategy": "row",
    },
    # Faculty CSVs: row-by-row (same)
    "faculty": {
        "chunk_size": 0,
        "chunk_overlap": 0,
        "strategy": "row",
    },
    # Course details — larger prose documents: bigger chunks for context
    "course_details": {
        "chunk_size": 800,
        "chunk_overlap": 160,
        "strategy": "recursive",
    },
    # Office orders / circulars: smaller documents — can stay as one or two chunks
    "office_orders": {
        "chunk_size": 500,
        "chunk_overlap": 100,
        "strategy": "recursive",
    },
}

# Global fallback chunk config
DEFAULT_CHUNK_CONFIG = {"chunk_size": 500, "chunk_overlap": 100, "strategy": "recursive"}

# ─── Retrieval Parameters ─────────────────────────────────────────────────────
DEFAULT_TOP_K = 5                 # number of chunks to retrieve per query
DISTANCE_THRESHOLD = 1.2          # cosine distance above which a result is considered not relevant
                                   # (ChromaDB returns L2 by default; lower = more similar)

# ─── Supported File Types ────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".csv"}

# ─── Metadata Keys (for ChromaDB metadata filtering) ─────────────────────────
META_SOURCE = "source"            # relative file path
META_CATEGORY = "category"        # e.g. "policies", "timetable", "faculty"
META_DOCTYPE = "doc_type"         # "pdf", "md", "csv"
META_DEPT = "dept"                # for CSV rows that have a dept field
META_SEMESTER = "semester"        # "Sem1", "Sem2"
META_COURSE_CODE = "course_code"  # for timetable / faculty rows
META_CHUNK_INDEX = "chunk_index"  # sequential index within source doc
META_FILENAME = "filename"        # bare filename

