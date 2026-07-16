"""
公众号草稿发布器

直接复用 WX--autoarticle 的 get_token / upload_image / create_draft。

配置（.env）：
  WX_AUTOARTICLE_PATH=/tmp/WX--autoarticle
  WX_ACCOUNT_NAME=AI挖矿日记
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_WX_PATH  = os.getenv("WX_AUTOARTICLE_PATH", "/tmp/WX--autoarticle")
_API_PATH = os.path.join(_WX_PATH, "api")
if _API_PATH not in sys.path:
    sys.path.insert(0, _API_PATH)
if _WX_PATH not in sys.path:
    sys.path.insert(0, _WX_PATH)

_ACCOUNT = os.getenv("WX_ACCOUNT_NAME", "")


def publish_wechat_draft(wechat: dict, images: dict | None = None) -> dict:
    """
    创建公众号草稿，含封面图和正文内嵌配图。
    wechat : {title, content, summary, intro, tags, ok}
    images : {wechat_image: 路径, xhs_image: 路径, ...}  可选
    返回   : {ok, draft_id, has_cover, error}
    """
    if not wechat.get("ok"):
        return {"ok": False, "error": "写稿失败，跳过发布"}
    if not _ACCOUNT:
        return {"ok": False, "error": "未配置 WX_ACCOUNT_NAME"}

    try:
        from engine.auto_publish import get_token, create_draft, upload_image
    except ImportError as e:
        return {"ok": False, "error": f"导入失败: {e}，请检查 WX_AUTOARTICLE_PATH"}

    # ── Cookie ────────────────────────────────────────────────────────────
    local_cookie = Path("data/cookies") / f"{_ACCOUNT}.json"
    wx_cookie    = Path(_WX_PATH) / "api" / "storage" / "cookies" / f"{_ACCOUNT}.json"
    cookie_file  = local_cookie if local_cookie.exists() else wx_cookie

    if not cookie_file.exists():
        return {"ok": False, "error": f"Cookie 不存在: {local_cookie} / {wx_cookie}"}

    import json
    with open(cookie_file, encoding="utf-8") as f:
        cookies = json.load(f)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    try:
        # ── Token ─────────────────────────────────────────────────────────
        token = get_token(cookie_str)
        if not token:
            return {"ok": False, "error": "获取 token 失败，Cookie 可能已过期"}

        # ── 1. 上传封面图 ─────────────────────────────────────────────────
        cdn_url = fileid = ""
        cover_path = None
        if images:
            for key in ("wechat_image", "xhs_image"):
                p = images.get(key)
                if p and Path(str(p)).exists():
                    cover_path = str(p)
                    break

        if cover_path:
            print(f"[公众号] 上传封面: {cover_path}")
            cdn_url, fileid, err = upload_image(token, cookie_str, cover_path)
            if err:
                print(f"[公众号] 封面上传失败（继续）: {err}")
                cdn_url = fileid = ""
            else:
                print(f"[公众号] ✓ 封面上传成功")
        else:
            print("[公众号] 无封面图")

        # ── 2. 正文 HTML（顶部内嵌配图）──────────────────────────────────
        html_content = _to_html(wechat["content"], inline_img=cdn_url)

        # ── 3. 创建草稿 ───────────────────────────────────────────────────
        digest   = (wechat.get("intro") or wechat.get("summary") or "")[:120]
        draft_id = create_draft(
            token=token,
            cookie_str=cookie_str,
            title=wechat["title"],
            content=html_content,
            cdn_url=cdn_url,
            fileid=fileid,
            author_name=_ACCOUNT,
            digest=digest,
        )

        print(f"[公众号] ✓ 草稿已创建: {draft_id}")
        return {
            "ok":        True,
            "draft_id":  draft_id,
            "title":     wechat["title"],
            "has_cover": bool(cdn_url),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _to_html(text: str, inline_img: str = "") -> str:
    """纯文本 → 公众号 HTML，可选顶部内嵌配图"""
    import html as html_lib
    parts = []

    # 正文顶部配图
    if inline_img:
        parts.append(
            f'<p style="text-align:center;margin:0 0 1.5em 0">'
            f'<img src="{inline_img}" style="max-width:100%;border-radius:8px"/></p>'
        )

    for para in text.strip().split("\n\n"):
        para = para.strip()
        if not para:
            continue
        escaped = html_lib.escape(para).replace("\n", "<br/>")
        parts.append(
            f'<p style="margin:0 0 1em 0;line-height:1.9;'
            f'font-size:16px;color:#333">{escaped}</p>'
        )

    return "\n".join(parts)


# 旧名兼容
_text_to_html = _to_html
