/* hostcd.dev — cookieless link-click tracking.
 *
 * Page VISITS are counted by Cloudflare Web Analytics (the beacon in <head>).
 * This adds link-CLICK events on top. It stores nothing, sets no cookie, and
 * reads no personal data — only the clicked link's href/text and the current
 * path. Events are sent via Cloudflare Zaraz's zaraz.track() when Zaraz is
 * enabled for the zone (Cloudflare dashboard → Zaraz); when it is not, the
 * calls are a harmless no-op, so the page works the same with or without it.
 */
(function () {
  "use strict";
  function track(name, props) {
    try {
      if (window.zaraz && typeof window.zaraz.track === "function") {
        window.zaraz.track(name, props);
      }
    } catch (e) { /* never let analytics break navigation */ }
  }
  document.addEventListener("click", function (ev) {
    var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#") return; // in-page anchors aren't link transitions
    var outbound = false;
    try { outbound = new URL(a.href, location.href).host !== location.host; } catch (e) {}
    track("link_click", {
      href: a.href,
      text: (a.textContent || "").trim().slice(0, 80),
      label: a.getAttribute("data-track") || null,
      outbound: outbound,
      from: location.pathname
    });
  }, { capture: true, passive: true });
})();
