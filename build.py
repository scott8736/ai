# -*- coding: utf-8 -*-
"""
ai.howtopackbook.com 빌더

site.json 하나를 고치고 이걸 돌리면 아래가 전부 다시 만들어집니다.

  - 모든 HTML 의 상단 메뉴 (데스크톱 + 모바일)
  - 모든 HTML 의 푸터 링크
  - 브랜드 이름 표기
  - 카테고리 페이지  /ai/ /api/ /video/ /image/ /software/ ...
  - 블로그 목록 /blog/ 의 카드와 글 편수
  - sitemap.xml · rss.xml · robots.txt

본문은 건드리지 않습니다. 메뉴/푸터/목록은 HTML 안에 심어 둔 주석 마커
<!--NAV--> ... <!--/NAV--> 사이만 갈아끼웁니다. 마커가 없는 파일은
첫 실행 때 기존 덩어리를 찾아 마커로 감싸 줍니다.

글 하나를 추가하는 법
  1) HTML 을 만든다. head 에 cat / kicker / posted 메타 세 줄을 넣는다
     <meta name="cat" content="제미나이">
     <meta name="kicker" content="발급 방법">
     <meta name="posted" content="2026-09-12">
  2) site.json 의 해당 카테고리 pages 에 URL 을 한 줄 추가
  3) python build.py

    python build.py          전부 다시 만든다
    python build.py --check  뭘 바꿀지만 보여주고 쓰지는 않는다
"""

import io
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))

DRY = "--check" in sys.argv

# 마커 -------------------------------------------------------------------

NAV_A, NAV_B = "<!--NAV-->", "<!--/NAV-->"
MNAV_A, MNAV_B = "<!--MNAV-->", "<!--/MNAV-->"
FOOT_A, FOOT_B = "<!--FOOTLINKS-->", "<!--/FOOTLINKS-->"
LIST_A, LIST_B = "<!--POSTLIST-->", "<!--/POSTLIST-->"
TOC_A, TOC_B = "<!--TOC-->", "<!--/TOC-->"
SHARE_A, SHARE_B = "<!--SHARE-->", "<!--/SHARE-->"

OLD_NAV = re.compile(r'<nav class="nav"[^>]*>.*?</nav>', re.S)
OLD_MNAV = re.compile(r'<div class="wrap mobile-nav__list">.*?</div>\s*(?=</div>)', re.S)
OLD_FOOT = re.compile(r'<div class="link-cols">.*?</div>\s*</div>\s*(?=</div>)', re.S)
OLD_LIST = re.compile(r'<div class="post-list">.*?</div>\s*(?=</section>)', re.S)

BLOCK = {
    "nav": (NAV_A, NAV_B),
    "mnav": (MNAV_A, MNAV_B),
    "foot": (FOOT_A, FOOT_B),
    "list": (LIST_A, LIST_B),
}


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    if DRY:
        return
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def html_files():
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "assets", "__pycache__")]
        for name in files:
            if name.endswith(".html"):
                out.append(os.path.join(base, name))
    return sorted(out)


def url_of(path):
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def path_of(url):
    u = url.strip("/")
    if not u:
        return os.path.join(ROOT, "index.html")
    if url.endswith("/"):
        return os.path.join(ROOT, *u.split("/"), "index.html")
    p = os.path.join(ROOT, *u.split("/"))
    return p if p.endswith(".html") else p + ".html"


# 페이지 메타 ------------------------------------------------------------

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)


def _meta(name, text):
    m = re.search(r'<meta name="%s" content="(.*?)"' % name, text, re.S)
    return m.group(1).strip() if m else ""


def meta_of(path, brand):
    """제목·설명·분류를 HTML 에서 직접 읽는다. 한 곳에만 적게 하려는 것."""
    if not os.path.exists(path):
        return None
    t = read(path)
    title = RE_TITLE.search(t)
    title = title.group(1).strip() if title else ""
    for tail in (" | " + brand, " | AI요금제연구소"):
        if title.endswith(tail):
            title = title[: -len(tail)]
    mod = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"', t)
    pub = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', t)
    posted = _meta("posted", t)
    return {
        "title": title,
        "desc": _meta("description", t),
        "cat": _meta("cat", t),
        "kicker": _meta("kicker", t),
        "posted": posted,
        "mod": posted or (mod.group(1) if mod else (pub.group(1) if pub else None)),
    }


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def ko_date(iso):
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return "%s년 %d월 %d일" % (y, int(m), int(d))


