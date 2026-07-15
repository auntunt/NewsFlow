"""NewsFlow — Phase 2: Processors (scorer.py)

Batch-scores ContentItems using the AI client.
Sends items in batches to avoid exceeding context limits.
"""
from __future__ import annotations

import json
import logging

from newsflow.ai.client import AIClient
from newsflow.ai.prompts import SCORE_SYSTEM, SCORE_USER_TMPL
from newsflow.models.content import ContentItem

logger = logging.getLogger(__name__)

BATCH_SIZE = 20  # items per LLM call


class Scorer:
    def __init__(self, ai: AIClient, batch_size: int = BATCH_SIZE) -> None:
        self.ai = ai
        self.batch_size = batch_size

    async def score(self, items: list[ContentItem]) -> list[ContentItem]:
        """Return items with ai_score, ai_reason, ai_tags filled in."""
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            await self._score_batch(batch)
        return items

    async def _score_batch(self, batch: list[ContentItem]) -> None:
        payload = [
            {
                "id": item.id,
                "title": item.title,
                "content": (item.content or "")[:300],
                "url": item.url,
            }
            for item in batch
        ]
        user_msg = SCORE_USER_TMPL.format(
            n=len(batch), items_json=json.dumps(payload, ensure_ascii=False)
        )
        try:
            result = await self.ai.complete_json(
                messages=[
                    {"role": "system", "content": SCORE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                model=self.ai.score_model,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.warning("Scoring batch failed: %s — skipping", exc)
            return

        scores: dict[str, dict] = {
            r["id"]: r for r in result.get("results", [])
        }

        for item in batch:
            if item.id in scores:
                r = scores[item.id]
                item.ai_score = float(r.get("score", 0))
                item.ai_reason = r.get("reason", "")
                item.ai_tags = r.get("tags", [])
