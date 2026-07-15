"""NewsFlow — Phase 1: Collectors (hackernews.py)

Fetches top/best stories from Hacker News Firebase API.
"""
from __future__ import annotations

import asyncio
from datetime import timezone

from newsflow.collectors.base import BaseCollector
from newsflow.models.content import ContentItem, SourceType

HN_API = "https://hacker-news.firebaseio.com/v0"


class HackerNewsCollector(BaseCollector):
    source_type = SourceType.HACKERNEWS

    async def collect(self, *, hours: int = 24, limit: int = 50) -> list[ContentItem]:
        async with self.make_client() as client:
            # fetch top story IDs
            resp = await client.get(f"{HN_API}/topstories.json")
            resp.raise_for_status()
            ids: list[int] = resp.json()[: limit * 2]  # fetch extra, filter below

            # fetch story details concurrently (max 10 at a time)
            semaphore = asyncio.Semaphore(10)
            tasks = [self._fetch_item(client, semaphore, sid) for sid in ids]
            stories = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[ContentItem] = []
        cutoff = self.now_utc().timestamp() - hours * 3600

        for raw in stories:
            if isinstance(raw, BaseException) or raw is None:
                continue
            story: dict = raw  # type: ignore[assignment]
            if story.get("type") != "story":
                continue
            if not story.get("url") and not story.get("text"):
                continue
            ts = story.get("time", 0)
            if ts < cutoff:
                continue

            from datetime import datetime

            pub = datetime.fromtimestamp(ts, tz=timezone.utc)
            items.append(
                ContentItem(
                    id=f"hackernews:story:{story['id']}",
                    source_type=SourceType.HACKERNEWS,
                    title=story.get("title", ""),
                    url=story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}",
                    content=story.get("text"),
                    author=story.get("by"),
                    published_at=pub,
                    fetched_at=self.now_utc(),
                    metadata={
                        "score": story.get("score", 0),
                        "comments": story.get("descendants", 0),
                        "hn_id": story["id"],
                    },
                )
            )
            if len(items) >= limit:
                break

        return items

    async def _fetch_item(
        self, client, semaphore: asyncio.Semaphore, item_id: int
    ) -> dict | None:
        async with semaphore:
            try:
                resp = await client.get(f"{HN_API}/item/{item_id}.json")
                resp.raise_for_status()
                return resp.json()
            except Exception:
                return None
