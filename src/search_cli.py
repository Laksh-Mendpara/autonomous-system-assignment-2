"""
search_cli.py — Interactive CLI for testing RAG retrieval.

Usage:
    uv run python -m src.search_cli
    uv run python -m src.search_cli --query "attendance requirement for major exam"
    uv run python -m src.search_cli --query "slot for autonomous systems" --category timetable
    uv run python -m src.search_cli --query "CSL7570 instructor email" --top_k 3
"""

from __future__ import annotations

import argparse

from src.indexer import build_index
from src.rag.retriever import Retriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Academic Helpdesk — Semantic Search CLI")
    parser.add_argument("--query", type=str, default=None, help="Query string (interactive if omitted)")
    parser.add_argument("--category", type=str, default=None, help="Filter to specific category")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild before searching")
    args = parser.parse_args()

    # Ensure index is built
    store = build_index(rebuild=args.rebuild)
    retriever = Retriever(store)

    def run_query(query: str) -> None:
        print(f"\n{'─'*60}")
        print(f"  Query: {query}")
        if args.category:
            print(f"  Filter: category={args.category}")
        print(f"{'─'*60}")

        results = retriever.retrieve(
            query=query,
            top_k=args.top_k,
            force_categories=[args.category] if args.category else None,
        )

        if not results:
            print("  No relevant results found above threshold.")
        else:
            for i, r in enumerate(results, 1):
                print(f"\n[{i}] Score: {r.score:.3f} | {r.citation}")
                print(f"    {r.text[:400]}{'…' if len(r.text) > 400 else ''}")

    if args.query:
        run_query(args.query)
    else:
        # Interactive mode
        print("\nAcademic Helpdesk — Semantic Search (type 'quit' to exit)")
        while True:
            try:
                query = input("\n> ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not query or query.lower() in {"quit", "exit", "q"}:
                break
            run_query(query)


if __name__ == "__main__":
    main()

