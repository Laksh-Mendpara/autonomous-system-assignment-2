#!/usr/bin/env python3
"""
chatbot.py — Simple Terminal Chatbot for IIT Jodhpur Academic Helpdesk.

Single-turn question & answer (stateless / no conversation memory):
Each query is routed by the Helpdesk Orchestrator to the appropriate specialist agent
or refused with an audit log entry if out of scope.

Usage:
  .venv/bin/python chatbot.py
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure offline huggingface cache usage
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.agents.orchestrator import AcademicHelpdeskOrchestrator
from src.llm.client import LLMClient

console = Console()


def print_banner(client: LLMClient) -> None:
    is_online = client.is_server_reachable()
    if is_online:
        backend_status = f"[bold green]● LLM Backend: Connected to Ollama ({client.model}) @ {client.api_base}[/bold green]"
    else:
        backend_status = (
            f"[bold yellow]○ LLM Backend: Offline Grounded Engine (Ollama not detected on {client.api_base})[/bold yellow]\n"
            f"[dim]  (To connect a live 8B model: run 'ollama run llama3.1:8b' in a separate terminal)[/dim]"
        )

    banner = (
        "[bold cyan]============================================================[/bold cyan]\n"
        "[bold white]       IIT Jodhpur — Academic Helpdesk Terminal Chatbot     [/bold white]\n"
        "[dim]   Multi-Agent Architecture | ChromaDB RAG | LiteLLM Connector [/dim]\n"
        "[bold cyan]============================================================[/bold cyan]\n\n"
        f"{backend_status}\n\n"
        "[dim]Ask any academic question, course slot, elective count, or email draft request.[/dim]\n"
        "[dim](Stateless: Single Turn Q&A. Type [bold red]'exit'[/bold red] or [bold red]'quit'[/bold red] to end the session)[/dim]"
    )
    console.print(Panel(banner, border_style="cyan"))


def main() -> None:
    # Initialize the Orchestrator with LiteLLM client
    client = LLMClient()
    print_banner(client)
    orchestrator = AcademicHelpdeskOrchestrator(llm_client=client)

    console.print("\n[bold green]Ready! Enter your academic question below:[/bold green]\n")

    while True:
        try:
            user_input = input("Student Query > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended. Goodbye![/yellow]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("\n[yellow]Thank you for using the Academic Helpdesk. Goodbye![/yellow]")
            break

        console.print("[dim]Processing query through multi-agent pipeline...[/dim]")

        # Process the single-turn query
        res = orchestrator.process_query(user_input)

        is_oos = res.get("is_out_of_scope", False)
        agent_name = res.get("agent", "Orchestrator Guard")
        decision = res.get("orchestrator_decision", "PROCESSED")
        answer = res.get("answer", "")
        citations = res.get("citations", [])
        backend = res.get("backend", client.backend_name)

        # Display decision and result
        if is_oos:
            console.print(Panel(
                Markdown(answer),
                title="🛑 Refusal — Out of Academic Scope (Logged to Audit File)",
                border_style="red",
            ))
            console.print(f"[dim]Decision: {decision} | Engine: {backend}[/dim]")
        else:
            console.print(f"[bold yellow]Agent Assigned:[/bold yellow] [bold green]{agent_name}[/bold green] ([dim]{decision}[/dim]) | [dim]Backend: {backend}[/dim]")
            console.print(Panel(
                Markdown(answer),
                title=f"🎓 Helpdesk Response ({agent_name})",
                border_style="green",
            ))

            if citations and citations != ["None"]:
                console.print("[bold blue]📚 Grounded Sources & Citations:[/bold blue]")
                for c in citations:
                    console.print(f"  • [cyan]{c}[/cyan]")

        console.print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
