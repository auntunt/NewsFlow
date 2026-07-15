"""Tests for collectors and models."""
import asyncio
from datetime import datetime, timezone

import pytest

from newsflow.models.content import ContentItem, SourceType
from newsflow.models.output import ArticleOutput
from newsflow.processors.filter import Deduplicator, ScoreFilter


# ── Model tests ───────────────────────────────────────────────────────────────

def test_content_item_creation():
    item = ContentItem(
        id="hackernews:story:123",
        source_type=SourceType.HACKERNEWS,
        title="Test Article",
        url="https://example.com",
        published_at=datetime.now(tz=timezone.utc),
    )
    assert item.id == "hackernews:story:123"
    assert item.ai_score is None
    assert item.ai_tags == []


def test_content_item_serialization():
    item = ContentItem(
        id="rss:test:abc",
        source_type=SourceType.RSS,
        title="RSS Item",
        url="https://example.com/rss",
        published_at=datetime.now(tz=timezone.utc),
        ai_score=8.5,
        ai_tags=["AI", "Python"],
    )
    data = item.model_dump(mode="json")
    restored = ContentItem(**data)
    assert restored.ai_score == 8.5
    assert restored.ai_tags == ["AI", "Python"]


# ── Processor tests ───────────────────────────────────────────────────────────

def _make_item(id_: str, url: str, score: float | None = None) -> ContentItem:
    return ContentItem(
        id=id_,
        source_type=SourceType.HACKERNEWS,
        title=f"Title {id_}",
        url=url,
        published_at=datetime.now(tz=timezone.utc),
        ai_score=score,
    )


def test_deduplicator_removes_duplicates():
    items = [
        _make_item("a", "https://example.com/1"),
        _make_item("b", "https://example.com/1"),  # duplicate URL
        _make_item("c", "https://example.com/2"),
    ]
    result = Deduplicator().dedup(items)
    assert len(result) == 2
    urls = {i.url for i in result}
    assert "https://example.com/1" in urls
    assert "https://example.com/2" in urls


def test_score_filter_threshold():
    items = [
        _make_item("a", "https://a.com", score=9.0),
        _make_item("b", "https://b.com", score=5.0),
        _make_item("c", "https://c.com", score=7.5),
        _make_item("d", "https://d.com", score=3.0),
    ]
    result = ScoreFilter(threshold=7.0, max_items=10).filter(items)
    scores = [i.ai_score for i in result]
    assert 9.0 in scores
    assert 7.5 in scores
    assert 5.0 not in scores
    assert 3.0 not in scores


def test_score_filter_max_items():
    items = [_make_item(str(i), f"https://example.com/{i}", score=float(i)) for i in range(20)]
    result = ScoreFilter(threshold=0.0, max_items=5).filter(items)
    assert len(result) == 5


# ── Registry tests ────────────────────────────────────────────────────────────

def test_get_collector_hackernews():
    from newsflow.collectors.registry import get_collector
    collector = get_collector("hackernews")
    assert collector is not None


def test_get_collector_unknown():
    from newsflow.collectors.registry import get_collector
    with pytest.raises(ValueError, match="Unknown collector"):
        get_collector("nonexistent_source")


def test_list_collectors():
    from newsflow.collectors.registry import list_collectors
    names = list_collectors()
    assert "hackernews" in names
    assert "rss" in names
    assert "github_trending" in names
    assert "newsnow" in names
