"""
benchmark_prompts.py — Benchmark questions loader for Academic Helpdesk evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BENCHMARK_FILE = Path(__file__).resolve().parent.parent.parent / "benchmark_questions.json"


def load_benchmark_prompts() -> list[dict[str, Any]]:
    """Load benchmark questions from benchmark_questions.json."""
    if not BENCHMARK_FILE.exists():
        raise FileNotFoundError(f"Benchmark file not found at {BENCHMARK_FILE}")
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


BENCHMARK_PROMPTS = load_benchmark_prompts()

