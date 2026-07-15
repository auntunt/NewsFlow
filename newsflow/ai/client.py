"""NewsFlow — Phase 2: AI Client (client.py)

Thin wrapper around litellm. Handles:
- Model selection (score_model vs generate_model)
- Retry with tenacity
- Token usage tracking
"""
from __future__ import annotations

import json
import os
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

# litellm picks up API keys from env automatically
import litellm

litellm.drop_params = True  # ignore unsupported params per model


class AIClient:
    def __init__(
        self,
        model: str | None = None,
        score_model: str | None = None,
        generate_model: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.model = model or os.getenv("NEWSFLOW_MODEL", "deepseek/deepseek-chat")
        self.score_model = score_model or os.getenv("NEWSFLOW_SCORE_MODEL", self.model)
        self.generate_model = generate_model or os.getenv(
            "NEWSFLOW_GENERATE_MODEL", self.model
        )
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.total_tokens: int = 0

    # ── public interface ──────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_json: bool = False,
    ) -> str:
        """Async completion. Returns the content string."""
        _model = model or self.model
        kwargs: dict[str, Any] = dict(
            model=_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._call_with_retry(**kwargs)
        usage = getattr(response, "usage", None)
        if usage:
            self.total_tokens += getattr(usage, "total_tokens", 0)

        return response.choices[0].message.content or ""

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict:
        """Completion that parses and returns JSON."""
        text = await self.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_json=True,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # attempt to extract JSON block
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"AI returned non-JSON: {text[:200]}")

    # ── internal ──────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_with_retry(self, **kwargs):
        return await litellm.acompletion(**kwargs)
