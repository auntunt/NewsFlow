"""
配图生成器（独立版，直接调 torchai.ai gpt-image-2）

根据文章内容智能生成 4 张相关配图：
- article_0.png : 封面图（1024x1024，同时作为公众号封面）
- article_1.png : 技术概念图（1024x1024）
- article_2.png : 中国视角图（1024x1024）
- article_3.png : 行动建议图（1024x1024）

以及原有三份固定封面（xhs / video），wechat_image 改为复用 article_0。

配置（.env）：
  IMAGE_API_KEY=sk-xxx
  IMAGE_API_BASE=https://torchai.ai
  OPENAI_API_KEY=sk-xxx
  OPENAI_API_BASE=https://zjz-ai.webtrn.cn/v1
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

IMAGE_API_KEY  = os.getenv("IMAGE_API_KEY",  "«redacted:sk-…»")
IMAGE_API_BASE = os.getenv("IMAGE_API_BASE", "https://torchai.ai")
IMAGE_MODEL    = os.getenv("IMAGE_MODEL",    "gpt-image-2")

IMAGES_DIR = Path("data/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# ── LLM prompt generation ─────────────────────────────────────────────────────

async def _async_generate_prompts(topic: dict, wechat_content: str) -> list[str]:
    """使用 LLM（AIClient）根据文章内容生成 4 个英文图片 prompt。"""
    from newsflow.ai.client import AIClient

    title = topic.get("title", "AI Technology")
    # 取前 1000 字
    snippet = wechat_content[:1000] if wechat_content else ""

    system_msg = (
        "You are an art director for a Chinese tech media publication. "
        "Your job is to generate cinematic, photorealistic image prompts for AI-generated article illustrations. "
        "Rules: NO text, NO letters, NO words, NO UI elements in images. "
        "Style: realistic, tech-forward, cinematic lighting, high quality photography or 3D render. "
        "Output exactly 4 lines, one prompt per line, no numbering, no labels, no extra commentary."
    )

    user_msg = (
        f"Article title: {title}\n\n"
        f"Article content excerpt (first 1000 chars):\n{snippet}\n\n"
        "Generate 4 English image prompts for this article. Each prompt corresponds to one section:\n"
        "Line 1 — Cover image: captures the article's main theme, bold and eye-catching\n"
        "Line 2 — Technical concept: visualizes the core technology or mechanism described\n"
        "Line 3 — China perspective: shows Chinese tech ecosystem, Chinese engineers, or China-specific angle\n"
        "Line 4 — Call to action: forward-looking, inspiring, depicts future possibilities or next steps\n\n"
        "Each prompt must be self-contained, specific, photorealistic/cinematic, "
        "no text no letters no words no UI, realistic sci-tech aesthetic."
    )

    client = AIClient()
    raw = await client.complete(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=800,
    )

    # 解析：每行一个 prompt，过滤空行
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    # 确保恰好 4 个；不足时用 fallback，过多时截断
    fallbacks = _fallback_prompts(topic)
    prompts: list[str] = []
    for i in range(4):
        if i < len(lines):
            prompts.append(lines[i])
        else:
            prompts.append(fallbacks[i])
    return prompts


def _generate_article_image_prompts(topic: dict, wechat_content: str = "") -> list[str]:
    """
    同步入口：调用 LLM 为文章生成 4 个英文图片 prompt。

    每个 prompt 对应文章一个部分：
      [0] 封面  [1] 技术概念  [2] 中国视角  [3] 行动建议

    若 LLM 调用失败，退回到基于话题关键词的固定 prompt。
    """
    try:
        return asyncio.run(_async_generate_prompts(topic, wechat_content))
    except Exception as e:
        print(f"  [图片] LLM prompt 生成失败，使用 fallback: {e}")
        return _fallback_prompts(topic)


def _fallback_prompts(topic: dict) -> list[str]:
    """基于话题关键词的保底 prompt，当 LLM 不可用时使用。"""
    title = (topic.get("title") or "").lower()

    if any(k in title for k in ["security", "ssh", "key", "leak", "hack", "vulnerab", "privacy"]):
        theme = "cybersecurity, digital lock and shield, warning red accents, dark background, no text"
    elif any(k in title for k in ["open source", "github", "code", "build", "apache"]):
        theme = "open source developer, terminal green on dark, code flowing, collaborative network, no text"
    elif any(k in title for k in ["agent", "workflow", "autonom", "automation"]):
        theme = "AI agents network, interconnected glowing nodes, autonomous workflow, dark sci-fi, no text"
    elif any(k in title for k in ["llm", "model", "claude", "gpt", "gemini", "grok", "reasoning"]):
        theme = "large language model neural network, glowing nodes, abstract AI brain, cinematic, no text"
    elif any(k in title for k in ["local", "self-host", "inference", "ollama"]):
        theme = "local AI computing, personal server, home lab, warm lighting, technical, no text"
    else:
        theme = "AI technology abstract visualization, data flowing, modern tech aesthetic, no text"

    base = f"{theme}, photorealistic, cinematic lighting, 8K, sharp focus, no letters no words"
    return [
        f"Cover art: {base}, bold dramatic composition",
        f"Technical concept: {base}, blueprint-style technical visualization",
        f"China tech perspective: {base}, Chinese engineers in modern office, Shanghai skyline",
        f"Future outlook: {base}, forward-looking inspirational scene, sunrise over digital city",
    ]


# ── Image generation ──────────────────────────────────────────────────────────

def _build_prompt(topic: dict, style: str) -> str:
    """原有固定样式 prompt（xhs / video 封面仍使用此逻辑）。"""
    title = (topic.get("title") or "").lower()

    if any(k in title for k in ["security", "ssh", "key", "leak", "hack", "vulnerab"]):
        theme = "cybersecurity theme, lock and shield visuals, warning red accents, dark background"
    elif any(k in title for k in ["open source", "github", "code", "build"]):
        theme = "open source developer theme, terminal green on dark, code matrix style"
    elif any(k in title for k in ["agent", "workflow", "autonom", "automation"]):
        theme = "AI agents network visualization, interconnected nodes, autonomous workflow"
    elif any(k in title for k in ["llm", "model", "claude", "gpt", "gemini", "reasoning"]):
        theme = "large language model neural network, glowing nodes, abstract AI brain visualization"
    elif any(k in title for k in ["local", "self-host", "inference", "ollama"]):
        theme = "local AI computing theme, personal server, home lab aesthetic"
    else:
        theme = "AI technology abstract visualization, data flowing, modern tech aesthetic"

    styles = {
        "xhs": (
            f"{theme}, clean modern infographic style, white and light background, "
            "colorful accent, flat design, Instagram-worthy, no text, no letters, "
            "square 1:1 composition, minimalist"
        ),
        "video": (
            f"{theme}, dramatic vertical video cover art, dark atmospheric background, "
            "neon tech glow, high contrast, no text, no letters, "
            "9:16 vertical composition, bold visual impact"
        ),
    }
    return styles[style]


def _generate_one(prompt: str, filename: str, size: str, max_retries: int = 3) -> str | None:
    """调用 gpt-image-2 生成一张图，保存到 data/images/，返回路径或 None"""
    api_url = IMAGE_API_BASE.rstrip("/") + "/v1/images/generations"
    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }

    for attempt in range(1, max_retries + 1):
        tmp_in  = tempfile.mktemp(suffix=".json")
        tmp_out = tempfile.mktemp(suffix=".json")
        try:
            with open(tmp_in, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            result = subprocess.run(
                [
                    "curl", "-s", "--http1.1", "--max-time", "120",
                    "-X", "POST", api_url,
                    "-H", "Content-Type: application/json",
                    "-H", f"Authorization: Bearer {IMAGE_API_KEY}",
                    "-d", f"@{tmp_in}",
                    "-o", tmp_out,
                ],
                capture_output=True, timeout=130,
            )

            if result.returncode != 0:
                print(f"    [图片] curl 失败 (attempt {attempt})")
                continue

            with open(tmp_out, encoding="utf-8") as f:
                data = json.load(f)

            if data.get("error"):
                print(f"    [图片] API 错误: {data['error']}")
                continue

            b64 = (data.get("data") or [{}])[0].get("b64_json")
            if not b64:
                url = (data.get("data") or [{}])[0].get("url")
                if url:
                    dest = IMAGES_DIR / filename
                    subprocess.run(["curl", "-s", "-o", str(dest), url], timeout=60)
                    if dest.exists() and dest.stat().st_size > 1000:
                        return str(dest)
                print(f"    [图片] 无 b64_json 数据 (attempt {attempt})")
                continue

            dest = IMAGES_DIR / filename
            with open(dest, "wb") as f:
                f.write(base64.b64decode(b64))

            size_kb = dest.stat().st_size // 1024
            print(f"    [图片] ✓ {filename} ({size_kb}KB)")
            return str(dest)

        except Exception as e:
            print(f"    [图片] 异常 (attempt {attempt}): {e}")
        finally:
            for p in [tmp_in, tmp_out]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    return None


def generate_images(
    topic: dict,
    run_id: str,
    wechat_content: str = "",
) -> dict:
    """
    智能生成 4 张文章配图 + xhs/video 封面，返回：
    {
      ok: bool,
      article_images: [path|None, path|None, path|None, path|None],
      wechat_image: path|None,   # 同 article_images[0]
      xhs_image:    path|None,
      video_image:  path|None,
    }
    """
    # ── Step 1: LLM 生成 4 个文章配图 prompt ──────────────────────────────────
    print("  [图片] 调用 LLM 生成文章配图 prompt...")
    article_prompts = _generate_article_image_prompts(topic, wechat_content)
    for i, p in enumerate(article_prompts):
        label = ["封面", "技术概念", "中国视角", "行动建议"][i]
        print(f"    [{i}] {label}: {p[:80]}{'…' if len(p) > 80 else ''}")

    # ── Step 2: 并发生成 4 张文章配图 (1024x1024) ─────────────────────────────
    article_configs = [
        (article_prompts[i], f"{run_id}_article_{i}.png", "1024x1024")
        for i in range(4)
    ]

    # xhs / video 封面仍用原有固定 prompt
    cover_configs = [
        (_build_prompt(topic, "xhs"),   f"{run_id}_xhs.png",   "1024x1024"),
        (_build_prompt(topic, "video"), f"{run_id}_video.png",  "1024x1792"),
    ]

    all_configs = article_configs + cover_configs
    results_map: dict[str, str | None] = {}

    print(f"  [图片] 并发生成 {len(all_configs)} 张图片...")
    with ThreadPoolExecutor(max_workers=len(all_configs)) as executor:
        future_to_key = {
            executor.submit(_generate_one, prompt, filename, size): filename
            for prompt, filename, size in all_configs
        }
        for future in as_completed(future_to_key):
            filename = future_to_key[future]
            try:
                results_map[filename] = future.result()
            except Exception as e:
                print(f"    [图片] {filename} 生成异常: {e}")
                results_map[filename] = None

    # ── Step 3: 整理结果 ──────────────────────────────────────────────────────
    article_images = [
        results_map.get(f"{run_id}_article_{i}.png")
        for i in range(4)
    ]

    wechat_image = article_images[0]   # 封面即 article_0
    xhs_image    = results_map.get(f"{run_id}_xhs.png")
    video_image  = results_map.get(f"{run_id}_video.png")

    ok = any(p is not None for p in article_images)

    return {
        "ok":             ok,
        "article_images": article_images,
        "wechat_image":   wechat_image,
        "xhs_image":      xhs_image,
        "video_image":    video_image,
    }
