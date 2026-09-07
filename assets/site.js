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
     광고 > 개요 > 광고 단위 기준 > 디스플레이 광고 에서 만들면
     data-ad-slot="1234567890" 형태로 나오는 그 숫자입니다.

     비워두면 해당 자리는 아예 렌더링하지 않습니다. 유효하지 않은 슬롯으로
     요청을 보내면 채워지지 않는 빈 상자만 남기 때문입니다.
     슬롯을 넣기 전까지는 애드센스 "자동 광고"로만 노출됩니다.        */

  var AD_CLIENT = "ca-pub-8646375689901020";
  var AD_SLOTS = {
    top: "",
    mid: "",
    bottom: ""
  };

  document.querySelectorAll("[data-ad]").forEach(function (holder) {
    var slot = AD_SLOTS[holder.getAttribute("data-ad")];

    if (!slot) {
      holder.remove();
      return;
    }

    var box = holder.querySelector(".ad__box");
    if (!box) return;

    var ins = document.createElement("ins");
    ins.className = "adsbygoogle";
    ins.style.display = "block";
    ins.setAttribute("data-ad-client", AD_CLIENT);
    ins.setAttribute("data-ad-slot", slot);
    ins.setAttribute("data-ad-format", "auto");
    ins.setAttribute("data-full-width-responsive", "true");
    box.appendChild(ins);

    // 스크립트 로드 뒤에 삽입한 단위는 push 해야 채워진다
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      /* 광고 차단기 등 — 페이지 동작에는 영향 없음 */
    }
  });
})();
