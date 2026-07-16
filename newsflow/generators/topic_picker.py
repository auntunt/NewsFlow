"""
选题器：从 filtered items 中挑出最适合深度解读的 1 条。

选题策略（按优先级）：
1. AI/LLM/Agent 相关度最高
2. 有技术深度（不只是新闻）
3. 国内开发者有感知的话题
4. 评分最高兜底
"""
from __future__ import annotations

import re
from typing import Any

# 高价值关键词：命中越多越好
HIGH_VALUE_KEYWORDS = [
    "agent", "llm", "claude", "gpt", "gemini", "anthropic", "openai",
    "mcp", "rag", "fine-tun", "reasoning", "multimodal", "workflow",
    "open source", "open-source", "self-host", "local", "inference",
    "benchmark", "evaluation", "prompt", "context window",
    "ai agent", "coding agent", "autonomous",
]

# 降权关键词：偏新闻/商业，技术深度低
LOW_VALUE_KEYWORDS = [
    "stock", "ipo", "lawsuit", "hire", "fired", "partnership",
    "acquisition", "funding", "valuation", "deal",
]


def _score_topic_value(item: dict) -> float:
    """综合评分：原始 AI 评分 × 关键词加权"""
    title = (item.get("title") or "").lower()
    content = (item.get("content") or item.get("description") or "").lower()
    text = title + " " + content

    base = float(item.get("score") or item.get("ai_score") or 7.0)

    # 高价值关键词加权
    hit_high = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in text)
    hit_low = sum(1 for kw in LOW_VALUE_KEYWORDS if kw in text)

    # 标题命中加倍
    title_hit = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in title)

    bonus = hit_high * 0.3 + title_hit * 0.5 - hit_low * 0.8
    return base + bonus


def pick_topic(items: list[dict]) -> dict:
    """选出最有价值的话题，返回标准化的 topic dict"""
    if not items:
        raise ValueError("items 为空，无法选题")

    scored = [(item, _score_topic_value(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)

    best = scored[0][0]

    # 标准化字段
    return {
        "title": best.get("title") or "",
        "url": best.get("url") or "",
        "source": best.get("source_type") or best.get("source") or "unknown",
        "score": best.get("score") or best.get("ai_score") or 0,
        "content": best.get("content") or best.get("description") or "",
        "metadata": best.get("metadata") or {},
        # 保留原始数据，供写稿参考
        "_raw": best,
    }
