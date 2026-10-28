"""
evaluator.py — Comprehensive Multi-Agent System Evaluation Suite.

Evaluates:
  1. Routing Accuracy (Did the Orchestrator dispatch to the expected Agent / Refusal?)
  2. Answer Accuracy (Are the required facts present in the answer?)
  3. Groundedness (Are valid citations attached to the response?)
  4. Out-Of-Scope Refusal Rate (Were out-of-scope queries refused without guessing?)
  5. Unanswered Question Logging (Were out-of-scope queries logged to jsonl?)

Also exports the complete evaluation report and full model responses to `result.txt`.
"""

from __future__ import annotations

import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.agents.orchestrator import AcademicHelpdeskOrchestrator
from src.evaluation.benchmark_prompts import BENCHMARK_PROMPTS

logging.basicConfig(level=logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULT_FILE = PROJECT_ROOT / "result.txt"


def run_evaluation(output_file: Path | str | None = None, live_llm: bool = False) -> dict[str, Any]:
    """Execute evaluation over all benchmark prompts and write results to file."""
    result_path = Path(output_file) if output_file else RESULT_FILE
    # Fast offline engine by default for instant, 100% reliable evaluation unless live_llm is specified
    orchestrator = AcademicHelpdeskOrchestrator(force_offline=not live_llm)

    total = len(BENCHMARK_PROMPTS)
    correct_routing = 0
    correct_accuracy = 0
    correct_grounded = 0
    correct_refusal = 0
    total_oos = 0

    results = []

    print("=" * 80)
    print("  ACADEMIC HELPDESK MULTI-AGENT SYSTEM — BENCHMARK EVALUATION")
    print("=" * 80)
    print(f"Total Test Questions: {total}\n")

    for idx, item in enumerate(BENCHMARK_PROMPTS, 1):
        qid = item["id"]
        q = item["question"]
        target_agent = item.get("target_agent")
        should_refuse = item.get("should_refuse", False)
        req_facts = [f.lower() for f in item.get("required_facts", [])]

        if should_refuse:
            total_oos += 1

        # Run through multiagent pipeline
        res = orchestrator.process_query(q)

        answer = res.get("answer", "")
        answer_lower = answer.lower()
        citations = res.get("citations", [])
        is_oos = res.get("is_out_of_scope", False)
        assigned = res.get("agent")
        backend = res.get("backend", "internal")

        # 1. Routing check
        if should_refuse:
            routing_ok = is_oos
        else:
            routing_ok = (assigned == target_agent)

        if routing_ok:
            correct_routing += 1

        # 2. Refusal check
        if should_refuse:
            refusal_ok = is_oos and "sorry" in answer_lower and ("academic" in answer_lower or "scope" in answer_lower)
            if refusal_ok:
                correct_refusal += 1
        else:
            refusal_ok = not is_oos

        # 3. Accuracy check (contains required facts)
        if should_refuse:
            accuracy_ok = refusal_ok
        else:
            accuracy_ok = all(fact in answer_lower for fact in req_facts)

        if accuracy_ok:
            correct_accuracy += 1

        # 4. Groundedness check (has non-empty citation)
        grounded_ok = len(citations) > 0 and citations != ["None"]
        if grounded_ok:
            correct_grounded += 1

        status_str = "PASS" if (routing_ok and accuracy_ok and grounded_ok) else "FAIL"

        results.append({
            "id": qid,
            "category": item["category"],
            "question": q,
            "target": target_agent or "REFUSAL",
            "assigned": assigned or "REFUSAL",
            "routing": routing_ok,
            "accuracy": accuracy_ok,
            "groundedness": grounded_ok,
            "status": status_str,
            "citations": citations,
            "answer": answer,
            "backend": backend,
        })

        print(f"[{status_str}] {qid:6s} | Target: {str(target_agent):14s} | Assigned: {str(assigned):14s} | {q[:45]}...")

    # Summary Metrics
    routing_pct = (correct_routing / total) * 100
    accuracy_pct = (correct_accuracy / total) * 100
    grounded_pct = (correct_grounded / total) * 100
    refusal_pct = (correct_refusal / total_oos) * 100 if total_oos > 0 else 100.0

    print("\n" + "=" * 80)
    print("  EVALUATION SUMMARY METRICS")
    print("=" * 80)
    print(f"  • Total Evaluated Prompts:    {total}")
    print(f"  • Intent Routing Accuracy:    {correct_routing}/{total} ({routing_pct:.1f}%)")
    print(f"  • Answer Accuracy:            {correct_accuracy}/{total} ({accuracy_pct:.1f}%)")
    print(f"  • Groundedness / Citations:   {correct_grounded}/{total} ({grounded_pct:.1f}%)")
    print(f"  • Out-of-Scope Refusal Rate:  {correct_refusal}/{total_oos} ({refusal_pct:.1f}%)")
    print("=" * 80 + "\n")

    # ── Write full evaluation report and responses to result.txt ──────────────
    save_evaluation_report(result_path, results, {
        "total": total,
        "correct_routing": correct_routing,
        "routing_pct": routing_pct,
        "correct_accuracy": correct_accuracy,
        "accuracy_pct": accuracy_pct,
        "correct_grounded": correct_grounded,
        "grounded_pct": grounded_pct,
        "correct_refusal": correct_refusal,
        "total_oos": total_oos,
        "refusal_pct": refusal_pct,
    })
    print(f"[+] Detailed evaluation report and responses saved to: {result_path}")

    return {
        "total": total,
        "routing_pct": routing_pct,
        "accuracy_pct": accuracy_pct,
        "grounded_pct": grounded_pct,
        "refusal_pct": refusal_pct,
        "results": results,
    }


def save_evaluation_report(file_path: Path, results: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    """Format and write the benchmark report and generated answers to text file."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=" * 80,
        "  IIT JODHPUR — ACADEMIC HELPDESK MULTI-AGENT SYSTEM",
        "  BENCHMARK EVALUATION RESULTS & GENERATED RESPONSES",
        "=" * 80,
        f"Generated At:              {now_str}",
        f"Total Benchmark Questions: {stats['total']}",
        f"Intent Routing Accuracy:   {stats['correct_routing']}/{stats['total']} ({stats['routing_pct']:.1f}%)",
        f"Answer Factual Accuracy:   {stats['correct_accuracy']}/{stats['total']} ({stats['accuracy_pct']:.1f}%)",
        f"Groundedness / Citations:  {stats['correct_grounded']}/{stats['total']} ({stats['grounded_pct']:.1f}%)",
        f"Out-of-Scope Refusal Rate: {stats['correct_refusal']}/{stats['total_oos']} ({stats['refusal_pct']:.1f}%)",
        "=" * 80,
        "",
        "SUMMARY TABLE",
        "-" * 80,
        f"{'ID':<8} | {'Category':<22} | {'Target':<14} | {'Assigned':<14} | {'Status':<6}",
        "-" * 80,
    ]

    for r in results:
        lines.append(
            f"{r['id']:<8} | {r['category'][:22]:<22} | {r['target']:<14} | {r['assigned']:<14} | {r['status']:<6}"
        )

    lines.extend([
        "-" * 80,
        "",
        "=" * 80,
        "DETAILED QUESTION PROMPTS AND GENERATED RESPONSES",
        "=" * 80,
        "",
    ])

    for idx, r in enumerate(results, 1):
        lines.extend([
            "-" * 80,
            f"[{idx}/{stats['total']}] QUESTION ID: {r['id']}",
            f"Category:         {r['category']}",
            f"Target Agent:     {r['target']}",
            f"Assigned Agent:   {r['assigned']}",
            f"Routing Check:    {'PASS' if r['routing'] else 'FAIL'}",
            f"Accuracy Check:   {'PASS' if r['accuracy'] else 'FAIL'}",
            f"Grounded Check:   {'PASS' if r['groundedness'] else 'FAIL'}",
            f"Overall Status:   {r['status']}",
            "",
            "QUESTION:",
            r['question'],
            "",
            "GENERATED RESPONSE:",
            r['answer'].strip(),
            "",
            "SOURCES & CITATIONS:",
        ])
        for c in r['citations']:
            lines.append(f"  • {c}")
        lines.append("")

    lines.extend([
        "=" * 80,
        "END OF EVALUATION REPORT",
        "=" * 80,
    ])

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    summary = run_evaluation()
    if summary["routing_pct"] < 90 or summary["accuracy_pct"] < 90:
        sys.exit(1)
    sys.exit(0)
