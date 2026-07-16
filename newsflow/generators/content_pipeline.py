"""
NewsFlow Phase 3 — 内容生成入口

从 NewsFlow 最新 run 结果中选出最有价值的 1 条，
生成三份内容：
  1. 公众号深度稿（1000-1500字，技术+本土化视角）
  2. 小红书笔记（300-400字，口语轻量版）
  3. 口播视频脚本（60-90秒，后续接 Remotion 渲染）

用法：
  python -m newsflow.generators.content_pipeline
  python -m newsflow.generators.content_pipeline --run-id 20260716_065007
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from newsflow.generators.topic_picker import pick_topic
from newsflow.generators.wechat_writer import generate_wechat
from newsflow.generators.xhs_writer import generate_xhs
from newsflow.generators.video_script import generate_video_script
from newsflow.generators.image_generator import generate_images
from newsflow.storage.local import LocalStorage


def run(run_id: str | None = None, dry_run: bool = False) -> dict:
    storage = LocalStorage()

    # 找最新 run
    if not run_id:
        runs = sorted(storage.root.iterdir(), reverse=True)
        if not runs:
            print("[Phase3] 没有找到任何 run，请先执行 newsflow run tech_daily")
            sys.exit(1)
        run_id = runs[0].name

    print(f"[Phase3] 使用 run: {run_id}")

    # 读取 filtered items（兼容实际存储格式）
    run_dir = storage.root / run_id
    for candidate in ["filtered.json", "filtered_items.json", "items.json", "run_summary.json"]:
        items_path = run_dir / candidate
        if items_path.exists():
            break
    else:
        print(f"[Phase3] 找不到 items 文件，目录内容：{list(run_dir.iterdir())}")
        sys.exit(1)

    with open(items_path, encoding="utf-8") as f:
        data = json.load(f)

    # 兼容不同存储格式
    if isinstance(data, dict):
        items = data.get("filtered_items") or data.get("items") or []
    else:
        items = data

    if not items:
        print("[Phase3] filtered items 为空")
        sys.exit(1)

    print(f"[Phase3] 候选内容 {len(items)} 条")

    # Step 1: 选题
    topic = pick_topic(items)
    print(f"\n[Phase3] 选题：{topic['title']}")
    print(f"         来源：{topic['source']} | 评分：{topic.get('score', '?')}")
    print(f"         链接：{topic['url']}")

    print("\n[Phase3] 生成配图...")
    images = generate_images(topic, run_id)

    # Step 2: 并行生成三份内容
    print("\n[Phase3] 生成公众号稿...")
    wechat = generate_wechat(topic)

    print("[Phase3] 生成小红书笔记...")
    xhs = generate_xhs(topic)

    print("[Phase3] 生成口播脚本...")
    video = generate_video_script(topic)

    result = {
        "run_id": run_id,
        "topic": topic,
        "images": images,
        "wechat": wechat,
        "xhs": xhs,
        "video_script": video,
    }

    # 保存结果
    out_dir = storage.root / run_id / "phase3"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "content.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[Phase3] ✓ 内容已保存至 {out_dir / 'content.json'}")

    if dry_run:
        print("\n=== 公众号标题 ===")
        print(wechat["title"])
        print("\n=== 小红书标题 ===")
        print(xhs["title"])
        print("\n=== 视频脚本（前200字）===")
        print(video["script"][:200] + "...")
        print("\n=== 配图 ===")
        for k, v in images.items():
            if k.endswith("_image"):
                label = k.replace("_image", "")
                print(f"  {label}: {v or '生成失败'}")
    else:
        # Step 3: 发布
        from newsflow.publishers.wechat_publisher import publish_wechat_draft
        from newsflow.publishers.xhs_publisher import publish_xhs

        print("\n[Phase3] 发布公众号草稿...")
        wx_result = publish_wechat_draft(wechat)
        print(f"         公众号：{'✓ 草稿已创建' if wx_result.get('ok') else '✗ ' + wx_result.get('error','')}")

        print("[Phase3] 发布小红书...")
        xhs_result = publish_xhs(xhs)
        print(f"         小红书：{'✓ 已发布' if xhs_result.get('ok') else '✗ ' + xhs_result.get('error','')}")

    return result


def main():
    parser = argparse.ArgumentParser(description="NewsFlow Phase 3: 写稿+发布")
    parser.add_argument("--run-id", help="指定 run id，默认取最新")
    parser.add_argument("--dry-run", action="store_true", help="只生成不发布，打印预览")
    args = parser.parse_args()
    run(run_id=args.run_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
