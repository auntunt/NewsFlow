"""
Remotion 口播视频生成器

流程：
1. edge-tts 生成音频，同时拿到词级时间戳（SSML word boundary）
2. 把时间戳转为 Remotion CaptionSegment 格式
3. 写入 props.json
4. 调用 remotion render 生成视频

edge-tts 支持 --write-media 和 --write-subtitles（WebVTT 格式含词级时间戳）
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts

VIDEOS_DIR = Path("data/videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

REMOTION_DIR = Path(__file__).parent.parent.parent / "remotion"

# 声音选择
VOICE_MALE   = "zh-CN-YunxiNeural"
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"


# ── 1. edge-tts 生成音频 + 词级字幕 ─────────────────────────────────────────
async def _tts_with_timestamps(
    text: str, audio_path: str, voice: str = VOICE_MALE
) -> list[dict]:
    """
    生成音频并返回词级时间戳列表。
    返回: [{"word": "你", "start_ms": 0, "end_ms": 320}, ...]
    """
    communicate = edge_tts.Communicate(text, voice)
    words: list[dict] = []
    audio_chunks: list[bytes] = []

    async for event in communicate.stream():
        if event["type"] == "audio":
            audio_chunks.append(event["data"])
        elif event["type"] == "WordBoundary":
            offset_ms  = event["offset"] // 10000   # 100ns → ms
            duration_ms = event["duration"] // 10000
            words.append({
                "word":     event["text"],
                "start_ms": offset_ms,
                "end_ms":   offset_ms + duration_ms,
            })

    with open(audio_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    return words


# ── 2. 词列表 → CaptionSegment（每 N 个字一段）───────────────────────────────
def _words_to_segments(
    words: list[dict], chars_per_segment: int = 10
) -> list[dict]:
    """把词列表分组成字幕段，每段约 10 个字"""
    if not words:
        return []

    segments = []
    i = 0
    while i < len(words):
        chunk = words[i : i + chars_per_segment]
        seg_text = "".join(w["word"] for w in chunk)
        segments.append({
            "text":    seg_text,
            "startMs": chunk[0]["start_ms"],
            "endMs":   chunk[-1]["end_ms"],
            "words": [
                {
                    "word":    w["word"],
                    "startMs": w["start_ms"],
                    "endMs":   w["end_ms"],
                }
                for w in chunk
            ],
        })
        i += chars_per_segment

    return segments


# ── 3. 调用 Remotion CLI 渲染 ──────────────────────────────────────────────
def _render_with_remotion(
    props: dict,
    output_path: str,
    duration_sec: float,
    concurrency: int = 2,
) -> bool:
    """写 props.json，调用 remotion render"""
    props_file = VIDEOS_DIR / "remotion_props.json"
    with open(props_file, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    fps = 30
    frames = int(duration_sec * fps) + 30  # 多留1秒

    cmd = [
        "npx", "remotion", "render", "NewsFlowVideo",
        "--props", str(props_file.absolute()),
        "--output", str(Path(output_path).absolute()),
        "--duration-in-frames", str(frames),
        "--concurrency", str(concurrency),
        "--log", "error",
    ]

    print(f"[Remotion] 开始渲染 ({frames} 帧，{duration_sec:.1f}s)...")
    result = subprocess.run(
        cmd,
        cwd=str(REMOTION_DIR),
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        print(f"[Remotion] 渲染失败:\n{result.stderr[-2000:]}")
        return False

    print(f"[Remotion] ✓ 渲染完成: {output_path}")
    return True


# ── 主入口 ─────────────────────────────────────────────────────────────────
def produce_remotion_video(
    video_script: dict,
    run_id: str,
    account_name: str = "AI 挖矿日记",
    voice: str = VOICE_MALE,
) -> dict:
    """
    完整流程：脚本 → 音频+时间戳 → Remotion 渲染 → mp4

    video_script: {script, segments, cover_text, hashtags}
    返回: {ok, video_path, audio_path, error}
    """
    script_text = video_script.get("script", "")
    cover_text  = video_script.get("cover_text", "AI挖矿日记")
    hashtags    = video_script.get("hashtags", [])

    if not script_text:
        return {"ok": False, "error": "视频脚本为空"}

    audio_path = str(VIDEOS_DIR / f"{run_id}_remotion_audio.mp3")
    video_path = str(VIDEOS_DIR / f"{run_id}_remotion.mp4")

    # Step 1: TTS + 词级时间戳
    print("[视频] TTS 生成音频...")
    words = asyncio.run(_tts_with_timestamps(script_text, audio_path, voice))
    print(f"[视频] ✓ 音频生成，{len(words)} 个词，时间戳已提取")

    if not words:
        return {"ok": False, "error": "TTS 生成失败或无词级时间戳"}

    # 音频总时长（ms）
    total_ms   = words[-1]["end_ms"] + 1000   # 结尾多1秒
    total_sec  = total_ms / 1000

    # Step 2: 词 → 字幕段
    # 封面5秒，字幕从5秒后开始，所有 ms 加 5000 偏移
    COVER_MS = 5000
    shifted_words = [
        {**w, "start_ms": w["start_ms"] + COVER_MS,
               "end_ms":   w["end_ms"]   + COVER_MS}
        for w in words
    ]
    segments = _words_to_segments(shifted_words, chars_per_segment=10)
    total_sec_with_cover = total_sec + COVER_MS / 1000

    # Step 3: 构建 Remotion props
    # 音频路径用相对于 remotion 目录的形式
    audio_rel = str(Path(audio_path).absolute())

    props = {
        "audioSrc":        audio_rel,
        "coverText":       cover_text,
        "segments":        segments,
        "coverDurationSec": 5,
        "accountName":    account_name,
        "hashtags":        hashtags[:3],
    }

    # Step 4: 渲染
    success = _render_with_remotion(
        props, video_path, total_sec_with_cover
    )

    if not success:
        return {"ok": False, "error": "Remotion 渲染失败，查看日志"}

    size_mb = Path(video_path).stat().st_size / 1024 / 1024 if Path(video_path).exists() else 0
    print(f"[视频] ✓ 最终视频: {video_path} ({size_mb:.1f}MB)")

    return {
        "ok":         True,
        "video_path": video_path,
        "audio_path": audio_path,
        "size_mb":    round(size_mb, 1),
    }
