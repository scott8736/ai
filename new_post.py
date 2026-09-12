# -*- coding: utf-8 -*-
"""
새 글 뼈대 만들기. 머리말(head)·스키마·메뉴 마커를 다 갖춘 파일을 찍어낸다.

쓰는 법:

    python new_post.py suno-guide music

  첫 번째가 주소(/blog/<여기>/), 두 번째가 site.json 의 카테고리 slug 다.
  만들고 나면 site.json 의 그 카테고리 pages 에 줄이 자동으로 추가된다.

그다음 할 일은 셋뿐이다.
  1) 만들어진 파일에서 <!-- 여기부터 --> 사이에 본문을 쓴다
  2) head 위쪽의 TODO 표시된 값(제목·설명·FAQ)을 채운다
  3) python build.py  &&  python check.py

본문 바깥(메뉴·푸터·사이트맵)은 손대지 않는다. build.py 가 알아서 한다.
"""

import collections
import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

TPL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>TODO 제목 - TODO 부제 | {brand}</title>
<meta name="description" content="TODO 첫 문단의 답을 그대로 요약해서 넣으세요. 검색 결과에 그대로 나옵니다. {today} 공식 페이지 확인.">
<link rel="canonical" href="{base}/blog/{slug}/">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#fcfcf9">
<meta name="cat" content="TODO분류">
<meta name="kicker" content="TODO성격">
<meta name="posted" content="{today}">

<meta property="og:type" content="article">
<meta property="og:site_name" content="{brand}">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="{base}/blog/{slug}/">
<meta property="og:title" content="TODO 제목 - TODO 부제">
<meta property="og:description" content="TODO 짧은 설명">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="TODO 제목 - TODO 부제">
<meta name="twitter:description" content="TODO 짧은 설명">

<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2318181b'/%3E%3Ctext x='16' y='22' font-family='Helvetica,Arial,sans-serif' font-size='14' font-weight='bold' fill='white' text-anchor='middle'%3EAI%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="/assets/site.css">
<link rel="alternate" type="application/rss+xml" title="{brand}" href="{base}/rss.xml">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "AI 도구 비교", "item": "{base}/" }},
        {{ "@type": "ListItem", "position": 2, "name": "{catlabel}", "item": "{base}/{catslug}/" }},
        {{ "@type": "ListItem", "position": 3, "name": "TODO 제목", "item": "{base}/blog/{slug}/" }}
      ]
    }},
    {{
      "@type": "WebPage",
      "@id": "{base}/blog/{slug}/#webpage",
      "url": "{base}/blog/{slug}/",
      "name": "TODO 제목",
      "inLanguage": "ko-KR",
      "datePublished": "{today}",
      "dateModified": "{today}"
    }},
    {{
      "@type": "FAQPage",
      "@id": "{base}/blog/{slug}/#faq",
      "inLanguage": "ko-KR",
      "mainEntity": [
        {{
          "@type": "Question",
          "name": "TODO 사람들이 실제로 검색하는 질문 그대로",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "TODO 결론부터. 아래 본문 FAQ 와 글자 하나까지 같아야 합니다."
          }}
        }}
      ]
    }}
  ]
}}
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
    <!--NAV-->
    <!--/NAV-->
    <div class="header__right">
      <button class="menu-btn" type="button" id="menu-btn" aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobile-nav">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </div>
  <div class="mobile-nav" id="mobile-nav" hidden>
    <!--MNAV-->
    <!--/MNAV-->
  </div>
</header>

