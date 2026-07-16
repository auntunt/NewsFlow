"""
公众号草稿发布器

直接复用 WX--autoarticle 的 get_token / upload_image / create_draft，
不修改原项目任何代码，通过 sys.path 注入使用。

配置：NewsFlow/.env 中加入：
  WX_AUTOARTICLE_PATH=/home/ubuntu/workspace/WX--autoarticle
  WX_ACCOUNT_NAME=你的公众号账号名（对应 storage/cookies/<账号>.json）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 注入 WX--autoarticle 的路径
_WX_PATH = os.getenv("WX_AUTOARTICLE_PATH", "/home/ubuntu/workspace/WX--autoarticle")
_API_PATH = os.path.join(_WX_PATH, "api")
if _API_PATH not in sys.path:
    sys.path.insert(0, _API_PATH)

_ACCOUNT = os.getenv("WX_ACCOUNT_NAME", "")


def publish_wechat_draft(wechat: dict) -> dict:
    """
    创建公众号草稿。
    wechat: {title, content, summary, tags, ok}
    返回: {ok, draft_id, error}
    """
    if not wechat.get("ok"):
        return {"ok": False, "error": "写稿失败，跳过发布"}

    if not _ACCOUNT:
        return {"ok": False, "error": "未配置 WX_ACCOUNT_NAME，请在 .env 中设置"}

    try:
        from engine.auto_publish import get_token, create_draft, upload_image
    except ImportError as e:
        return {"ok": False, "error": f"无法导入 WX--autoarticle 模块: {e}\n请检查 WX_AUTOARTICLE_PATH 配置"}

    # 读 cookie —— 优先从 NewsFlow 本地，fallback 到 WX--autoarticle
    local_cookie = Path("data/cookies") / f"{_ACCOUNT}.json"
    wx_cookie    = Path(_WX_PATH) / "api" / "storage" / "cookies" / f"{_ACCOUNT}.json"
    cookie_file  = local_cookie if local_cookie.exists() else wx_cookie

    if not cookie_file.exists():
        return {
            "ok": False,
            "error": f"Cookie 不存在，已查找：\n  {local_cookie}\n  {wx_cookie}"
        }

    import json
    with open(cookie_file, encoding="utf-8") as f:
        cookies = json.load(f)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    try:
        token = get_token(cookie_str)
        if not token:
            return {"ok": False, "error": "获取微信 token 失败，Cookie 可能已过期"}

        # 公众号内容转 HTML（简单处理换行）
        html_content = _text_to_html(wechat["content"])

        # intro 优先作为摘要（更有吸引力），fallback 到 summary
        digest = (wechat.get("intro") or wechat.get("summary") or "")[:120]
        draft_id = create_draft(
            token=token,
            cookie_str=cookie_str,
            title=wechat["title"],
            content=html_content,
            cdn_url="",
            fileid="",
            author_name=_ACCOUNT,
            digest=digest,
        )

        return {"ok": True, "draft_id": draft_id, "title": wechat["title"]}

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _text_to_html(text: str) -> str:
    """纯文本转公众号 HTML，保留段落结构"""
    import html
    paragraphs = text.strip().split("\n\n")
    parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        escaped = html.escape(para).replace("\n", "<br/>")
        parts.append(
            f'<p style="margin: 0 0 1em 0; line-height: 1.8; font-size: 16px;">'
            f'{escaped}</p>'
        )
    return "\n".join(parts)
