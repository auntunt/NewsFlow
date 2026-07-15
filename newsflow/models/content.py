"""NewsFlow — Phase 1: Data Models (content.py)

Based on Horizon's ContentItem, extended with Chinese source types.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceType(str, Enum):
    # English sources (from Horizon)
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    RSS = "rss"
    GITHUB = "github"
    GITHUB_TRENDING = "github_trending"
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    GDELT = "gdelt"
    GOOGLE_NEWS = "google_news"
    # Full-text fetchers (from InfoStream)
    JINA = "jina"
    FIRECRAWL = "firecrawl"
    # Chinese sources (from TrendRadar)
    NEWSNOW = "newsnow"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    TOUTIAO = "toutiao"
    BAIDU = "baidu"
    DOUYIN = "douyin"


class ContentItem(BaseModel):
    """Normalised content item — the lingua franca across the whole pipeline."""

    id: str = Field(
        description="Globally unique ID: {source_type}:{subtype}:{native_id}"
    )
    source_type: SourceType
    title: str
    url: str  # HttpUrl is strict; keep as str for flexibility
    content: str | None = None
    author: str | None = None
    published_at: datetime
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # AI-enriched fields (filled by processors)
    ai_score: float | None = None        # 0–10
    ai_reason: str | None = None
    ai_summary: str | None = None
    ai_tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
