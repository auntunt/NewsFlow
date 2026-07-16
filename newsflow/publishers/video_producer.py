"""
video_producer.py — 口播视频生成器

流程：
1. TTS：edge-tts 把每个 segment 转成音频，再合并成完整 mp3
2. 字幕：根据 segments.duration_s 累加时间戳，生成 SRT
3. 背景视频：ffmpeg 把封面图转成竖版静止背景视频，嵌入字幕
4. 最终合成：合并音频 + 带字幕视频 → final mp4
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOICE_MALE = "zh-CN-YunxiNeural"
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"
DEFAULT_VOICE = VOICE_MALE

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess, raise on non-zero exit."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stderr: {result.stderr[-2000:]}"
        )
    return result


# ---------------------------------------------------------------------------
# Step 1: TTS
# ---------------------------------------------------------------------------


async def _tts_segment(text: str, voice: str, out_path: Path) -> None:
    """Generate a single TTS audio file for one segment."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


async def _generate_tts(
    segments: list[dict],
    run_id: str,
    output_dir: Path,
    voice: str = DEFAULT_VOICE,
) -> tuple[Path, list[Path]]:
    """
    Generate TTS for each segment individually, then concat into one mp3.

    Returns (combined_mp3_path, [segment_mp3_paths])
    """
    segment_paths: list[Path] = []

    for i, seg in enumerate(segments):
        seg_path = output_dir / f"{run_id}_seg{i:02d}.mp3"
        await _tts_segment(seg["text"], voice, seg_path)
        segment_paths.append(seg_path)
        print(f"  [TTS] segment {i} → {seg_path.name}")

    # Concat all segments into one audio file using ffmpeg
    combined_path = output_dir / f"{run_id}_audio.mp3"

    if len(segment_paths) == 1:
        import shutil

        shutil.copy2(segment_paths[0], combined_path)
    else:
        # Build ffmpeg concat
        list_file = output_dir / f"{run_id}_concat.txt"
        with open(list_file, "w") as f:
            for p in segment_paths:
                f.write(f"file '{p.resolve()}'\n")

        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(combined_path),
            ]
        )
        list_file.unlink(missing_ok=True)

    print(f"  [TTS] combined audio → {combined_path.name}")
    return combined_path, segment_paths


# ---------------------------------------------------------------------------
# Step 2: SRT subtitle generation
# ---------------------------------------------------------------------------


def _generate_srt(segments: list[dict], run_id: str, output_dir: Path) -> Path:
    """
    Generate SRT from segments list.
    Each segment: {text, duration_s, note}
    """
    srt_path = output_dir / f"{run_id}.srt"

    lines = []
    t = 0.0
    for i, seg in enumerate(segments, start=1):
        start = t
        end = t + float(seg["duration_s"])
        # Wrap long text — SRT usually looks better with shorter lines
        text = seg["text"].replace("\n\n", " ").replace("\n", " ")
        lines.append(str(i))
        lines.append(f"{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}")
        lines.append(text)
        lines.append("")
        t = end

    srt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [SRT] subtitle file → {srt_path.name}")
    return srt_path


# ---------------------------------------------------------------------------
# Step 3 & 4: Video assembly via ffmpeg
# ---------------------------------------------------------------------------


def _get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        # Fallback: sum segment durations
        return 0.0


