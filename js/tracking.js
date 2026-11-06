// Calm Kids Sensory - shared analytics and ad pixel loader.
// One file for every page: Google Analytics 4 and the Pinterest Tag.
//
// Consent: visitors in Europe (browser time zone in Europe/ or the UK) see a
// small banner and nothing loads until they choose Accept. Everywhere else the
// tags load by default, and /privacy/ explains how to opt out. A choice is
// stored in this browser only (localStorage key "cks_consent").
//
// Events (called by starter-pack-form.js after a successful submit):
//   window.CKSTrack.signup("email" | "social")
//     -> GA4 event "starter_pack_signup", Pinterest event "lead"
(function () {
  "use strict";

  var GA4_ID = "G-8TYLTRYQXL";
  var PINTEREST_TAG_ID = "2613586674556"; // numbers only; skipped if not all digits

  var KEY = "cks_consent";
  var loaded = false;

  function stored() {
    try { return window.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function store(v) {
    try { window.localStorage.setItem(KEY, v); } catch (e) { /* private mode: choice lasts for this page only */ }
  }

  function isEurope() {
    var tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { return true; }
    if (!tz) return true; // cannot tell, so ask
    return /^Europe\//.test(tz) || tz === "Atlantic/Reykjavik" || tz === "Atlantic/Canary" ||
           tz === "Atlantic/Madeira" || tz === "Atlantic/Azores" || tz === "Atlantic/Faroe";
  }

  function pinterestEnabled() { return /^\d+$/.test(PINTEREST_TAG_ID); }

  function loadGA4() {
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", GA4_ID);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA4_ID);
    document.head.appendChild(s);
  }

  function loadPinterest() {
    if (!pinterestEnabled()) return;
    /* Standard Pinterest base code */
    !function (e) {
      if (!window.pintrk) {
        window.pintrk = function () { window.pintrk.queue.push(Array.prototype.slice.call(arguments)); };
        var n = window.pintrk;
        n.queue = []; n.version = "3.0";
        var t = document.createElement("script");
        t.async = !0; t.src = e;
        var r = document.getElementsByTagName("script")[0];
        r.parentNode.insertBefore(t, r);
      }
    }("https://s.pinimg.com/ct/core.js");
    window.pintrk("load", PINTEREST_TAG_ID);
    window.pintrk("page");
  }

  function loadAll() {
    if (loaded) return;
    loaded = true;
    loadGA4();
    loadPinterest();
  }

  function removeBanner() {
    var b = document.getElementById("cks-consent");
    if (b && b.parentNode) b.parentNode.removeChild(b);
  }

  function showBanner() {
    if (document.getElementById("cks-consent")) return;
    var d = document.createElement("div");
    d.id = "cks-consent";
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-label", "Privacy choices");
    d.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;max-width:560px;margin:0 auto;" +
      "background:#f7f3ea;color:#3f4a3c;border:1px solid #a8b8a0;border-radius:12px;padding:16px 18px;" +
      "font:15px/1.5 Georgia,'Times New Roman',serif;box-shadow:0 4px 18px rgba(0,0,0,.12);z-index:99999;";
    d.innerHTML =
      '<p style="margin:0 0 12px">We would like to use analytics and an advertising pixel to learn which pages are helpful. ' +
      'They are switched off unless you agree. Details are in our <a href="/privacy/#cookies" style="color:inherit;text-decoration:underline">Privacy Policy</a>.</p>' +
      '<div style="display:flex;gap:10px;flex-wrap:wrap">' +
      '<button type="button" id="cks-consent-yes" style="background:#4a5c46;color:#fff;border:0;border-radius:8px;padding:9px 18px;font:inherit;cursor:pointer">Accept</button>' +
      '<button type="button" id="cks-consent-no" style="background:transparent;color:#3f4a3c;border:1px solid #a8b8a0;border-radius:8px;padding:9px 18px;font:inherit;cursor:pointer">Decline</button>' +
      '</div>';
    document.body.appendChild(d);
    document.getElementById("cks-consent-yes").addEventListener("click", function () {
      store("granted"); removeBanner(); loadAll();
    });
    document.getElementById("cks-consent-no").addEventListener("click", function () {
      store("denied"); removeBanner();
    });
  }

  function decide() {
    var c = stored();
    if (c === "granted") { loadAll(); return; }
    if (c === "denied") { return; }
    if (isEurope()) { showBanner(); return; }
    loadAll();
  }

  window.CKSTrack = {
    // Called only after the Starter Pack form has submitted successfully.
    signup: function (method) {
      if (!loaded) return;
      if (typeof window.gtag === "function") {
        window.gtag("event", "starter_pack_signup", { method: method || "email" });
      }
      if (typeof window.pintrk === "function" && pinterestEnabled()) {
        window.pintrk("track", "lead", { lead_type: "starter_pack" });
      }
    },
    // Used by the "Change my choice" button on /privacy/.
    openChoices: function () {
      try { window.localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
      showBanner();
    },
    // True when the visitor has declined (for the privacy page status line).
    status: function () { return stored() || (isEurope() ? "not chosen" : "on by default"); }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", decide);
  } else {
    decide();
  }
})();
