"""
配图生成器（独立版，直接调 torchai.ai gpt-image-2）

为三份内容各生成一张配图：
- 公众号：1024x1024 科技感封面
- 小红书：1024x1024 简洁信息图
- 视频：1024x1792 竖版封面

配置（.env）：
  IMAGE_API_KEY=sk-xxx
  IMAGE_API_BASE=https://torchai.ai
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

IMAGE_API_KEY  = os.getenv("IMAGE_API_KEY", "sk-ZCP3F7JullkCxBGvVwAqMlv5DCyulJ68e9dqJOZ2Fg78JK6L")
IMAGE_API_BASE = os.getenv("IMAGE_API_BASE", "https://torchai.ai")
IMAGE_MODEL    = os.getenv("IMAGE_MODEL", "gpt-image-2")

IMAGES_DIR = Path("data/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _build_prompt(topic: dict, style: str) -> str:
    title = (topic.get("title") or "").lower()

    # 话题主题词
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
        "wechat": (
            f"{theme}, professional tech article cover, dark blue gradient background, "
            "cinematic lighting, high quality, no text, no letters, no words, "
            "16:9 cinematic composition, sharp focus"
        ),
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
        # 写入临时请求文件
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
                    # URL 格式，用 curl 下载
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


def generate_images(topic: dict, run_id: str) -> dict:
    """
    生成三张配图，返回：
    {ok, wechat_image, xhs_image, video_image}
    各值为本地路径或 None
    """
    configs = [
        ("wechat", f"{run_id}_wechat.png", "1024x1024"),
        ("xhs",    f"{run_id}_xhs.png",    "1024x1024"),
        ("video",  f"{run_id}_video.png",   "1024x1792"),
    ]

    results: dict[str, str | None] = {}
    for style, filename, size in configs:
        print(f"  [图片] 生成 {style} 配图 ({size})...")
        prompt = _build_prompt(topic, style)
        path = _generate_one(prompt, filename, size)
        results[f"{style}_image"] = path

    results["ok"] = any(results.get(f"{s}_image") for s in ["wechat", "xhs", "video"])  # type: ignore
    return results
