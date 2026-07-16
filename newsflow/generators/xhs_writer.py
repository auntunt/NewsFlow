"""
小红书笔记生成器

目标：300-400字，同一话题的轻量口语版
风格：像真人在分享发现，不像科普文章

小红书特点：
- 开头要够抓眼球（前两行决定展开率）
- emoji 适量（每段1-2个）
- 话题标签 5-8 个
- 结尾引导互动（"你有没有试过..."）
"""
from __future__ import annotations

import asyncio
import json
import re

from newsflow.ai.client import AIClient

XHS_SYSTEM = """你是一个在小红书分享 AI 工具使用心得的技术博主，
粉丝是对 AI 感兴趣的开发者和产品人。
风格：像朋友分享发现，口语化，有实用信息，不卖课不贩焦虑。"""

XHS_PROMPT_TEMPLATE = """基于这条 AI 热点，写一篇小红书笔记：

话题：{title}
核心信息：{content}

要求：
1. 开头第一句必须够吸引人，让人想展开读（可以用问句/反常识/数字冲击）
2. 用口语写，像在跟朋友发消息
3. 重点说"这个对国内开发者/产品人有什么用"，结合实际使用场景
4. 每段适当加 emoji，但不要每句都加
5. 字数 300-400 字
6. 结尾加一个互动问题

输出格式（严格 JSON）：
{{
  "title": "小红书标题（20字以内，要有点击欲）",
  "content": "正文（纯文本，换行用\\n，emoji 直接写进去）",
  "tags": ["AI工具", "LLM", ...等5-8个话题标签，不带#号]
}}"""


def generate_xhs(topic: dict) -> dict:
    """生成小红书笔记"""
    client = AIClient()

    prompt = XHS_PROMPT_TEMPLATE.format(
        title=topic["title"],
        content=(topic.get("content") or "")[:500],
    )

    try:
        result = asyncio.run(client.complete(
            messages=[
                {"role": "system", "content": XHS_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=1500,
            response_json=True,
        ))

        try:
            data = json.loads(result)
        except Exception:
            m = re.search(r'\{[\s\S]+\}', result)
            data = json.loads(m.group(0)) if m else {}

        return {
            "ok": True,
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "tags": data.get("tags", []),
            "source_topic": topic,
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "source_topic": topic}
