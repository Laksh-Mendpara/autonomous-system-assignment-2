"""
base_agent.py — Base class for all specialized academic agents.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from src.llm.client import LLMClient
from src.tools.definitions import TOOL_MAP, TOOL_SCHEMAS, execute_tool

logger = logging.getLogger("academic_helpdesk.agents")


class BaseAgent(ABC):
    """
    Abstract base class providing LLM invocation, tool execution,
    and grounded generation with citations.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm_client: LLMClient | None = None,
        allowed_tools: list[str] | None = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm_client or LLMClient()
        self.allowed_tools = allowed_tools or list(TOOL_MAP.keys())

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        """Filter global tool schemas to only allowed tools for this agent."""
        return [
            s for s in TOOL_SCHEMAS
            if s["function"]["name"] in self.allowed_tools
        ]

    @abstractmethod
    def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent on a user query and return a structured response."""
        pass

    def _execute_tool_loop(
        self,
        query: str,
        initial_tool_call: tuple[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an agent turn with tool calling:
        1. Invokes the tool (either pre-determined or suggested by LLM).
        2. Feeds tool result back into context.
        3. Formulates a final grounded answer with citations.
        """
        trace = []
        tool_results = []

        # If a specific tool is directly targeted by the agent:
        if initial_tool_call:
            tool_name, tool_args = initial_tool_call
            trace.append({"step": "tool_call", "tool": tool_name, "args": tool_args})
            result = execute_tool(tool_name, tool_args)
            trace.append({"step": "tool_result", "tool": tool_name, "result": result})
            tool_results.append((tool_name, result))

        # Build prompt messages for synthesis
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]

        # Append tool outputs to context
        if tool_results:
            formatted_context = self._format_tool_results_for_prompt(tool_results)
            messages.append({
                "role": "system",
                "content": f"Retrieved Context and Tool Evidence:\n{formatted_context}",
            })

        # Ask LLM (or fallback) to synthesize final grounded response
        response = self.llm.generate(
            messages=messages,
            tools=self.tool_schemas if not tool_results else None,
            temperature=0.1,
        )

        final_content = response.get("content", "")
        # If the LLM returned generic fallback text, synthesize directly from tool results
        if not final_content or response.get("backend") == "offline_fallback":
            final_content = self.synthesize_from_tool_results(query, tool_results)

        # Extract citations
        citations = self._extract_citations(tool_results)

        return {
            "agent": self.name,
            "query": query,
            "answer": final_content,
            "citations": citations,
            "trace": trace,
            "backend": response.get("backend", "local"),
        }

    def _format_tool_results_for_prompt(self, tool_results: list[tuple[str, Any]]) -> str:
        parts = []
        for name, res in tool_results:
            parts.append(f"--- Tool '{name}' Result ---\n{json.dumps(res, indent=2, default=str)}")
        return "\n\n".join(parts)

    def _extract_citations(self, tool_results: list[tuple[str, Any]]) -> list[str]:
        citations = []
        for _, res in tool_results:
            if isinstance(res, dict):
                if "citation" in res and res["citation"] not in citations:
                    citations.append(str(res["citation"]))
                if "chunks" in res:
                    for ch in res["chunks"]:
                        if "citation" in ch and ch["citation"] not in citations:
                            citations.append(ch["citation"])
                if "results" in res:
                    for item in res["results"]:
                        if isinstance(item, dict) and "citation" in item and item["citation"] not in citations:
                            citations.append(item["citation"])
        return citations

    @abstractmethod
    def synthesize_from_tool_results(self, query: str, tool_results: list[tuple[str, Any]]) -> str:
        """Grounded synthesis formatting specific to each agent."""
        pass

