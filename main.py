#!/usr/bin/env python3
"""
main.py — Main Entry Point for the IIT Jodhpur Academic Helpdesk System.

Usage:
  .venv/bin/python main.py             # Run the 25-prompt benchmark evaluation
  .venv/bin/python main.py --chat      # Launch the interactive terminal chatbot
  .venv/bin/python main.py --eval      # Explicitly run the evaluation suite
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IIT Jodhpur Multi-Agent Academic Helpdesk System"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Launch the interactive terminal chatbot (single-turn Q&A)",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run the automated 25-question benchmark evaluation suite",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run evaluation against live Ollama/llama.cpp model instead of fast offline engine",
    )

    args = parser.parse_args()

    if args.chat:
        from chatbot import main as chat_main
        chat_main()
    else:
        # Default behavior: run benchmark evaluation and save result.txt
        from src.evaluation.evaluator import run_evaluation
        summary = run_evaluation(live_llm=args.live)
        if summary["routing_pct"] < 90 or summary["accuracy_pct"] < 90:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
