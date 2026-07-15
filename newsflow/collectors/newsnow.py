"""NewsFlow — Phase 1: Collectors (newsnow.py)

Fetches Chinese trending topics via newsnow API (TrendRadar approach).
Requires a running newsnow instance (self-hosted or public).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from newsflow.collectors.base import BaseCollector
from newsflow.models.content import ContentItem, SourceType

# Default to the public instance — override with NEWSNOW_BASE_URL
DEFAULT_BASE = os.getenv("NEWSNOW_BASE_URL", "https://newsnow.busiyi.world")

# Map newsnow source IDs to SourceType
NEWSNOW_SOURCE_MAP: dict[str, SourceType] = {
    "weibo": SourceType.WEIBO,
    "zhihu": SourceType.ZHIHU,
    "bilibili": SourceType.BILIBILI,
    "toutiao": SourceType.TOUTIAO,
    "baidu": SourceType.BAIDU,
    "douyin": SourceType.DOUYIN,
}


class NewsnowCollector(BaseCollector):
    source_type = SourceType.NEWSNOW

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.base_url = self.config.get("base_url", DEFAULT_BASE).rstrip("/")
        # which platforms to fetch; default: weibo, zhihu, bilibili, toutiao
        self.sources: list[str] = self.config.get(
            "sources", ["weibo", "zhihu", "bilibili", "toutiao"]
        )

    async def collect(self, *, hours: int = 24, limit: int = 50) -> list[ContentItem]:
        items: list[ContentItem] = []

        async with self.make_client() as client:
            for source in self.sources:
                try:
                    resp = await client.get(
                        f"{self.base_url}/api/s/{source}",
                        params={"latest": "true"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning(
                        "newsnow fetch failed for %s: %s", source, exc
                    )
                    continue

                source_type = NEWSNOW_SOURCE_MAP.get(source, SourceType.NEWSNOW)
                entries = data.get("items") or data.get("data") or []
                now = self.now_utc()

                for entry in entries:
                    url = entry.get("url") or entry.get("mobileUrl") or ""
                    if not url:
                        continue
                    items.append(
                        ContentItem(
                            id=f"newsnow:{source}:{entry.get('id', url[-20:])}",
                            source_type=source_type,
                            title=entry.get("title") or entry.get("name", ""),
                            url=url,
                            content=entry.get("desc") or entry.get("excerpt"),
                            published_at=now,
                            fetched_at=now,
                            metadata={
                                "platform": source,
                                "hot": entry.get("hot") or entry.get("views", 0),
                                "extra": entry.get("extra", {}),
                            },
                        )
                    )

                if len(items) >= limit:
                    break

        return items[:limit]
