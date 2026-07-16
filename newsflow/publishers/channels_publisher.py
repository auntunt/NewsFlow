"""
视频号发布器

基于 social-auto-upload 的视频号实现逻辑，独立集成进 NewsFlow。
支持：图文笔记（不需要视频文件）+ 视频（Phase 3.2 Remotion 后接入）

Cookie 管理：
  - 首次登录：调用 login() 生成二维码扫码，保存 storage_state
  - Cookie 路径：data/cookies/channels_<账号>.json

配置（.env）：
  CHANNELS_ACCOUNT_NAME=AI挖矿日记
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CHANNELS_URL      = "https://channels.weixin.qq.com"
CHANNELS_POST_URL = "https://channels.weixin.qq.com/platform/post/create"
ACCOUNT           = os.getenv("CHANNELS_ACCOUNT_NAME",
                               os.getenv("WX_ACCOUNT_NAME", "AI挖矿日记"))
COOKIE_DIR        = Path("data/cookies")
COOKIE_DIR.mkdir(parents=True, exist_ok=True)

# 复用已安装的 playwright chromium
CHROMIUM_PATH = os.environ.get(
    "CHROMIUM_PATH",
    "/home/ubuntu/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome"
)


def _launch_kwargs(headless: bool = True) -> dict:
    kwargs: dict = {
        "headless": headless,
        "args": ["--no-sandbox", "--disable-setuid-sandbox",
                 "--disable-dev-shm-usage"],
    }
    if os.path.exists(CHROMIUM_PATH):
        kwargs["executable_path"] = CHROMIUM_PATH
    return kwargs


def _cookie_path(account: str) -> Path:
    return COOKIE_DIR / f"channels_{account}.json"


# ── 登录（生成二维码，等待扫码）──────────────────────────────────────────────
async def login(account: str = ACCOUNT, headless: bool = True,
                qr_save_path: str = "/tmp/channels_qrcode.png") -> dict:
    """扫码登录视频号，保存 storage_state"""
    from patchright.async_api import async_playwright

    cookie_file = _cookie_path(account)
    print(f"[视频号] 开始登录，二维码保存至: {qr_save_path}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**_launch_kwargs(headless))
        ctx  = await browser.new_context()
        page = await ctx.new_page()
        await page.goto(CHANNELS_URL, timeout=30000)
        await asyncio.sleep(2)

        # 截取二维码
        try:
            qr = await page.wait_for_selector(
                "img.qrcode-image, img[src*='qrcode'], .qrcode img",
                timeout=8000
            )
            await qr.screenshot(path=qr_save_path)
            print(f"[视频号] ✓ 二维码已保存: {qr_save_path}")
        except Exception as e:
            await page.screenshot(path=qr_save_path)
            print(f"[视频号] 保存页面截图: {e}")

        # 等待扫码
        print("[视频号] 等待扫码（最多90秒）...")
        deadline = time.time() + 90
        logged_in = False
        while time.time() < deadline:
            await asyncio.sleep(2)
            if "platform" in page.url or "post" in page.url:
                logged_in = True
                break

        if logged_in:
            await ctx.storage_state(path=str(cookie_file))
            print(f"[视频号] ✓ 登录成功，Cookie 保存: {cookie_file}")
            await browser.close()
            return {"ok": True, "cookie_file": str(cookie_file)}
        else:
            await browser.close()
            return {"ok": False, "error": "扫码超时"}


# ── 发布图文笔记 ───────────────────────────────────────────────────────────────
async def _publish_note(content: str, image_paths: list[str],
                        tags: list[str], account: str) -> dict:
    """视频号图文笔记发布（异步）"""
    from patchright.async_api import async_playwright

    cookie_file = _cookie_path(account)
    if not cookie_file.exists():
        return {
            "ok": False,
            "error": f"Cookie 不存在: {cookie_file}，请先调用 login() 扫码"
        }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**_launch_kwargs())
        ctx  = await browser.new_context(storage_state=str(cookie_file))
        page = await ctx.new_page()
        result: dict = {"ok": False, "error": "未知错误"}

        try:
            print("[视频号] 打开发布页...")
            await page.goto(CHANNELS_POST_URL, timeout=30000)
            await asyncio.sleep(3)

            if "login" in page.url or "weixin.qq.com" not in page.url:
                return {"ok": False, "error": "Cookie 已失效，请重新扫码登录"}

            # 如果跳到首页，点「内容管理」→「图文」进入图文发布
            if "home" in page.url or page.url.rstrip("/") == CHANNELS_POST_URL.rstrip("/"):
                try:
                    # 点内容管理
                    await page.click('text=内容管理', timeout=5000)
                    await asyncio.sleep(1)
                    # 点图文
                    await page.click('.finder-ui-desktop-sub-menu__item:has-text("图文")',
                                      timeout=5000)
                    await asyncio.sleep(2)
                    # 找「发图文」按钮
                    await page.click('button:has-text("发图文"), a:has-text("发图文"), '
                                      'button:has-text("写图文"), .post-btn',
                                      timeout=5000)
                    await asyncio.sleep(2)
                    print("[视频号] ✓ 进入图文发布页")
                except Exception as e:
                    print(f"[视频号] 导航到图文页失败: {e}")
                    # 直接访问图文发布 URL
                    await page.goto(
                        "https://channels.weixin.qq.com/platform/post/create?postType=2",
                        timeout=20000
                    )
                    await asyncio.sleep(3)

            # 上传图片
            if image_paths:
                print(f"[视频号] 上传图片...")
                for frame in [page, *page.frames]:
                    try:
                        fi = await frame.wait_for_selector(
                            'input[type="file"][accept*="image"]',
                            timeout=3000
                        )
                        existing = [p for p in image_paths if os.path.exists(p)]
                        if existing:
                            await fi.set_input_files(existing)
                            await asyncio.sleep(3)
                            print(f"[视频号] ✓ 图片上传完成")
                        break
                    except Exception:
                        continue

            # 填写正文
            print("[视频号] 填写正文...")
            try:
                editor = await page.wait_for_selector(
                    '.input-editor, '
                    'div[data-placeholder], '
                    'div[contenteditable="true"], '
                    '.weui-desktop-editor, '
                    '.note-editor, textarea',
                    timeout=8000
                )
                await editor.click()
                await asyncio.sleep(0.5)
                await page.keyboard.press("Control+a")
                await page.keyboard.type(content[:2000], delay=15)
                print("[视频号] ✓ 正文填写完成")
            except Exception as e:
                print(f"[视频号] 正文输入失败: {e}")

            # 添加话题
            for tag in tags[:5]:
                tag_clean = tag.lstrip("#")
                try:
                    await page.keyboard.type(f" #{tag_clean}", delay=15)
                    await asyncio.sleep(0.5)
                    suggestion = page.locator(
                        '.topic-list li:first-child, '
                        '.weui-desktop-dropdown__item:first-child'
                    )
                    if await suggestion.count() > 0:
                        await suggestion.first.click()
                        await asyncio.sleep(0.3)
                except Exception:
                    pass

            await asyncio.sleep(1)

            # 点击发布
            print("[视频号] 点击发布...")
            try:
                btn = await page.wait_for_selector(
                    'button:has-text("发表"), button:has-text("发布")',
                    timeout=8000
                )
                await btn.click()
                await asyncio.sleep(3)
                print("[视频号] ✓ 发布完成")
                result = {"ok": True, "url": page.url}
            except Exception as e:
                await page.screenshot(path="/tmp/channels_fail.png")
                result = {"ok": False, "error": f"发布按钮点击失败: {e}"}

            # 保存更新后的 cookie
            await ctx.storage_state(path=str(cookie_file))

        except Exception as e:
            result = {"ok": False, "error": str(e)}
        finally:
            await browser.close()

    return result


def publish_channels_note(xhs: dict, images: dict,
                          account: str = ACCOUNT) -> dict:
    """
    同步入口：发布视频号图文笔记。
    复用 xhs 内容（同话题，格式略调整）。
    """
    if not xhs.get("ok"):
        return {"ok": False, "error": "写稿失败，跳过发布"}

    content = f"{xhs['title']}\n\n{xhs['content']}"
    tags    = xhs.get("tags", [])

    image_paths = []
    for key in ["xhs_image", "wechat_image"]:
        p = images.get(key)
        if p and os.path.exists(str(p)):
            image_paths.append(str(p))
            break

    return asyncio.run(_publish_note(content, image_paths, tags, account))
