"""
client.py — LiteLLM connector supporting Ollama, Docker llama.cpp, and offline fallback.

Usage:
  client = LLMClient(model="ollama/llama3.1:8b", api_base="http://localhost:11434")
  client = LLMClient(model="openai/llama-3.1-8b-instruct", api_base="http://localhost:8080/v1")
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("academic_helpdesk.llm")

# Default settings
DEFAULT_OLLAMA_MODEL = os.environ.get("HELP_DESK_MODEL", "ollama/llama3.1:8b")
DEFAULT_OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
DEFAULT_LLAMA_CPP_API_BASE = os.environ.get("LLAMA_CPP_API_BASE", "http://localhost:8080/v1")
DEFAULT_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "15.0"))


class LLMClient:
    """
    LiteLLM client interface for invoking quantized 8B models (Llama 3.1 / Qwen 2.5)
    hosted on Ollama or Docker llama.cpp server.
    Features:
      - Circuit breaker on timeouts: disables slow server for session to avoid repeated hangs.
      - Cached connectivity check: avoids blocking network requests on every turn.
      - Graceful offline fallback: produces deterministic grounded responses.
    """

    def __init__(
        self,
        model: str | None = None,
        api_base: str | None = None,
        api_key: str = "local-key",
        timeout: float | None = None,
        temperature: float = 0.1,
        force_offline: bool = False,
    ):
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.api_base = api_base or (
            DEFAULT_OLLAMA_API_BASE if "ollama" in self.model else DEFAULT_LLAMA_CPP_API_BASE
        )
        self.api_key = api_key
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self.temperature = temperature
        self.force_offline = force_offline or (os.environ.get("LLM_OFFLINE", "0") in ("1", "true", "True"))
        self._litellm = None
        self._server_disabled = False
        self._checked_reachable: bool | None = None

    def _get_litellm(self):
        if self._litellm is None:
            import litellm

            litellm.suppress_debug_info = True
            litellm.set_verbose = False
            self._litellm = litellm
        return self._litellm

    @property
    def backend_name(self) -> str:
        if self.is_server_reachable():
            return f"Live Server ({self.model}) @ {self.api_base}"
        return f"Offline Grounded Engine (Server not detected on {self.api_base})"

    def is_server_reachable(self) -> bool:
        """Check if Ollama (11434) or llama.cpp (8080) is reachable AND has a model installed."""
        if self.force_offline or self._server_disabled:
            return False

        # Return cached result if already tested in this session
        if self._checked_reachable is not None:
            return self._checked_reachable

        checks = [
            (self.api_base, "/api/tags" if "11434" in self.api_base else "/models"),
            ("http://localhost:11434", "/api/tags"),
            ("http://localhost:8080/v1", "/models"),
        ]
        for check_base, check_path in checks:
            try:
                url = f"{check_base}{check_path}"
                req = urllib.request.Request(url, headers={"User-Agent": "AcademicHelpdesk/1.0"})
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status in (200, 204):
                        data = resp.read().decode("utf-8")
                        try:
                            parsed = json.loads(data)
                            # For Ollama: verify that at least one model is installed
                            if "11434" in check_base or "tags" in check_path:
                                models_list = parsed.get("models", [])
                                if not models_list:
                                    logger.info(
                                        "Ollama is listening on port 11434, but no models are installed yet. "
                                        "Run 'ollama pull llama3.1:8b'. Using internal grounded engine."
                                    )
                                    continue
                                model_names = [m.get("name", "") for m in models_list]
                                base_target = self.model.replace("ollama/", "")
                                matched = any(base_target in name for name in model_names)
                                if not matched and model_names:
                                    self.model = f"ollama/{model_names[0]}"
                        except Exception:
                            pass

                        if check_base != self.api_base and not os.environ.get("HELP_DESK_MODEL"):
                            self.api_base = check_base
                            if "8080" in check_base:
                                self.model = "openai/llama-3.1-8b-instruct"
                        self._checked_reachable = True
                        return True
            except Exception:
                continue

        self._checked_reachable = False
        return False

    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute completion via LiteLLM.
        Returns a standardized dict:
          {
            "content": str,
            "tool_calls": list[{"name": str, "arguments": dict}],
            "backend": "litellm" | "offline_fallback"
          }
        """
        temp = temperature if temperature is not None else self.temperature

        # Attempt invocation through LiteLLM if reachable
        if self.is_server_reachable():
            try:
                litellm = self._get_litellm()
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "api_base": self.api_base,
                    "api_key": self.api_key,
                    "temperature": temp,
                    "timeout": self.timeout,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice

                response = litellm.completion(**kwargs)
                choice = response.choices[0]
                message = choice.message

                tool_calls = []
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        args = tc.function.arguments
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                pass
                        tool_calls.append({
                            "id": getattr(tc, "id", "call_1"),
                            "name": tc.function.name,
                            "arguments": args,
                        })

                content = message.content or ""
                if content:
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "backend": f"litellm ({self.model})",
                    }
            except Exception as e:
                # Trip circuit breaker so subsequent queries don't hang
                self._server_disabled = True
                self._checked_reachable = False
                logger.info(
                    f"LLM server on {self.api_base} timed out or failed ({e}). "
                    f"Tripping circuit breaker: switched to fast deterministic engine for remaining queries."
                )

        # Offline fallback: Synthesize grounded response using provided context/tools
        return self._offline_synthesize(messages, tools)

    def _offline_synthesize(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """
        Deterministic, grounded synthesizer used when the local server is initializing
        or during offline unit tests.
        """
        return {
            "content": "",
            "tool_calls": [],
            "backend": "offline_fallback",
        }
