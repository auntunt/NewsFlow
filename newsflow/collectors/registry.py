"""NewsFlow — Phase 1: Collectors (registry.py)

Maps collector type strings to collector classes.
Workflow YAML references these by name.
"""
from __future__ import annotations

from newsflow.collectors.base import BaseCollector
from newsflow.collectors.hackernews import HackerNewsCollector
from newsflow.collectors.rss import RSSCollector
from newsflow.collectors.github_trending import GitHubTrendingCollector
from newsflow.collectors.newsnow import NewsnowCollector

_REGISTRY: dict[str, type[BaseCollector]] = {
    "hackernews": HackerNewsCollector,
    "rss": RSSCollector,
    "github_trending": GitHubTrendingCollector,
    "newsnow": NewsnowCollector,
}


def get_collector(type_name: str, config: dict | None = None) -> BaseCollector:
    cls = _REGISTRY.get(type_name)
    if cls is None:
        raise ValueError(
            f"Unknown collector type: {type_name!r}. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return cls(config=config)


def list_collectors() -> list[str]:
    return sorted(_REGISTRY.keys())
