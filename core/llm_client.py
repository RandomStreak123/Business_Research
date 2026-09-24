"""
Thin wrapper around Groq's OpenAI-compatible chat completions API with:
  - strict low temperature for anti-hallucination fidelity
  - dynamic rate-limit pause parsing (handles 429 "try again in Xs" gracefully)
  - retries on the primary model
  - automatic fallback to alternate models if the primary keeps failing
  - every attempt/failure written to the shared activity log
"""

import os
import re
import time

from openai import APIError, APIStatusError, APITimeoutError, OpenAI

from config import (
    FALLBACK_MODELS,
    GROQ_API_KEY_ENV_VAR,
    GROQ_BASE_URL,
    LLM_TEMPERATURE,
    MAX_RETRIES_PER_MODEL,
    MAX_TOKENS,
    PRIMARY_MODEL,
    RETRY_BACKOFF_SECONDS,
)


class AllModelsFailedError(RuntimeError):
    """Raised when the primary model and every fallback model fail."""


class LLMClient:
    def __init__(self, task_manager, primary_model: str = PRIMARY_MODEL,
                 fallback_models: list[str] | None = None):
        api_key = os.environ.get(GROQ_API_KEY_ENV_VAR)
        if not api_key:
            raise RuntimeError(
                f"{GROQ_API_KEY_ENV_VAR} is not set. Get a free key at "
                f"https://console.groq.com/keys and run:\n"
                f"  export {GROQ_API_KEY_ENV_VAR}=your_key_here"
            )
        self.client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        self.tm = task_manager
        self.model_chain = [primary_model] + (
            fallback_models if fallback_models is not None else list(FALLBACK_MODELS)
        )

    def complete(self, system: str, prompt: str, agent_name: str,
                 max_tokens: int = MAX_TOKENS,
                 temperature: float = LLM_TEMPERATURE) -> str:
        last_error: Exception | None = None

        for model_index, model in enumerate(self.model_chain):
            is_fallback = model_index > 0
            for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                try:
                    if is_fallback:
                        self.tm.log(
                            "model_fallback", agent_name,
                            f"trying fallback model '{model}' (previous error: {last_error})",
                        )
                    response = self.client.chat.completions.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    text = response.choices[0].message.content or ""
                    if not text.strip():
                        raise ValueError("empty response from model")

                    self.tm.log(
                        "model_call_ok", agent_name,
                        f"model={model} attempt={attempt} chars={len(text)} temp={temperature}",
                    )
                    return text

                except (APIError, APIStatusError, APITimeoutError, ValueError) as exc:
                    last_error = exc
                    error_msg = str(exc)
                    self.tm.log(
                        "model_call_failed", agent_name,
                        f"model={model} attempt={attempt}/{MAX_RETRIES_PER_MODEL} error={error_msg[:120]}",
                    )
                    if attempt < MAX_RETRIES_PER_MODEL:
                        # Extract exact wait time requested by provider if available
                        match = re.search(r"try again in ([\d\.]+)s", error_msg)
                        if match:
                            delay = float(match.group(1)) + 1.0
                        else:
                            delay = RETRY_BACKOFF_SECONDS * attempt
                        time.sleep(delay)

        raise AllModelsFailedError(
            f"All models exhausted for agent '{agent_name}'. Last error: {last_error}"
        )