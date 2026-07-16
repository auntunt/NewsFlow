"""
小红书发布器

直接复用 WX--autoarticle 的 XhsPublisher（Playwright 自动化）。

配置：NewsFlow/.env 中加入：
  WX_AUTOARTICLE_PATH=/home/ubuntu/workspace/WX--autoarticle
  XHS_ACCOUNT_NAME=你的小红书账号名（对应 storage/cookies/xhs_<账号>.json）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_WX_PATH = os.getenv("WX_AUTOARTICLE_PATH", "/home/ubuntu/workspace/WX--autoarticle")
_API_PATH = os.path.join(_WX_PATH, "api")
if _API_PATH not in sys.path:
    sys.path.insert(0, _API_PATH)

_XHS_ACCOUNT = os.getenv("XHS_ACCOUNT_NAME", "")


def publish_xhs(xhs: dict) -> dict:
    """
    发布小红书笔记。
    xhs: {title, content, tags, ok}
    返回: {ok, error}
    """
    if not xhs.get("ok"):
        return {"ok": False, "error": "写稿失败，跳过发布"}

    if not _XHS_ACCOUNT:
        return {"ok": False, "error": "未配置 XHS_ACCOUNT_NAME，请在 .env 中设置"}

    try:
        from publisher.xhs_publisher import XhsPublisher
    except ImportError as e:
        return {"ok": False, "error": f"无法导入 XhsPublisher: {e}"}

    # 构造话题列表（加 # 前缀）
    topics = [f"#{t}" for t in (xhs.get("tags") or [])[:8]]

    try:
        publisher = XhsPublisher(_XHS_ACCOUNT, wx_autoarticle_root=_WX_PATH)
        result = publisher.publish(
            title=xhs["title"][:20],        # 小红书标题限 20 字
            content=xhs["content"],
            image_paths=[],                  # 无图片时走纯文字笔记
            topics=topics,
            visibility="public",
        )
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
