"""ai.howtopackbook.com 요금 변경 감시 - 매달 윈도우 예약 작업(AIPack-WatchPrices)이 돌린다.

공식 요금 페이지를 헤드리스 브라우저로 열어 화면에 보이는 가격 표기(₩·원·$·€ 숫자)를 전부 모으고,
기준값(tools/watch_baseline.json)과 다르면 알림 창을 띄우고 tools/watch_log.txt 에 남긴다.
항목마다 정규식을 짜지 않는 이유: 서비스가 14개라 문구가 조금만 바뀌어도 깨진다. 가격 숫자 묶음이
달라졌다는 것만 알리고, 무엇이 바뀌었는지는 사람이 공식 페이지에서 확인한다(지어내지 않는다).

바뀐 걸 보면 할 일: 대화창에 "AI 요금 재확인" - 공식 페이지 대조 → 글 → pricing.json → build.py → 푸시.
사이트에 반영한 뒤 기준값을 새 값으로 바꾼다:
    python tools/watch_prices.py --accept

ChatGPT·Claude 는 일반 요청에 403 을 주므로 브라우저로 연다. 광고 도메인은 막는다(무효 트래픽 방지).
네트워크 오류는 그 페이지만 "(못 읽음)"으로 남기고, 그것만으로는 알림을 띄우지 않는다.
"""
import ctypes
import datetime
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "watch_baseline.json")
LOG = os.path.join(HERE, "watch_log.txt")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/140.0 Safari/537.36 ai-howtopackbook-price-watch-bot")
ADS = re.compile(r"doubleclick|googlesyndication|googleadservices|adservice|adnxs|criteo|taboola|outbrain|facebook\.net|hotjar")

PAGES = {
    "제미나이 요금": "https://gemini.google/kr/subscriptions/",
    "제미나이 학생": "https://gemini.google/kr/students/",
    "구글 원 요금": "https://one.google.com/about/plans?hl=ko&gl=KR",
    "ChatGPT 요금": "https://chatgpt.com/ko-KR/pricing/",
    "클로드 요금": "https://claude.com/pricing",
    "캡컷 Pro": "https://www.capcut.com/resource/capcut-standard-vs-pro",
    "브루 요금": "https://vrew.ai/ko/payment/pricepolicy",
    "미드저니 플랜": "https://docs.midjourney.com/hc/en-us/articles/27870484040333-Comparing-Midjourney-Plans",
    "노션 요금": "https://www.notion.com/ko/pricing",
    "캔바 요금": "https://www.canva.com/ko_kr/pricing/",
    "딥엘 요금": "https://www.deepl.com/ko/pro",
    "수노 요금": "https://suno.com/pricing",
    "일레븐랩스 요금": "https://elevenlabs.io/pricing",
    "타입캐스트 요금": "https://typecast.ai/kr/pricing/",
}
# 모델 단가표(제미나이 API 등)는 넣지 않는다 - 새 모델만 나와도 울린다. 사이트가 다루는 건 플랜 가격이다.
# 날짜·문구 변화도 같이 보는 곳: 학생 혜택 기한, 키 정책
PHRASES = {
    "제미나이 학생": [r"20\d\d년 \d{1,2}월 \d{1,2}일까지", r"AI (?:Plus|Pro)[^.。]{0,20}(?:1년|12개월)"],
}
PRICE = re.compile(r"(?:₩|KRW\s?|US\$|\$|€)\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?원")


def prices_of(text):
    toks = {re.sub(r"\s+", "", t) for t in PRICE.findall(text)}
    return sorted(toks)


def read_current():
    cur = {}
    with sync_playwright() as p:
        # 자동화 표시를 끄지 않으면 chatgpt.com 이 빈 화면을 준다(10-08 확인)
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx.route("**/*", lambda r: r.abort() if ADS.search(r.request.url) else r.continue_())
        page = ctx.new_page()
        for name, url in PAGES.items():
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)
                text = page.inner_text("body")
                item = {"가격": prices_of(text)}
                for pat in PHRASES.get(name, []):
                    item.setdefault("문구", []).extend(sorted(set(re.findall(pat, text))))
                if not item["가격"] and not item.get("문구"):
                    item = "(가격 표기 없음 - 페이지 구조가 바뀌었거나 막힘)"
                cur[name] = item
            except Exception as e:
                cur[name] = "(못 읽음: %s)" % type(e).__name__
        b.close()
    return cur


def log(msg):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")


def popup(title, body):
    if os.environ.get("WATCH_NO_POPUP"):  # 시험용
        return
    try:
        ctypes.windll.user32.MessageBoxW(0, body, title, 0x40 | 0x40000)
    except Exception:
        pass


def diff(old, new):
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for k in sorted(set(old) | set(new)):
            a, b = set(old.get(k, [])), set(new.get(k, []))
            if a != b:
                gone, came = sorted(a - b), sorted(b - a)
                out.append("%s 빠짐 %s / 생김 %s" % (k, ", ".join(gone) or "-", ", ".join(came) or "-"))
        return "; ".join(out)
    return "%s -> %s" % (old if isinstance(old, str) else "읽힘", new if isinstance(new, str) else "읽힘")


def main():
    accept = "--accept" in sys.argv
    cur = read_current()

    if accept or not os.path.exists(BASELINE):
        json.dump(cur, open(BASELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        log("기준값 저장: %d개 페이지" % len(cur))
        print("기준값 저장:", json.dumps(cur, ensure_ascii=False, indent=2))
        return 0

    base = json.load(open(BASELINE, encoding="utf-8"))
    changed, unread = [], []
    for k, v in cur.items():
        if base.get(k) == v:
            continue
        if isinstance(v, str) and v.startswith("(못 읽음"):
            unread.append(k)  # 일시 오류일 수 있다 - 알림은 띄우지 않는다
            continue
        changed.append("- %s: %s" % (k, diff(base.get(k), v)))

    if unread:
        log("못 읽음(다음 달 재시도): " + ", ".join(unread))
    if not changed:
        log("변화 없음")
        print("변화 없음" + (" (못 읽음: %s)" % ", ".join(unread) if unread else ""))
        return 0

    log("변경 감지: " + " | ".join(changed))
    print("\n".join(changed))
    popup(
        "AI 도구 연구소 - 공식 요금이 바뀌었을 수 있습니다",
        "\n".join(changed)
        + "\n\nClaude 에게 \"AI 요금 재확인\"이라고 말하면 공식 페이지와 대조해 글·요금표를 고칩니다."
        + "\n반영한 뒤 기준값 갱신: python tools/watch_prices.py --accept",
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
