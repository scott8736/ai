/* AI Pack / AI요금제연구소 — 페이지 동작
   1) 모바일 메뉴 토글
   2) 애드센스 광고 단위 삽입 */

(function () {
  "use strict";

  /* ---------- 모바일 메뉴 ---------- */

  var btn = document.getElementById("menu-btn");
  var panel = document.getElementById("mobile-nav");

  if (btn && panel) {
    btn.addEventListener("click", function () {
      var open = panel.hidden;
      panel.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
      btn.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    });

    // 앵커를 누르면 메뉴를 닫는다
    panel.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        panel.hidden = true;
        btn.setAttribute("aria-expanded", "false");
        btn.setAttribute("aria-label", "메뉴 열기");
      }
    });
  }

  /* ---------- 애드센스 ----------

     AD_SLOTS 에는 애드센스 콘솔에서 발급받은 "광고 단위 ID"(숫자 10자리)를 넣습니다.
     광고 > 개요 > 광고 단위 기준 에서 만들면 data-ad-slot="1234567890" 형태로
     나오는 그 숫자입니다.

     format 은 광고 단위를 만들 때 고른 유형에 맞춥니다.
       "auto"   — 디스플레이 광고. 자리 크기에 맞춰 알아서 늘어난다
       "fluid"  — 인아티클 광고. 문단 사이에 자연스럽게 들어가 이탈이 적다

     비워두면 해당 자리는 아예 렌더링하지 않습니다. 유효하지 않은 슬롯으로
     요청을 보내면 채워지지 않는 빈 상자만 남기 때문입니다.

     앵커 광고(모바일 하단 고정)와 전면 광고는 여기서 넣는 게 아니라
     애드센스 콘솔의 "자동 광고" 설정에서 켭니다. 코드 수정이 필요 없습니다. */

  var AD_CLIENT = "ca-pub-8646375689901020";
  var AD_SLOTS = {
    top: { slot: "", format: "auto" },
    mid: { slot: "", format: "fluid", layout: "in-article" },
    bottom: { slot: "", format: "auto" }
  };

  document.querySelectorAll("[data-ad]").forEach(function (holder) {
    var conf = AD_SLOTS[holder.getAttribute("data-ad")];

    if (!conf || !conf.slot) {
      holder.remove();
      return;
    }

    var box = holder.querySelector(".ad__box");
    if (!box) return;

    var ins = document.createElement("ins");
    ins.className = "adsbygoogle";
    ins.style.display = "block";
    ins.setAttribute("data-ad-client", AD_CLIENT);
    ins.setAttribute("data-ad-slot", conf.slot);
    ins.setAttribute("data-ad-format", conf.format);

    if (conf.layout) {
      ins.setAttribute("data-ad-layout", conf.layout);
    } else {
      ins.setAttribute("data-full-width-responsive", "true");
    }

    box.appendChild(ins);

    // 스크립트 로드 뒤에 삽입한 단위는 push 해야 채워진다
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      /* 광고 차단기 등 — 페이지 동작에는 영향 없음 */
    }
  });
})();