<main>
  <div class="wrap">
    <nav class="crumb" aria-label="위치">
      <a href="/">AI 도구 비교</a> <span class="crumb__sep">›</span> <a href="/{catslug}/">{catlabel}</a> <span class="crumb__sep">›</span> <span>TODO 짧은 이름</span>
    </nav>
  </div>

  <section class="wrap page-hero">
    <div class="eyebrow">
      <span class="eyebrow__mark" style="background:#18181b" aria-hidden="true">T</span>
      <span class="eyebrow__label" style="color:#52525b">TODO LABEL</span>
    </div>
    <h1>TODO 제목 — TODO 부제</h1>
    <p class="page-hero__lead"><b>TODO 여기서 답을 끝내세요.</b> 결론이 세 번째 문단에 있으면 지식스니펫에 안 뽑힙니다. 서론·배경을 앞에 두지 마세요.</p>
    <div class="page-hero__meta">
      <span class="chip">✓ TODO</span>
      <span class="chip">✓ TODO</span>
      <span class="chip">✓ {todayko} 확인</span>
    </div>
  </section>

  <section class="wrap" style="padding-top:36px;padding-bottom:40px">
    <div class="prose">

      <!-- 여기부터 본문 -->

      <h2>한 줄 요약</h2>
      <p>TODO</p>

      <div class="ad" data-ad="top"><div class="ad__box"></div></div>

      <h2>TODO</h2>
      <p>TODO</p>

      <div class="ad ad--mid" data-ad="mid"><div class="ad__box"></div></div>

      <h2>TODO</h2>
      <p>TODO</p>

      <div class="tip">
        <b>{todayko} 공식 페이지 확인 기준입니다.</b>
        TODO 무엇이 바뀔 수 있는지 적고, 공식 링크를 겁니다.
      </div>

      <h2>이 글을 쓰면서</h2>
      <p>TODO 확인하다가 알게 된 것, 다른 글과 다르게 쓴 이유.</p>

      <!-- 여기까지 본문 -->

    </div>
  </section>

  <div class="wrap"><div class="ad" data-ad="bottom"><div class="ad__box"></div></div></div>

  <section class="wrap" style="padding-bottom:8px">
    <div class="next-up">
      <div class="next-up__title">이어서 볼 만한 것</div>
      <div class="next-up__grid">
        <a class="next-up__card" href="/{catslug}/">
          <b>{catlabel} 글 모음</b>
          <span>TODO</span>
        </a>
        <a class="next-up__card" href="/blog/">
          <b>전체 글 목록</b>
          <span>요금표에 안 적혀 있는 것들</span>
        </a>
      </div>
    </div>
  </section>

  <section class="faq">
    <div class="wrap faq__inner">
      <div>
        <h2>자주 묻는 질문</h2>
        <p class="faq__lead">{todayko} 공식 페이지 확인 기준입니다.</p>
      </div>
      <div class="faq__list">
        <div class="faq__item">
          <h3 class="faq__q">TODO 사람들이 실제로 검색하는 질문 그대로</h3>
          <p class="faq__a">TODO 결론부터. 위 FAQPage 스키마와 글자 하나까지 같아야 합니다.</p>
        </div>
      </div>
    </div>
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
      <!--FOOTLINKS-->
      <!--/FOOTLINKS-->
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


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    slug, catslug = sys.argv[1].strip("/"), sys.argv[2]

    cfgpath = os.path.join(ROOT, "site.json")
    cfg = json.loads(
        io.open(cfgpath, encoding="utf-8").read(),
        object_pairs_hook=collections.OrderedDict,
    )

    cat = next((c for c in cfg["categories"] if c["slug"] == catslug), None)
    if cat is None:
        names = " ".join(c["slug"] for c in cfg["categories"])
        print("그런 카테고리가 없습니다: %s\n쓸 수 있는 것: %s" % (catslug, names))
        sys.exit(1)

    out = os.path.join(ROOT, "blog", slug, "index.html")
    if os.path.exists(out):
        print("이미 있습니다: %s" % out)
        sys.exit(1)

    y, m, d = TODAY.split("-")
    html = TPL.format(
        slug=slug,
        catslug=catslug,
        catlabel=cat["label"],
        base=cfg["site"]["base"],
        brand=cfg["site"]["name"],
        alt=cfg["site"]["alt"],
        today=TODAY,
        todayko="%s년 %d월 %d일" % (y, int(m), int(d)),
    )

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    url = "/blog/%s/" % slug
    if url not in cat["pages"]:
        cat["pages"].insert(0, url)
        with io.open(cfgpath, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    print("만들었습니다:  blog/%s/index.html" % slug)
    print("site.json:     %s 카테고리에 %s 추가" % (catslug, url))
    print("")
    print("다음: 파일에서 TODO 를 채우고  python build.py")


if __name__ == "__main__":
    main()
