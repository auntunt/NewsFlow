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
        article_cdns: list[str] = []   # 正文内嵌图的 cdn_url 列表

        if images:
            for key in ("wechat_image", "article_images", "xhs_image"):
                if key == "article_images":
                    continue
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

        # ── 上传正文内嵌图（article_images[1:]，跳过封面）────────────────
        if images:
            article_paths = images.get("article_images") or []
            for i, apath in enumerate(article_paths[1:], 1):   # 跳过[0]（已做封面）
                if not apath or not Path(str(apath)).exists():
                    continue
                print(f"[公众号] 上传内嵌图 {i}: {apath}")
                ac, _, aerr = upload_image(token, cookie_str, str(apath))
                if aerr:
                    print(f"[公众号] 内嵌图 {i} 上传失败: {aerr}")
                else:
                    article_cdns.append(ac)
                    print(f"[公众号] ✓ 内嵌图 {i} 上传成功")

        # ── 2. 正文 HTML（内嵌多张配图）─────────────────────────────────
        html_content = _to_html(
            wechat["content"],
            cover_img=cdn_url,
            inline_imgs=article_cdns,   # 均匀插入正文段落之间
        )

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


def _to_html(text: str, cover_img: str = "",
             inline_img: str = "",      # 兼容旧调用
             inline_imgs: list[str] | None = None) -> str:
    """
    纯文本 → 公众号 HTML，支持多张内嵌配图。
    cover_img  : 顶部封面图
    inline_imgs: 均匀插入正文段落之间的图片列表
    """
    import html as html_lib
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    imgs = inline_imgs or ([inline_img] if inline_img else [])
    parts: list[str] = []

    # 顶部封面
    if cover_img:
        parts.append(
            f'<p style="text-align:center;margin:0 0 1.5em 0">'
            f'<img src="{cover_img}" style="max-width:100%;border-radius:8px"/></p>'
        )

    # 计算图片插入位置（均匀分布在段落之间）
    n_imgs = len(imgs)
    n_paras = len(paragraphs)
    # 例如 3 张图 10 段：在第 3、6、9 段后插图
    insert_after: set[int] = set()
    if n_imgs and n_paras:
        step = max(n_paras // (n_imgs + 1), 1)
        for k in range(1, n_imgs + 1):
            pos = min(k * step - 1, n_paras - 1)
            insert_after.add(pos)

    img_iter = iter(imgs)
    for i, para in enumerate(paragraphs):
        escaped = html_lib.escape(para).replace("\n", "<br/>")
        parts.append(
            f'<p style="margin:0 0 1em 0;line-height:1.9;'
            f'font-size:16px;color:#333">{escaped}</p>'
        )
        if i in insert_after:
            try:
                cdn = next(img_iter)
                if cdn:
                    parts.append(
                        f'<p style="text-align:center;margin:1.5em 0">'
                        f'<img src="{cdn}" style="max-width:100%;border-radius:8px"/></p>'
                    )
            except StopIteration:
                pass

    return "\n".join(parts)


# 旧名兼容
_text_to_html = _to_html