# 조각 -------------------------------------------------------------------


def live_categories(cfg):
    """글이 있고 menu 가 켜진 카테고리만. 빈 '준비중' 메뉴를 안 내보내려는 것."""
    return [c for c in cfg["categories"] if c.get("menu", True) and c["pages"]]


def build_nav(cfg, here):
    items = [("/" + c["slug"] + "/", c["label"]) for c in live_categories(cfg)]
    items += [(x["href"], x["label"]) for x in cfg.get("nav_extra", [])]
    out = ['<nav class="nav" aria-label="주요 메뉴">']
    for href, label in items:
        cur = ' aria-current="page"' if href == here else ""
        out.append('      <a href="%s"%s>%s</a>' % (href, cur, label))
    out.append("    </nav>")
    return "\n".join(out)


def build_mnav(cfg, here):
    items = [("/", "전체 비교")]
    items += [("/" + c["slug"] + "/", c["label"]) for c in live_categories(cfg)]
    items += [(x["href"], x["label"]) for x in cfg.get("nav_extra", [])]
    items += [("/discount/", "할인 모음")]
    out = ['<div class="wrap mobile-nav__list">']
    for href, label in items:
        cur = ' aria-current="page"' if href == here else ""
        out.append('      <a href="%s"%s>%s</a>' % (href, cur, label))
    out.append("    </div>")
    return "\n".join(out)


def build_footer(cfg):
    out = ['<div class="link-cols">']
    for col in cfg["footer_cols"]:
        out.append('        <div class="link-col">')
        out.append('          <h2 class="link-col__title">%s</h2>' % col["title"])
        out.append("          <ul>")
        if col.get("auto") == "categories":
            links = [
                {"href": "/" + c["slug"] + "/", "label": c["label"]}
                for c in live_categories(cfg)
            ]
        else:
            links = col["links"]
        for l in links:
            ext = ' target="_blank" rel="noopener"' if l.get("ext") else ""
            out.append(
                '            <li><a href="%s"%s>%s</a></li>' % (l["href"], ext, l["label"])
            )
        out.append("          </ul>")
        out.append("        </div>")
    out.append("      </div>")
    return "\n".join(out)


def card(url, m, indent="      "):
    bits = [b for b in (m.get("cat"), m.get("kicker"), ko_date(m.get("posted"))) if b]
    out = ['%s<a class="post-card" href="%s">' % (indent, url)]
    out.append('%s  <div class="post-card__meta">' % indent)
    if bits:
        out.append('%s    <span class="post-card__cat">%s</span>' % (indent, bits[0]))
        for b in bits[1:]:
            out.append("%s    <span>%s</span>" % (indent, b))
    out.append("%s  </div>" % indent)
    out.append('%s  <h2 class="post-card__title">%s</h2>' % (indent, m["title"]))
    out.append('%s  <p class="post-card__desc">%s</p>' % (indent, m["desc"]))
    out.append("%s</a>" % indent)
    return "\n".join(out)


def listed_pages(metas):
    """cat/kicker 를 단 페이지 = 목록에 나갈 글. 최근순."""
    rows = [(u, m) for u, m in metas.items() if m and m.get("cat") and m.get("posted")]
    rows.sort(key=lambda x: x[1]["posted"], reverse=True)
    return rows


def build_postlist(rows):
    out = ['<div class="post-list">', ""]
    for url, m in rows:
        out.append(card(url, m))
        out.append("")
    out.append("    </div>")
    return "\n".join(out)


# 카테고리 페이지 --------------------------------------------------------

CAT_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{title} | {brand}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{base}/{slug}/">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#fcfcf9">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{brand}">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="{base}/{slug}/">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">

<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2318181b'/%3E%3Ctext x='16' y='22' font-family='Helvetica,Arial,sans-serif' font-size='14' font-weight='bold' fill='white' text-anchor='middle'%3EAI%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="/assets/site.css">
<link rel="alternate" type="application/rss+xml" title="{brand}" href="{base}/rss.xml">

