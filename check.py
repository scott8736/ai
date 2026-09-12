# -*- coding: utf-8 -*-
"""
배포 전 점검. 고치지는 않고 알려만 준다.

  - 내부 링크가 실제 파일로 가는가
  - JSON-LD 가 문법에 맞는가
  - 페이지마다 title / description / canonical 이 있는가
  - 제목·설명이 다른 페이지와 겹치지 않는가

    python check.py
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://ai.howtopackbook.com"

problems = []


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def html_files():
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "assets", "__pycache__")]
        for n in files:
            if n.endswith(".html"):
                out.append(os.path.join(base, n))
    return sorted(out)


def url_of(p):
    rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def exists(url):
    """사이트 URL 이 실제 파일로 이어지는가"""
    u = url.split("#")[0].split("?")[0]
    if not u.startswith("/"):
        return True
    if u == "/":
        return True
    seg = u.strip("/").split("/")
    cands = [
        os.path.join(ROOT, *seg, "index.html"),
        os.path.join(ROOT, *seg),
        os.path.join(ROOT, *seg[:-1], seg[-1] + ".html"),
    ]
    return any(os.path.isfile(c) for c in cands)


titles, descs = {}, {}

for path in html_files():
    url = url_of(path)
    t = read(path)

    # JSON-LD
    for i, block in enumerate(
        re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    ):
        try:
            json.loads(block)
        except Exception as e:
            problems.append("%s  JSON-LD %d번째 문법 오류: %s" % (url, i + 1, e))

    # 필수 태그
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    if not m or not m.group(1).strip():
        problems.append("%s  title 없음" % url)
    else:
        titles.setdefault(m.group(1).strip(), []).append(url)

    m = re.search(r'<meta name="description" content="(.*?)"', t, re.S)
    if not m or not m.group(1).strip():
        problems.append("%s  description 없음" % url)
    else:
        descs.setdefault(m.group(1).strip(), []).append(url)

    m = re.search(r'<link rel="canonical" href="(.*?)"', t)
    if not m:
        # 404 는 정본 주소가 없는 게 맞다
        if url != "/404.html":
            problems.append("%s  canonical 없음" % url)
    else:
        # /privacy.html 의 정본을 /privacy 로 두는 것은 의도된 설정이다
        ok = (BASE + url, BASE + url[:-5] if url.endswith(".html") else None)
        if m.group(1) not in ok:
            problems.append("%s  canonical 불일치 -> %s" % (url, m.group(1)))

    if '<html lang="ko">' not in t:
        problems.append("%s  html lang=ko 아님" % url)

    # 내부 링크
    for href in re.findall(r'href="(/[^"]*)"', t):
        if not exists(href):
            problems.append("%s  깨진 링크 -> %s" % (url, href))

for group, label in ((titles, "제목"), (descs, "설명")):
    for text, urls in group.items():
        if len(urls) > 1:
            problems.append("%s 중복: %s" % (label, " · ".join(urls)))

# sitemap 의 주소가 실재하는가
sm = os.path.join(ROOT, "sitemap.xml")
if os.path.exists(sm):
    for loc in re.findall(r"<loc>(.*?)</loc>", read(sm)):
        u = loc.replace(BASE, "")
        if not exists(u):
            problems.append("sitemap 에 없는 주소: %s" % u)

if problems:
    print("문제 %d건" % len(problems))
    for p in problems:
        print("  - " + p)
    sys.exit(1)

print("이상 없음 · HTML %d개" % len(html_files()))
