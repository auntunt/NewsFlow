#!/usr/bin/env python3
"""
NewsFlow 邮件发送工具

支持：
- 发送三份稿件 HTML 邮件
- 附带配图附件（如有）

用法：
  python send_email.py                          # 发最新 run
  python send_email.py --run-id 20260716_083018 # 发指定 run
"""

import argparse
import json
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── SMTP 配置 ─────────────────────────────────────────────
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SENDER    = "342873853@qq.com"
PASSWORD  = "vockqkqtavhabhhj"
RECIPIENT = "342873853@qq.com"


def text_to_html(text: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(
        f'<p style="margin:0 0 1em 0;line-height:1.8">'
        f'{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )


def build_html(data: dict, image_cids: dict) -> str:
    wechat = data.get("wechat", {})
    xhs    = data.get("xhs", {})
    video  = data.get("video_script", {})
    topic  = data.get("topic", {})

    # 配图 img 标签（如果有 cid 就内嵌，否则不显示）
    def img_tag(key, alt):
        cid = image_cids.get(key)
        if cid:
            return f'<img src="cid:{cid}" alt="{alt}" style="max-width:100%;border-radius:8px;margin:12px 0">'
        return ""

    # 分段时长表格
    segments_html = ""
    for seg in video.get("segments", []):
        segments_html += (
            f'<tr><td style="padding:4px 12px;color:#666">{seg.get("note","")}</td>'
            f'<td style="padding:4px 12px">{seg.get("duration_s",0)}秒</td>'
            f'<td style="padding:4px 12px">{seg.get("text","")[:60]}...</td></tr>'
        )

    # 话题标签
    xhs_tags = " ".join(f'<span style="background:#f0f0f0;padding:2px 8px;border-radius:12px;font-size:13px;margin:2px">#{t}</span>'
                        for t in xhs.get("tags", []))

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;
        max-width:700px;margin:0 auto;padding:20px;color:#333;background:#f9f9f9}}
  .section{{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;
             box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;
           font-weight:600;color:#fff;margin-bottom:12px}}
  .wechat-badge{{background:#07c160}}
  .xhs-badge{{background:#ff2442}}
  .video-badge{{background:#5e60ce}}
  h1{{font-size:20px;margin:0 0 16px;line-height:1.4;color:#111}}
  h2{{font-size:16px;margin:0 0 12px;color:#111}}
  .source{{font-size:13px;color:#999;margin-bottom:16px}}
  table{{border-collapse:collapse;width:100%;font-size:14px}}
  th{{text-align:left;padding:6px 12px;background:#f5f5f5;color:#666;font-weight:500}}
  .cover{{font-size:28px;font-weight:700;letter-spacing:2px;
           padding:16px;background:#111;color:#fff;border-radius:8px;text-align:center}}
</style>
</head>
<body>

<div style="text-align:center;padding:16px 0 24px">
  <div style="font-size:24px;font-weight:700">📰 NewsFlow 今日稿件</div>
  <div style="color:#999;font-size:14px;margin-top:4px">{today}</div>
  <div style="margin-top:8px;padding:8px 16px;background:#fff;border-radius:8px;display:inline-block;font-size:14px">
    选题：<strong>{topic.get("title","")}</strong>
    &nbsp;|&nbsp; 来源：{topic.get("source","")}
    &nbsp;|&nbsp; 评分：{topic.get("score","?")}
  </div>
</div>

<!-- 公众号 -->
<div class="section">
  <span class="badge wechat-badge">微信公众号</span>
  {img_tag("wechat", "公众号封面")}
  <h1>{wechat.get("title","")}</h1>
  <div class="source">摘要：{wechat.get("summary","")}</div>
  {text_to_html(wechat.get("content",""))}
  <div style="margin-top:16px;font-size:13px;color:#999">
    标签：{" ".join(wechat.get("tags",[]))}
  </div>
</div>

<!-- 小红书 -->
<div class="section">
  <span class="badge xhs-badge">小红书</span>
  {img_tag("xhs", "小红书配图")}
  <h2>{xhs.get("title","")}</h2>
  {text_to_html(xhs.get("content",""))}
  <div style="margin-top:12px">{xhs_tags}</div>
</div>

<!-- 视频脚本 -->
<div class="section">
  <span class="badge video-badge">口播视频脚本</span>
  {img_tag("video", "视频封面")}
  <div class="cover">{video.get("cover_text","")}</div>
  <div style="margin-top:16px;font-size:14px;color:#555;line-height:1.9;
               white-space:pre-wrap">{video.get("script","")}</div>
  <div style="margin-top:16px">
    <table>
      <tr><th>片段</th><th>时长</th><th>内容预览</th></tr>
      {segments_html}
    </table>
  </div>
  <div style="margin-top:8px;font-size:13px;color:#999">
    话题：{" ".join(video.get("hashtags",[]))}
  </div>
</div>

</body></html>"""


def send(content_json_path: str):
    with open(content_json_path, encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    topic_title = data.get("topic", {}).get("title", "")[:30]

    msg = MIMEMultipart("related")
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg["Subject"] = f"NewsFlow 今日稿件 {today}｜{topic_title}"

    # ── 处理配图附件 ───────────────────────────────────────
    images_data = data.get("images", {})
    image_cids  = {}
    image_map   = {
        "wechat": images_data.get("wechat_image"),
        "xhs":    images_data.get("xhs_image"),
        "video":  images_data.get("video_image"),
    }

    for key, path in image_map.items():
        if path and os.path.exists(path):
            cid = f"img_{key}"
            image_cids[key] = cid
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header(
                    "Content-Disposition", "inline",
                    filename=os.path.basename(path)
                )
                msg.attach(img)
            print(f"  [邮件] 附加配图: {key} → {path}")
        else:
            print(f"  [邮件] 无配图: {key}（跳过）")

    # ── HTML 正文 ──────────────────────────────────────────
    html_body = build_html(data, image_cids)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # ── 发送 ───────────────────────────────────────────────
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())

    print(f"✓ 邮件已发送至 {RECIPIENT}")
    print(f"  主题：{msg['Subject']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", help="指定 run id，默认取最新")
    args = parser.parse_args()

    data_root = Path("data/runs")
    if args.run_id:
        json_path = data_root / args.run_id / "phase3" / "content.json"
    else:
        runs = sorted(data_root.iterdir(), reverse=True)
        json_path = None
        for run_dir in runs:
            candidate = run_dir / "phase3" / "content.json"
            if candidate.exists():
                json_path = candidate
                break

    if not json_path or not json_path.exists():
        print("找不到 phase3/content.json，请先执行 newsflow publish --dry-run")
        return

    print(f"[邮件] 发送稿件：{json_path}")
    send(str(json_path))


if __name__ == "__main__":
    main()