<script type="application/ld+json">
{schema}
</script>

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8646375689901020" crossorigin="anonymous"></script>
</head>
<body>

<header class="site-header">
  <div class="wrap site-header__bar">
    <a class="brand" href="/">
      <span class="brand__mark">AI</span>
      <span class="brand__name">{alt} <span class="brand__sep">/</span> {brand}</span>
    </a>
    {NAV_A}
    {NAV_B}
    <div class="header__right">
      <button class="menu-btn" type="button" id="menu-btn" aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobile-nav">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </div>
  <div class="mobile-nav" id="mobile-nav" hidden>
    {MNAV_A}
    {MNAV_B}
  </div>
</header>

<main>
  <div class="wrap">
    <nav class="crumb" aria-label="위치">
      <a href="/">AI 도구 비교</a> <span class="crumb__sep">›</span> <span>{label}</span>
    </nav>
  </div>

  <section class="wrap page-hero">
    <div class="eyebrow">
      <span class="eyebrow__mark" style="background:#18181b" aria-hidden="true">{mark}</span>
      <span class="eyebrow__label" style="color:#52525b">{slugupper}</span>
    </div>
    <h1>{h1}</h1>
    <p class="page-hero__lead">{desc}</p>
    <div class="page-hero__meta">
      <span class="chip">✓ 공식 페이지 직접 확인</span>
      <span class="chip">✓ 확인 날짜 명시</span>
      <span class="chip">✓ 판매·중개 없음</span>
    </div>
  </section>

  <section class="wrap" style="padding-top:8px;padding-bottom:40px">

    <div class="kicker-row">
      <span class="kicker-tag">{label}</span>
      <span class="kicker-date">{count}편</span>
    </div>

    {LIST_A}
    {LIST_B}

  </section>
</main>

<footer class="site-footer">
  <div class="wrap site-footer__inner">
    <div class="site-footer__top">
      <div class="site-footer__about">
        <div class="site-footer__brand">
          <span class="site-footer__mark">AI</span>
          <span class="site-footer__name">{alt} / {brand}</span>
        </div>
        <p class="disclaimer">ai.howtopackbook.com은 여기 소개하는 어떤 회사와도 제휴관계가 없습니다. 모든 상표는 각 소유자 소유입니다. 이 사이트는 구독을 판매하지도 중개하지도 않으며, 게시된 정보는 참고용이므로 결제 전 공식 페이지를 확인하세요.</p>
      </div>
      {FOOT_A}
      {FOOT_B}
    </div>
    <div class="site-footer__bottom">
      <span class="site-footer__copy">Copyright 2026 howtopackbook.com. All rights reserved.</span>
      <span class="site-footer__made">Made for Korean AI users · Light, fast, no tracking beyond AdSense</span>
    </div>
  </div>
</footer>

