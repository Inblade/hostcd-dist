/* hostcd.dev cookie consent for Google Analytics (GA4).
 *
 * Default is the privacy-first, cookieless Cloudflare Web Analytics that is
 * always on. Google Analytics 4 (measurement ID G-07H29RVY42) — which sets
 * cookies and sends data to Google — is loaded ONLY after the visitor clicks
 * Accept. The choice is remembered in localStorage; Decline loads nothing.
 *
 * window.hostcdCookieSettings() re-opens the banner so a visitor can change or
 * withdraw their choice (used by the "cookie choice" link on the privacy page).
 */
(function () {
  "use strict";
  var GA_ID = "G-07H29RVY42";
  var KEY = "hostcd-analytics-consent"; // "granted" | "denied"
  var loaded = false;

  function store(get, val) {
    try {
      if (get) return window.localStorage.getItem(KEY);
      window.localStorage.setItem(KEY, val);
    } catch (e) {
      /* private mode / storage blocked — treat as no stored choice */
    }
    return null;
  }

  function loadAnalytics() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    function gtag() {
      window.dataLayer.push(arguments);
    }
    window.gtag = gtag;
    gtag("js", new Date());
    gtag("config", GA_ID, { anonymize_ip: true });
  }

  function injectStyle() {
    if (document.getElementById("hostcd-consent-style")) return;
    var css =
      "#hostcd-consent{position:fixed;left:50%;transform:translateX(-50%);bottom:16px;z-index:2147483000;" +
      "width:calc(100% - 32px);max-width:560px;box-sizing:border-box;" +
      "background:var(--surface,#14161c);color:var(--ink,#eaebef);" +
      "border:1px solid var(--line,#242834);border-radius:14px;" +
      "box-shadow:0 10px 40px rgba(0,0,0,.35);padding:16px 18px;" +
      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;" +
      "font-size:14px;line-height:1.5}" +
      "#hostcd-consent p{margin:0 0 12px;color:var(--muted,#949ba9)}" +
      "#hostcd-consent a{color:var(--accent,#ff7a33);text-decoration:none}" +
      "#hostcd-consent a:hover{text-decoration:underline}" +
      "#hostcd-consent .row{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}" +
      "#hostcd-consent button{font:inherit;font-size:13.5px;cursor:pointer;border-radius:9px;" +
      "padding:8px 16px;border:1px solid var(--line,#242834);background:transparent;color:var(--ink,#eaebef)}" +
      "#hostcd-consent button.accept{background:var(--accent,#ff7a33);border-color:var(--accent,#ff7a33);" +
      "color:var(--accent-ink,#17110a);font-weight:600}" +
      "#hostcd-consent button:hover{border-color:var(--muted,#949ba9)}" +
      "#hostcd-consent button.accept:hover{filter:brightness(1.05)}";
    var st = document.createElement("style");
    st.id = "hostcd-consent-style";
    st.textContent = css;
    document.head.appendChild(st);
  }

  function removeBanner() {
    var b = document.getElementById("hostcd-consent");
    if (b && b.parentNode) b.parentNode.removeChild(b);
  }

  function showBanner() {
    if (document.getElementById("hostcd-consent")) return;
    injectStyle();
    var box = document.createElement("div");
    box.id = "hostcd-consent";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-live", "polite");
    box.setAttribute("aria-label", "Cookie choice");
    box.innerHTML =
      '<p>This site uses privacy-first, cookieless analytics by default. ' +
      "May we also enable <strong>Google Analytics</strong> (which sets cookies) to understand usage? " +
      'See our <a href="/privacy/">Privacy Policy</a>.</p>' +
      '<div class="row">' +
      '<button type="button" class="decline">Decline</button>' +
      '<button type="button" class="accept">Accept</button>' +
      "</div>";
    box.querySelector(".accept").addEventListener("click", function () {
      store(false, "granted");
      removeBanner();
      loadAnalytics();
    });
    box.querySelector(".decline").addEventListener("click", function () {
      store(false, "denied");
      removeBanner();
    });
    document.body.appendChild(box);
  }

  // Let the privacy page (or anyone) re-open the banner to change/withdraw.
  window.hostcdCookieSettings = showBanner;

  function init() {
    var choice = store(true);
    if (choice === "granted") {
      loadAnalytics();
    } else if (choice === "denied") {
      /* respect the decline — load nothing */
    } else {
      showBanner();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
