"""NewsFlow — Phase 1: Collectors (rss.py)

Generic RSS / Atom feed collector using feedparser.
"""
from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from newsflow.collectors.base import BaseCollector
from newsflow.models.content import ContentItem, SourceType


class RSSCollector(BaseCollector):
    source_type = SourceType.RSS

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        # config["feeds"] = list of {url, name} or plain URL strings
        feeds = self.config.get("feeds", [])
        self.feeds: list[dict] = [
            (f if isinstance(f, dict) else {"url": f, "name": f})
            for f in feeds
        ]

    async def collect(self, *, hours: int = 24, limit: int = 50) -> list[ContentItem]:
        items: list[ContentItem] = []
        cutoff = self.now_utc().timestamp() - hours * 3600

        for feed_cfg in self.feeds:
            url = feed_cfg["url"]
            name = feed_cfg.get("name", url)
            parsed = feedparser.parse(url)

            for entry in parsed.entries:
                ts = self._entry_timestamp(entry)
                if ts < cutoff:
                    continue

                entry_id = entry.get("id") or entry.get("link", "")
                content = (
                    entry.get("summary")
                    or entry.get("description")
                    or entry.get("content", [{}])[0].get("value", "")
                )

                items.append(
                    ContentItem(
                        id=f"rss:{_slug(name)}:{_short_hash(entry_id)}",
                        source_type=SourceType.RSS,
                        title=entry.get("title", ""),
                        url=entry.get("link", url),
                        content=content,
                        author=entry.get("author"),
                        published_at=datetime.fromtimestamp(ts, tz=timezone.utc),
                        fetched_at=self.now_utc(),
                        metadata={"feed_name": name, "feed_url": url},
                    )
                )
                if len(items) >= limit:
                    return items

        return items

    @staticmethod
    def _entry_timestamp(entry) -> float:
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            val = entry.get(key)
            if val:
                import calendar
                return float(calendar.timegm(val))
        return 0.0


def _slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:32]


def _short_hash(s: str) -> str:
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:10]