<script src="/assets/site.js" defer></script>
</body>
</html>
"""


def build_category_pages(cfg, metas):
    base = cfg["site"]["base"]
    made = []
    for c in cfg["categories"]:
        if not c["pages"]:
            continue
        rows = [(u, metas.get(u)) for u in c["pages"] if metas.get(u)]
        rows.sort(key=lambda x: (x[1].get("posted") or x[1].get("mod") or ""), reverse=True)

        items = [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": base + u,
                "name": m["title"],
            }
            for i, (u, m) in enumerate(rows)
        ]
        schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "@id": "%s/%s/#webpage" % (base, c["slug"]),
                "url": "%s/%s/" % (base, c["slug"]),
                "name": c["title"],
                "description": c["desc"],
                "inLanguage": "ko-KR",
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(items),
                    "itemListElement": items,
                },
            },
            ensure_ascii=False,
            indent=2,
        )

        html = CAT_PAGE.format(
            title=esc(c["title"]),
            desc=esc(c["desc"]),
            h1=esc(c["title"].split(" - ")[0]),
            label=esc(c["label"]),
            slug=c["slug"],
            slugupper=c["slug"].upper(),
            mark=c["label"][0],
            count=len(rows),
            base=base,
            brand=esc(cfg["site"]["name"]),
            alt=esc(cfg["site"]["alt"]),
            schema=schema,
            NAV_A=NAV_A, NAV_B=NAV_B,
            MNAV_A=MNAV_A, MNAV_B=MNAV_B,
            FOOT_A=FOOT_A, FOOT_B=FOOT_B,
            LIST_A=LIST_A + "\n    " + build_postlist(rows) + "\n    ",
            LIST_B=LIST_B,
        )
        path = os.path.join(ROOT, c["slug"], "index.html")
        write(path, html)
        made.append("/%s/ (%d편)" % (c["slug"], len(rows)))
    return made


# og:image · 목차 · 공유 ---------------------------------------------------


def og_slug(url):
    s = url.strip("/").replace("/", "-") or "index"
    return re.sub(r"[^a-zA-Z0-9_-]", "-", s)


def inject_og(text, url, cfg):
    """페이지마다 다른 카드를 물린다. 네이버 결과 썸네일로 그대로 쓰인다."""
    if url == "/404.html":
        return text
    slug = og_slug(url)
    if not os.path.exists(os.path.join(ROOT, "og", slug + ".png")):
        return text
    src = "%s/og/%s.png" % (cfg["site"]["base"], slug)

    block = "\n".join([
        '<meta property="og:image" content="%s">' % src,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:image" content="%s">' % src,
    ])

    if 'property="og:image"' in text:
        # 이미 있으면 통째로 갈아끼운다
        text = re.sub(
            r'<meta property="og:image"[^>]*>\s*'
            r'(?:<meta property="og:image:width"[^>]*>\s*)?'
            r'(?:<meta property="og:image:height"[^>]*>\s*)?'
            r'(?:<meta name="twitter:image"[^>]*>)?',
            lambda _: block,
            text,
            count=1,
        )
    else:
        m = re.search(r'<meta property="og:url"[^>]*>', text)
        if not m:
            return text
        text = text[: m.end()] + "\n" + block + text[m.end():]

    # 이미지가 붙었으니 큰 카드로
    return text.replace(
        '<meta name="twitter:card" content="summary">',
        '<meta name="twitter:card" content="summary_large_image">',
    )


RE_H2 = re.compile(r"<h2(?![^>]*\bid=)>(.*?)</h2>", re.S)


def _anchor_id(label, used):
    plain = re.sub(r"<[^>]+>", "", label)
    base = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", plain).strip("-")[:40] or "sec"
    slug, n = base, 2
    while slug in used:
        slug, n = "%s-%d" % (base, n), n + 1
    used.add(slug)
    return slug


def add_toc(text):
    """소제목이 5개를 넘으면 목차를 넣는다.

    첫 번째 절(대개 '한 줄 요약') 뒤에 놓는다. 지식스니펫은 첫 문단에서
    답을 찾으므로 목차를 답 위에 두면 손해다."""
    m = re.search(r'<div class="prose">(.*?)\n    </div>', text, re.S)
    if not m:
        return text
    prose = m.group(1)

    used, items = set(), []

    def tag(mm):
        label = mm.group(1).strip()
        sid = _anchor_id(label, used)
        items.append((sid, re.sub(r"<[^>]+>", "", label)))
        return '<h2 id="%s">%s</h2>' % (sid, label)

    prose = RE_H2.sub(tag, prose)
    if len(items) < 5:
        return text

    links = "\n".join(
        '          <li><a href="#%s">%s</a></li>' % (sid, lb) for sid, lb in items
    )
    toc = "\n".join([
        TOC_A,
        '      <nav class="toc" aria-label="목차">',
        '        <div class="toc__title">이 글의 순서</div>',
        '        <ol class="toc__list">',
        links,
        "        </ol>",
        "      </nav>",
        "      " + TOC_B,
    ])

    if TOC_A in prose:
        prose = re.sub(
            re.escape(TOC_A) + r".*?" + re.escape(TOC_B),
            lambda _: toc,
            prose,
            count=1,
            flags=re.S,
        )
    else:
        heads = list(re.finditer(r'<h2 id="', prose))
        if len(heads) < 2:
            return text
        cut = heads[1].start()
        prose = prose[:cut] + toc + "\n\n      " + prose[cut:]

    return text[: m.start(1)] + prose + text[m.end(1):]


def build_share(url, cfg, title):
    """카카오톡 공유는 앱 키가 있어야 해서 뺐다. 링크 복사·X·네이버만."""
    import urllib.parse as up

    full = cfg["site"]["base"] + url
    enc_u = up.quote(full, safe="")
    enc_t = up.quote(title, safe="")
    return "\n".join([
        '<div class="share">',
        '      <span class="share__label">공유</span>',
        '      <button class="share__btn" type="button" data-copy="%s">링크 복사</button>' % full,
        '      <a class="share__btn" href="https://twitter.com/intent/tweet?url=%s&amp;text=%s" target="_blank" rel="noopener">X</a>'
        % (enc_u, enc_t),
        '      <a class="share__btn" href="https://share.naver.com/web/shareView?url=%s&amp;title=%s" target="_blank" rel="noopener">네이버</a>'
        % (enc_u, enc_t),
        "    </div>",
    ])


def add_share(text, url, cfg, title):
    if 'class="prose"' not in text:
        return text
    payload = build_share(url, cfg, title)

    if SHARE_A in text and SHARE_B in text:
        return re.sub(
            re.escape(SHARE_A) + r".*?" + re.escape(SHARE_B),
            lambda _: SHARE_A + "\n    " + payload + "\n    " + SHARE_B,
            text,
            count=1,
            flags=re.S,
        )

    m = re.search(r"</div>\n  </section>\n", text)
    if not m:
        return text
    blk = "".join([
        '  <div class="wrap">\n    ',
        SHARE_A,
        "\n    ",
        payload,
        "\n    ",
        SHARE_B,
        "\n  </div>\n\n",
    ])
    return text[: m.end()] + blk + text[m.end():]


def add_breadcrumb(text, url, cfg, title):
    """카테고리·정책 페이지에 빵부스러기 스키마. 구현 비용이 거의 없다."""
    if '"BreadcrumbList"' in text or url in ("/", "/404.html"):
        return text
    if not title:
        return text
    base = cfg["site"]["base"]
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "AI 도구 비교", "item": base + "/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": base + url},
        ],
    }
    tag = '<script type="application/ld+json">\n%s\n</script>\n\n' % json.dumps(
        data, ensure_ascii=False, indent=2
    )
    # 애드센스가 없는 정책 페이지도 있으므로 </head> 를 기준으로 삼는다
    m = re.search(r'<script async src="https://pagead2', text) or re.search(r"</head>", text)
    if not m:
        return text
    return text[: m.start()] + tag + text[m.start():]


# 마커 주입 --------------------------------------------------------------


def splice(text, kind, payload, old_re):
    a, b = BLOCK[kind]
    if a in text and b in text:
        return (
            re.sub(
                re.escape(a) + r".*?" + re.escape(b),
                lambda m: a + "\n    " + payload + "\n    " + b,
                text,
                count=1,
                flags=re.S,
            ),
            "갱신",
        )
    m = old_re.search(text)
    if not m:
        return text, "없음"
    return (
        text[: m.start()] + a + "\n    " + payload + "\n    " + b + text[m.end():],
        "마커생성",
    )


def rebrand(text, cfg):
    name = cfg["site"]["name"]
    alt = cfg["site"]["alt"]
    text = text.replace(
        'AI Pack <span class="brand__sep">/</span> AI요금제연구소',
        '%s <span class="brand__sep">/</span> %s' % (alt, name),
    )
    text = text.replace("AI Pack / AI요금제연구소", "%s / %s" % (alt, name))
    text = text.replace("AI요금제연구소", name)
    return text


# sitemap / rss / robots -------------------------------------------------


def build_sitemap(cfg, pages):
    base = cfg["site"]["base"]
    ex = set(cfg.get("sitemap_exclude", []))
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    today = datetime.now(KST).strftime("%Y-%m-%d")
    for url, m in pages:
        if url in ex:
            continue
        prio = "1.0" if url == "/" else ("0.8" if url.count("/") <= 2 else "0.6")
        rows += [
            "  <url>",
            "    <loc>%s%s</loc>" % (base, url),
            "    <lastmod>%s</lastmod>" % ((m or {}).get("mod") or today),
            "    <priority>%s</priority>" % prio,
            "  </url>",
        ]
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def build_rss(cfg, rows):
    """최근 수정순 25건만. 전부 밀어 넣으면 뭐가 새것인지 사라진다."""
    base = cfg["site"]["base"]
    site = cfg["site"]
    now = datetime.now(KST).strftime("%a, %d %b %Y %H:%M:%S +0900")
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        "  <title>%s</title>" % esc(site["name"]),
        "  <link>%s/</link>" % base,
        "  <description>%s</description>" % esc(site["desc"]),
        "  <language>ko</language>",
        "  <lastBuildDate>%s</lastBuildDate>" % now,
        '  <atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>' % base,
    ]
    for url, m in rows[:25]:
        d = m.get("posted") or m.get("mod")
        if d:
            pub = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=KST).strftime(
                "%a, %d %b %Y 09:00:00 +0900"
            )
        else:
            pub = now
        out += [
            "  <item>",
            "    <title>%s</title>" % esc(m.get("title", "")),
            "    <link>%s%s</link>" % (base, url),
            '    <guid isPermaLink="true">%s%s</guid>' % (base, url),
            "    <pubDate>%s</pubDate>" % pub,
            "    <description>%s</description>" % esc(m.get("desc", "")),
            "  </item>",
        ]
    out += ["</channel>", "</rss>"]
    return "\n".join(out) + "\n"


def build_robots(cfg):
    """네이버 Yeti 는 이름 붙은 그룹이 없으면 '수집 미확인' 으로 잡는다.
    이름 붙은 그룹은 와일드카드를 대체하므로 규칙을 그 안에 다시 적는다."""
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "User-agent: Yeti\n"
        "Allow: /\n"
        "\n"
        "Sitemap: %s/sitemap.xml\n" % cfg["site"]["base"]
    )


# 메인 -------------------------------------------------------------------


def main():
    cfg = json.loads(read(os.path.join(ROOT, "site.json")))
    brand = cfg["site"]["name"]

    metas = {}
    for p in html_files():
        metas[url_of(p)] = meta_of(p, brand)

    made = build_category_pages(cfg, metas)
    for s in made:
        print("카테고리 %s" % s)

    rows = listed_pages(metas)
    postlist = build_postlist(rows)
    footer = build_footer(cfg)
    stats = {"갱신": 0, "마커생성": 0, "없음": 0}
    tocs = [0]

    for path in html_files():
        here = url_of(path)
        text = orig = read(path)

        text = rebrand(text, cfg)
        text, s1 = splice(text, "nav", build_nav(cfg, here), OLD_NAV)
        text, _ = splice(text, "mnav", build_mnav(cfg, here), OLD_MNAV)
        text, _ = splice(text, "foot", footer, OLD_FOOT)
        stats[s1] += 1

        m = metas.get(here) or {}
        short = (m.get("title") or "").split(" - ")[0].split(" — ")[0]
        text = inject_og(text, here, cfg)
        text = add_breadcrumb(text, here, cfg, short)
        text = add_toc(text)
        if TOC_A in text:
            tocs[0] += 1
        text = add_share(text, here, cfg, short)

        # 블로그 목록은 /blog/ 만. 카테고리 페이지는 자기 목록을 이미 갖고 있다
        if here == "/blog/":
            text, _ = splice(text, "list", postlist, OLD_LIST)
            text = re.sub(
                r'(<span class="kicker-date">)\d+편[^<]*(</span>)',
                lambda m: "%s%d편 · 최근 갱신 %s%s"
                % (m.group(1), len(rows), ko_date(rows[0][1]["posted"]), m.group(2)),
                text,
            )

        if text != orig:
            write(path, text)

    print("메뉴 주입: 갱신 %(갱신)d · 마커생성 %(마커생성)d · 못찾음 %(없음)d" % stats)
    print("목록 글 %d편 · 목차 %d개" % (len(rows), tocs[0]))

    pages = [(url_of(p), meta_of(p, brand)) for p in html_files()]
    write(os.path.join(ROOT, "sitemap.xml"), build_sitemap(cfg, pages))
    write(os.path.join(ROOT, "rss.xml"), build_rss(cfg, rows))
    write(os.path.join(ROOT, "robots.txt"), build_robots(cfg))
    print("sitemap %d건 · rss %d건 · robots 갱신" % (len(pages), min(len(rows), 25)))

    if DRY:
        print("\n--check 라서 아무것도 쓰지 않았습니다.")


if __name__ == "__main__":
    main()
