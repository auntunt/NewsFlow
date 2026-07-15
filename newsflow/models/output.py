"""NewsFlow — Phase 1: Data Models (output.py)

ArticleOutput: the result of the generators layer (AI-rewritten content).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlatformVersions(BaseModel):
    wechat_html: str | None = None
    xiaohongshu_text: str | None = None
    feishu_markdown: str | None = None
    plain_markdown: str | None = None


class RunStats(BaseModel):
    collected: int = 0
    filtered: int = 0
    word_count: int = 0
    token_used: int = 0


class ArticleOutput(BaseModel):
    """A fully generated, platform-formatted article ready for publishing."""

    id: str
    workflow: str
    run_id: str
    title: str
    content_markdown: str
    content_html: str = ""
    platform_versions: PlatformVersions = Field(default_factory=PlatformVersions)
    source_items: list[str] = Field(default_factory=list)   # ContentItem ids
    stats: RunStats = Field(default_factory=RunStats)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    extra: dict[str, Any] = Field(default_factory=dict)
