"""
口播视频脚本生成器

目标：60-90秒口播脚本，结构化输出，后续接 Remotion 渲染
格式：分段 + 每段时长估算，便于字幕切割

口播风格参考：差评、科技每日推送、回形针——
- 第一句就抓住人
- 每句话都有信息量，没有废话
- 口语化但不口水话
- 有节奏感（停顿用"……"标记）
"""
from __future__ import annotations

import asyncio
import json
import re

from newsflow.ai.client import AIClient

VIDEO_SYSTEM = """你是一个 AI 科技内容的短视频口播作者，
专门为视频号/抖音写 60-90 秒的口播脚本。

你的受众：对 AI 感兴趣、有一定技术背景的中国年轻人。
风格：信息密度高、节奏快、有点个性，像 B 站 UP 主在讲话而不是在播新闻。"""

VIDEO_PROMPT_TEMPLATE = """基于这条 AI 热点，写一段 60-90 秒的口播脚本：

话题：{title}
核心信息：{content}

脚本结构要求：
- 钩子（5秒）：第一句话必须让人停止划屏，可以是反常识/数字冲击/直接点痛
- 核心内容（40-60秒）：解释是什么、为什么重要、国内开发者怎么用
- 收尾（5-10秒）：一句有力的总结或行动号召

格式要求：
- 口语化，像真人在说话，不是在念稿
- 用"……"标记自然停顿
- 避免"今天我来讲"这类废话开头
- 专业术语第一次出现时用口语解释
- 整体字数 200-300 字（对应 60-90 秒语速）

输出格式（严格 JSON）：
{{
  "script": "完整口播脚本（纯文本，……表示停顿）",
  "segments": [
    {{"text": "第一段文字", "duration_s": 5, "note": "钩子"}},
    {{"text": "第二段文字", "duration_s": 45, "note": "核心内容"}},
    {{"text": "第三段文字", "duration_s": 10, "note": "收尾"}}
  ],
  "cover_text": "封面大字（5-10字，抓眼球）",
  "hashtags": ["视频号话题标签1", "视频号话题标签2"]
}}"""


def generate_video_script(topic: dict) -> dict:
    """生成口播视频脚本"""
    client = AIClient()

    prompt = VIDEO_PROMPT_TEMPLATE.format(
        title=topic["title"],
        content=(topic.get("content") or "")[:500],
    )

    try:
        result = asyncio.run(client.complete(
            messages=[
                {"role": "system", "content": VIDEO_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,
            max_tokens=2000,
            response_json=True,
        ))

        try:
            data = json.loads(result)
        except Exception:
            m = re.search(r'\{[\s\S]+\}', result)
            data = json.loads(m.group(0)) if m else {}

        return {
            "ok": True,
            "script": data.get("script", ""),
            "segments": data.get("segments", []),
            "cover_text": data.get("cover_text", ""),
            "hashtags": data.get("hashtags", []),
            "source_topic": topic,
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "source_topic": topic}