def _generate_video(
    cover_image_path: Path,
    audio_path: Path,
    srt_path: Path,
    run_id: str,
    output_dir: Path,
) -> Path:
    """
    Build final mp4:
      - cover image → static vertical background (1080x1920)
      - overlay SRT subtitles (white, large, shadow, lower-third)
      - merge with audio
    """
    final_path = output_dir / f"{run_id}_final.mp4"

    # Get actual audio duration so video length matches exactly
    duration = _get_audio_duration(audio_path)
    if duration <= 0:
        # Fallback: use sum of all srt entries
        duration = 120.0

    print(f"  [VIDEO] audio duration = {duration:.1f}s")

    # Escape the srt path for ffmpeg subtitles filter
    # ffmpeg subtitles filter needs the path properly escaped
    srt_escaped = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")

    # subtitle style: white bold large text, drop shadow, positioned at lower 1/3
    # FontSize=56 for 1080-wide vertical video, y position ≈ 1280 (roughly 2/3 down)
    subtitle_style = (
        "FontName=Noto Sans CJK SC,"
        "FontSize=52,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "Bold=1,"
        "Outline=3,"
        "Shadow=2,"
        "Alignment=2,"
        "MarginV=320"
    )

    # ffmpeg command:
    # 1. loop the still image for `duration` seconds
    # 2. scale/crop to 1080x1920 (vertical)
    # 3. burn SRT subtitles
    # 4. add audio, cut to audio length
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(cover_image_path.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-vf",
        (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"subtitles='{srt_escaped}':force_style='{subtitle_style}'"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        "-t",
        str(duration),
        str(final_path),
    ]

    print(f"  [VIDEO] encoding final mp4 (this may take ~10-30s)…")
    _run(cmd)
    print(f"  [VIDEO] final mp4 → {final_path.name}")
    return final_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def produce_video(
    video_script: dict,
    run_id: str,
    cover_image_path: str,
    voice: str = DEFAULT_VOICE,
) -> dict:
    """
    Generate a vertical short-video with TTS audio + subtitles.

    Args:
        video_script: dict with keys {script, segments, cover_text, hashtags}
        run_id:        e.g. "20260716_083018"
        cover_image_path: path to the cover/background image
        voice:         edge-tts voice name (default: zh-CN-YunxiNeural)

    Returns:
        {ok, video_path, audio_path, srt_path, error}
    """
    try:
        # Resolve paths
        workspace = Path(__file__).resolve().parents[2]  # newsflow/publishers/ → NewsFlow/
        output_dir = _ensure_dir(workspace / "data" / "videos")
        cover = Path(cover_image_path).resolve()

        if not cover.exists():
            raise FileNotFoundError(f"Cover image not found: {cover}")

        segments = video_script.get("segments", [])
        if not segments:
            raise ValueError("video_script.segments is empty")

        print(f"\n[VideoProducer] Starting for run_id={run_id}")
        print(f"  cover image : {cover}")
        print(f"  output dir  : {output_dir}")
        print(f"  voice       : {voice}")
        print(f"  segments    : {len(segments)}")

        # 1. TTS
        print("\n[Step 1] TTS generation…")
        audio_path, _seg_paths = asyncio.run(
            _generate_tts(segments, run_id, output_dir, voice=voice)
        )

        # 2. SRT
        print("\n[Step 2] Subtitle generation…")
        srt_path = _generate_srt(segments, run_id, output_dir)

        # 3 & 4. Video assembly
        print("\n[Step 3+4] Video assembly…")
        final_path = _generate_video(cover, audio_path, srt_path, run_id, output_dir)

        size = final_path.stat().st_size
        print(f"\n✅ Done! Final video: {final_path}  ({size / 1024 / 1024:.1f} MB)")

        return {
            "ok": True,
            "video_path": str(final_path),
            "audio_path": str(audio_path),
            "srt_path": str(srt_path),
            "error": None,
        }

    except Exception as e:
        import traceback

        err = traceback.format_exc()
        print(f"\n❌ Error: {e}\n{err}")
        return {
            "ok": False,
            "video_path": None,
            "audio_path": None,
            "srt_path": None,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# CLI / test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Load video_script from content.json
    run_id = sys.argv[1] if len(sys.argv) > 1 else "20260716_083018"
    workspace = Path(__file__).resolve().parents[2]  # → NewsFlow/

    content_path = workspace / "data" / "runs" / run_id / "phase3" / "content.json"
    with open(content_path, encoding="utf-8") as f:
        content = json.load(f)

    video_script = content["video_script"]
    cover_image = workspace / "data" / "images" / f"{run_id}_video.png"

    result = produce_video(
        video_script=video_script,
        run_id=run_id,
        cover_image_path=str(cover_image),
    )

    print("\n--- Result ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["ok"]:
        vp = Path(result["video_path"])
        size_mb = vp.stat().st_size / 1024 / 1024
        print(f"\nFinal MP4: {vp}")
        print(f"File size: {size_mb:.2f} MB")
