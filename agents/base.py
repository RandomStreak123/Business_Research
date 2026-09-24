"""
Shared base class for all agents.

Each agent wraps the LLMClient with a fixed name (for logging/fallback
attribution) and a `run()` method subclasses implement.
"""

from typing import Any

from core.llm_client import LLMClient
from core.task_manager import TaskManager


class Agent:
    name: str = "agent"

    def __init__(self, llm: LLMClient, tm: TaskManager):
        self.llm = llm
        self.tm = tm

    def ask(self, system: str, prompt: str, max_tokens: int | None = None,
            temperature: float | None = None) -> str:
        kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        return self.llm.complete(system=system, prompt=prompt, agent_name=self.name, **kwargs)
