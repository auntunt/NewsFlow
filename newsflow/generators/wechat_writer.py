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

请基于这条信息，写一篇公众号深度长文，要求：

【字数要求】
**必须 1500 字以上**，不足 1500 字视为不合格。宁可多写不要少。

【内容框架（必须覆盖以下五个部分）】

第一部分·事件切入（200字）
用一个国内开发者熟悉的具体场景开头，不从"最近有一项研究"开始。
让读者第一句就觉得"这说的就是我的问题"。

第二部分·核心事件（300字）
详细解释这件事是什么、怎么发生的、涉及哪些关键细节。
不要只复述标题，要比原文多一层信息。

第三部分·技术深挖（400字）
从技术角度深入分析：背后的原理是什么？为什么会这样设计或发生？
有没有类似的历史案例可以对比？技术社区的反应和争议点在哪？

第四部分·中国视角（300字）
结合国内实际情况深度分析，必须覆盖以下至少两点：
- 国内开发者/企业面临的具体差异（工具可及性、网络环境、合规要求等）
- 国内是否有对应的替代方案或类似产品？差距在哪？
- 这件事对国内 AI 工程师的实际工作有什么影响？
- 踩过类似坑的国内案例或社区讨论

第五部分·行动建议+结尾（300字）
给读者 2-4 个今天就能做的具体行动建议（要足够具体，不是泛泛而谈）。
结尾用一个能触发转发或收藏的收尾句（反问/未解之问/场景回扣）。

【写作铁律】
{writing_rules}

---

输出格式（严格 JSON）：
{{
  "title": "公众号标题（15-25字，制造悬念或戳痛点，禁止陈述句标题）",
  "content": "正文全文（纯文本，换行用\\n，禁止 markdown 格式，必须 1500 字以上）",
  "summary": "50字以内的摘要（用于消息推送预览）",
  "intro": "100字以内的文章简介（显示在公众号文章列表下方，吸引人点进来，口语化，有悬念感，不要剧透结论）",
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
            max_tokens=6000,
            response_json=True,
        ))

        # 解析 JSON（长文容易有特殊字符，多重兜底）
        import json, re
        data = {}
        # 1. 直接解析
        try:
            data = json.loads(result)
        except Exception:
            pass

        # 2. 提取最外层 {}
        if not data:
            m = re.search(r'\{[\s\S]+\}', result)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    pass

        # 3. 逐字段正则提取（最稳健，专门处理长文 JSON）
        if not data or not data.get("content"):
            title_m   = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', result)
            content_m = re.search(r'"content"\s*:\s*"([\s\S]*?)"\s*,\s*"summary"', result)
            summary_m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', result)
            intro_m   = re.search(r'"intro"\s*:\s*"((?:[^"\\]|\\.)*)"', result)
            tags_m    = re.search(r'"tags"\s*:\s*\[([^\]]*)\]', result)

            if title_m or content_m:
                tags = []
                if tags_m:
                    tags = re.findall(r'"([^"]+)"', tags_m.group(1))
                data = {
                    "title":   title_m.group(1) if title_m else "",
                    "content": content_m.group(1).replace("\\n", "\n") if content_m else "",
                    "summary": summary_m.group(1) if summary_m else "",
                    "intro":   intro_m.group(1) if intro_m else "",
                    "tags":    tags,
                }

        return {
            "ok":           True,
            "title":        data.get("title", ""),
            "content":      data.get("content", ""),
            "summary":      data.get("summary", ""),
            "intro":        data.get("intro", ""),
            "tags":         data.get("tags", []),
            "word_count":   len(data.get("content", "")),
            "source_topic": topic,
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "source_topic": topic}
