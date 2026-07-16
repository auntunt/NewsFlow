"""
公众号深度稿生成器

目标：1000-1500字，技术深度 + 中国本土化视角
风格参考：sspai、少数派、科技猫、差评——有观点、有细节、不灌水

Prompt 策略：
- 把海外原始话题作为信息素材，不是翻译
- 结合国内开发者实际场景（部署成本、API 可及性、替代方案）
- 写作规则从 WX--autoarticle writing_rules.md 提炼，内嵌在 prompt 中
"""
from __future__ import annotations

import os
import sys

from newsflow.ai.client import AIClient

# ── 写作规则（来自 WX--autoarticle/api/engine/rules/writing_rules.md 精华）──
WRITING_RULES = """
写作铁律（违反即重写）：
- 句长剧烈长短交替：短句(3-8字)紧贴长句(40+字)，禁止连续3句长度相近
- 禁用词：首先/其次/最后/总之/综上所述/值得注意的是/众所周知/不可否认/由此可见
- 多用具体替代抽象：不写"很多人"写"我认识的三个朋友"；不写"最近"写"上周四"
- 禁止序号(1.2.3.)、小标题、总结段逐条回顾要点
- 每个观点配一段对话或具体生活切片，不停留在抽象分析
- 结尾禁止"综上""未来可期"，用反问/未答之问/场景回扣
- 标题制造"我要点进去"的缺口，不是提前总结全文
"""

# ── 公众号主 prompt ─────────────────────────────────────────────────────────
WECHAT_SYSTEM = """你是一个专注 AI 技术的公众号作者，
擅长把海外最新 AI 动态翻译成中国开发者能直接用上的深度解读。

你的读者是：在国内工作的 AI 工程师、产品经理、独立开发者，
他们用 Claude/GPT API、部署过本地模型、关注 LLM Agent 落地。

写作风格：有技术深度但不堆砌术语，有观点但不贩卖焦虑，
像一个比读者多看了三天信息的朋友在讲话。"""

WECHAT_PROMPT_TEMPLATE = """以下是一条海外 AI 热点：

标题：{title}
来源：{source}
链接：{url}
内容摘要：{content}

---

请基于这条信息，写一篇公众号深度稿，要求：

【内容框架】
1. 开头：用一个国内开发者熟悉的具体场景切入（不是从"最近有一项研究"开始），
   让读者第一句就感觉"这说的就是我的问题"
2. 核心信息：解释这件事是什么、为什么重要——但要比原文多一层分析
3. 中国视角：结合国内实际情况分析（比如：API 访问限制怎么解决？
   国内有没有类似替代方案？实际部署成本如何？哪些坑国内开发者更容易踩？）
4. 实操建议：给读者 1-3 个可以今天就试的具体行动
5. 结尾：一个能触发读者转发或收藏的收尾（反问/未解之问/场景回扣）

【字数】1000-1500字

【写作铁律】
{writing_rules}

---

输出格式（严格 JSON）：
{{
  "title": "公众号标题（15-25字，制造悬念或戳痛点，禁止陈述句）",
  "content": "正文全文（纯文本，换行用\\n，禁止 markdown 格式）",
  "summary": "50字以内的摘要（用于消息推送）",
  "tags": ["标签1", "标签2", "标签3"]
}}"""


def generate_wechat(topic: dict) -> dict:
    """生成公众号深度稿，返回 {title, content, summary, tags, ok}"""
    client = AIClient()

    prompt = WECHAT_PROMPT_TEMPLATE.format(
        title=topic["title"],
        source=topic["source"],
        url=topic["url"],
        content=(topic.get("content") or "")[:800],
        writing_rules=WRITING_RULES,
    )

    try:
        import asyncio
        result = asyncio.run(client.complete(
            messages=[
                {"role": "system", "content": WECHAT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
            response_json=True,
        ))

        # 解析 JSON
        import json, re
        try:
            data = json.loads(result)
        except Exception:
            m = re.search(r'\{[\s\S]+\}', result)
            data = json.loads(m.group(0)) if m else {}

        return {
            "ok": True,
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "summary": data.get("summary", ""),
            "tags": data.get("tags", []),
            "source_topic": topic,
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "source_topic": topic}
