# -*- coding: utf-8 -*-
"""
페이지마다 다른 og:image 카드를 만든다.

썸네일 한 장을 돌려쓰지 않는 이유:
네이버 웹문서 결과에 이 이미지가 그대로 썸네일로 붙는다. 그래서 로고가 아니라
**그 페이지에서 확인한 숫자**를 그려 넣는다. 검색 결과에서 답이 먼저 보이게 하려는 것.

    python ogimage.py           바뀐 것만 다시 그린다
    python ogimage.py --all     전부 다시 그린다

결과는 og/{슬러그}.png (1200x630). build.py 가 meta 태그를 붙인다.
"""

import hashlib
import io
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "og")
FORCE = "--all" in sys.argv

W, H = 1200, 630
PAD = 72

# 색 — 사이트와 같은 계열
BG = (252, 252, 249)
INK = (24, 24, 27)
MUTED = (113, 113, 122)
LINE = (228, 228, 231)
ACCENT = (24, 24, 27)

FONT_DIR = "C:/Windows/Fonts"


def font(size, bold=False):
    name = "malgunbd.ttf" if bold else "malgun.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def wrap(draw, text, f, maxw):
    """한국어는 단어 경계가 없어 글자 단위로 접는다."""
    lines, cur = [], ""
    for ch in text:
        t = cur + ch
        if draw.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)


def meta(name, t):
    m = re.search(r'<meta name="%s" content="(.*?)"' % name, t, re.S)
    return m.group(1).strip() if m else ""


def page_info(path, brand):
    t = read(path)
    title = RE_TITLE.search(t)
    title = title.group(1).strip() if title else ""
    for tail in (" | " + brand, " | AI요금제연구소"):
        if title.endswith(tail):
            title = title[: -len(tail)]
    # "제목 - 부제" 에서 부제를 따로 뽑는다
    head, sub = title, ""
    for sep in (" - ", " — "):
        if sep in title:
            head, sub = title.split(sep, 1)
            break
    return {
        "head": head.strip(),
        "sub": sub.strip(),
        "cat": meta("cat", t),
        "posted": meta("posted", t),
        "raw": t,
    }


def draw_card(info, brand):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 6], fill=ACCENT)
    foot_y = H - 118
    d.line([PAD, foot_y, W - PAD, foot_y], fill=LINE, width=1)

    maxw = W - PAD * 2
    cat = info["cat"] or "AI 도구"

    # 먼저 재본다 — 내용 높이를 알아야 세로 가운데로 놓을 수 있다
    fb = font(26, True)
    badge_h = 48 + 30

    for size in (62, 56, 50, 44):
        fh = font(size, True)
        lines = wrap(d, info["head"], fh, maxw)
        if len(lines) <= 3:
            break
    lines = lines[:3]
    line_h = int(size * 1.32)
    title_h = len(lines) * line_h

    sub_lines, sub_h, fs = [], 0, None
    if info["sub"]:
        for ssize in (34, 31, 28):
            fs = font(ssize)
            sub_lines = wrap(d, info["sub"], fs, maxw)
            if len(sub_lines) <= 2:
                break
        sub_lines = sub_lines[:2]
        sub_line_h = int(ssize * 1.42)
        sub_h = 18 + len(sub_lines) * sub_line_h

    block = badge_h + title_h + sub_h
    y = max(PAD + 6, (foot_y - block) // 2)

    # 분류 배지
    tw = d.textlength(cat, font=fb)
    d.rounded_rectangle([PAD, y, PAD + tw + 34, y + 48], radius=10, fill=ACCENT)
    d.text((PAD + 17, y + 9), cat, font=fb, fill=(255, 255, 255))
    y += badge_h

    # 제목
    for ln in lines:
        d.text((PAD, y), ln, font=fh, fill=INK)
        y += line_h

    # 부제 — 이 페이지의 답
    if sub_lines:
        y += 18
        for ln in sub_lines:
            d.text((PAD, y), ln, font=fs, fill=MUTED)
            y += sub_line_h

    # 바닥
    d.text((PAD, H - 88), brand, font=font(27, True), fill=INK)
    if info["posted"]:
        yy, mm, dd = info["posted"].split("-")
        stamp = "%s년 %d월 %d일 확인" % (yy, int(mm), int(dd))
        fs2 = font(25)
        d.text((W - PAD - d.textlength(stamp, font=fs2), H - 86), stamp, font=fs2, fill=MUTED)

    return img


def slug_of(url):
    s = url.strip("/").replace("/", "-") or "index"
    return re.sub(r"[^a-zA-Z0-9_-]", "-", s)


def url_of(path):
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def html_files():
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "assets", "og", "__pycache__")]
        for n in files:
            if n.endswith(".html"):
                out.append(os.path.join(base, n))
    return sorted(out)


def main():
    cfg = json.loads(read(os.path.join(ROOT, "site.json")))
    brand = cfg["site"]["name"]
    os.makedirs(OUT, exist_ok=True)

    made = skipped = 0
    for path in html_files():
        url = url_of(path)
        if url == "/404.html":
            continue
        info = page_info(path, brand)
        if not info["head"]:
            continue

        slug = slug_of(url)
        dest = os.path.join(OUT, slug + ".png")

        # 제목·부제·날짜가 그대로면 다시 그리지 않는다
        sig = hashlib.md5(
            ("|".join([info["head"], info["sub"], info["cat"], info["posted"]])).encode("utf-8")
        ).hexdigest()[:12]
        sigfile = os.path.join(OUT, "." + slug + ".sig")
        if not FORCE and os.path.exists(dest) and os.path.exists(sigfile):
            if read(sigfile).strip() == sig:
                skipped += 1
                continue

        draw_card(info, brand).save(dest, "PNG", optimize=True)
        with io.open(sigfile, "w", encoding="utf-8") as f:
            f.write(sig)
        made += 1

    print("og 카드: 새로 %d장 · 그대로 %d장" % (made, skipped))
    total = len([f for f in os.listdir(OUT) if f.endswith(".png")])
    size = sum(
        os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".png")
    )
    print("총 %d장 · %.1f MB" % (total, size / 1024 / 1024))


if __name__ == "__main__":
    main()
