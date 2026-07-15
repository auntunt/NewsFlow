"""NewsFlow — Phase 1: Collectors (base.py)

Abstract base class for all collectors.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from newsflow.models.content import ContentItem


class BaseCollector(ABC):
    """Every collector must implement `collect()`."""

    source_type: str  # must match SourceType value

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    async def collect(
        self,
        *,
        hours: int = 24,
        limit: int = 50,
    ) -> list[ContentItem]:
        """Fetch and return normalised ContentItem list."""
        ...

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def make_client(timeout: float = 20.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; NewsFlow/0.1; "
                    "+https://github.com/auntunt/NewsFlow)"
                )
            },
            follow_redirects=True,
        )
