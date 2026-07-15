"""NewsFlow — Phase 2: Processors (filter.py + deduplicator.py combined)"""
from __future__ import annotations

from newsflow.models.content import ContentItem


class Deduplicator:
    """URL-based deduplication."""

    def dedup(self, items: list[ContentItem]) -> list[ContentItem]:
        seen: set[str] = set()
        result: list[ContentItem] = []
        for item in items:
            key = item.url.rstrip("/").lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result


class ScoreFilter:
    """Filter items by ai_score threshold."""

    def __init__(self, threshold: float = 7.0, max_items: int = 20) -> None:
        self.threshold = threshold
        self.max_items = max_items

    def filter(self, items: list[ContentItem]) -> list[ContentItem]:
        scored = [i for i in items if i.ai_score is not None]
        unscored = [i for i in items if i.ai_score is None]

        # sort scored items descending
        scored.sort(key=lambda x: x.ai_score or 0, reverse=True)

        # keep items above threshold, then fill with unscored if needed
        above = [i for i in scored if (i.ai_score or 0) >= self.threshold]
        result = (above + unscored)[: self.max_items]
        return result
