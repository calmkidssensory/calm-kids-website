// Calm Kids Sensory - one-click signup buttons (Continue with Google / Facebook).
// Shared by the Quiet Time Starter Pack forms and the survey. Each button only
// appears once its ID below has been filled in, so the site works unchanged
// until Google and Meta are set up (see calm-guides/social-signup/SETUP.txt).
//
// What we ask for: the email address, nothing else. No name, photo or friends.
// Privacy: the Google and Meta scripts are not loaded when the page opens. They
// load when the signup box scrolls into view (or is touched), as the privacy
// page explains.
(function () {
  "use strict";

  // SETUP: paste your IDs between the quotes.
  var GOOGLE_CLIENT_ID = "160203199985-mdb4u8ljie31b6qa7nib5atjva7r313j.apps.googleusercontent.com";
  var FACEBOOK_APP_ID = "PASTE_YOUR_FACEBOOK_APP_ID_HERE";
  var FB_VERSION = "v25.0";

  function isSet(v) { return !!v && v.indexOf("PASTE_YOUR") !== 0; }

  var GOOGLE_LOGO = '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
  var FACEBOOK_LOGO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#1877F2" d="M24 12.07C24 5.41 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.1 10.13 24v-8.44H7.08v-3.49h3.04V9.41c0-3.02 1.8-4.7 4.54-4.7 1.31 0 2.68.24 2.68.24v2.97h-1.5c-1.5 0-1.96.93-1.96 1.89v2.26h3.34l-.53 3.49h-2.8V24C19.62 23.1 24 18.1 24 12.07z"/></svg>';

  var CSS =
    ".cks-social{margin:0 0 6px;text-align:center}" +
    ".cks-social-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;max-width:340px;margin:0 auto 10px;padding:11px 12px;white-space:nowrap;" +
    "font-family:var(--font-body,Inter,Arial,sans-serif);font-weight:500;font-size:.88rem;line-height:1.2;color:#1f1f1f;background:#fff;border:1px solid #747775;border-radius:999px;cursor:pointer;" +
    "transition:transform .18s ease,box-shadow .18s ease,background .18s ease}" +
    ".cks-social-btn:hover:not([disabled]){background:#f8faf6;box-shadow:0 8px 20px rgba(45,42,30,.10);transform:translateY(-1px)}" +
    ".cks-social-btn:focus-visible{outline:3px solid var(--lavender-deep,#b9a8e8);outline-offset:3px}" +
    ".cks-social-btn[disabled]{opacity:.6;cursor:wait}" +
    ".cks-social-btn svg{width:20px;height:20px;flex:none}" +
    ".cks-social .cks-or{display:flex;align-items:center;gap:12px;max-width:340px;margin:14px auto 14px;color:var(--ink-faint,#9a9284);font-size:.82rem}" +
    ".cks-social .cks-or::before,.cks-social .cks-or::after{content:'';flex:1;height:1px;background:var(--cream-deep,#f0e8d8)}" +
    ".cks-social .cks-social-msg{margin:4px 0 0;font-size:.85rem;line-height:1.5;color:var(--ink-soft,#6e685e)}" +
    ".cks-social .cks-social-msg.is-error{color:#8a4a3a}" +
    "@media (prefers-reduced-motion:reduce){.cks-social-btn:hover:not([disabled]){transform:none}}";

  var styled = false;
  function addStyles() {
    if (styled) return;
    styled = true;
    var s = document.createElement("style");
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ---- script loading (each provider loads once, on demand) -----------------
  var loading = {};
  function loadOnce(key, src, ready) {
    if (loading[key]) return loading[key];
    loading[key] = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = function () { ready ? ready(resolve) : resolve(); };
      s.onerror = function () { loading[key] = null; reject(new Error("load failed: " + key)); };
      document.head.appendChild(s);
    });
    return loading[key];
  }

  function loadGoogle() {
    return loadOnce("google", "https://accounts.google.com/gsi/client");
  }

  function loadFacebook() {
    return loadOnce("facebook", "https://connect.facebook.net/en_US/sdk.js", function (resolve) {
      // sdk.js normally calls window.fbAsyncInit itself; calling initFB again is harmless.
      initFB();
      resolve();
    });
  }
  var fbReady = false;
  function initFB() {
    if (fbReady || !window.FB) return;
    fbReady = true;
    window.FB.init({ appId: FACEBOOK_APP_ID, cookie: false, xfbml: false, version: FB_VERSION });
  }
  window.fbAsyncInit = initFB;

  // ---- sign-in flows --------------------------------------------------------
  function googleFlow(onEmail, onProblem) {
    try {
      var client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: "openid email",
        callback: function (resp) {
          if (!resp || !resp.access_token) { onProblem(); return; }
          fetch("https://www.googleapis.com/oauth2/v3/userinfo", { headers: { Authorization: "Bearer " + resp.access_token } })
            .then(function (r) { return r.json(); })
            .then(function (u) {
              if (u && u.email) onEmail(String(u.email).toLowerCase(), "google");
              else onProblem("Google did not share an email address. Please use the email box instead.");
            })
            .catch(function () { onProblem("Something went quietly wrong. Please try again, or use the email box."); });
        },
        error_callback: function () { onProblem(); } // window closed: say nothing
      });
      client.requestAccessToken();
    } catch (e) {
      onProblem("Google sign-in is not available right now. Please use the email box.");
    }
  }

  function facebookFlow(onEmail, onProblem) {
    try {
      window.FB.login(function (resp) {
        if (!resp || !resp.authResponse) { onProblem(); return; } // cancelled: say nothing
        window.FB.api("/me", { fields: "email" }, function (me) {
          if (me && me.email) onEmail(String(me.email).toLowerCase(), "facebook");
          else onProblem("Facebook did not share an email address. Please use the email box instead.");
        });
      }, { scope: "email" });
    } catch (e) {
      onProblem("Facebook sign-in is not available right now. Please use the email box.");
    }
  }

  // ---- UI -------------------------------------------------------------------
  function makeButton(label, logo) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "cks-social-btn";
    b.innerHTML = logo + "<span>" + label + "</span>";
    return b;
  }

  // Adds the buttons at the top of `container`.
  // opts.onEmail(email, provider) is called after a successful sign-in.
  function mount(container, opts) {
    var useGoogle = isSet(GOOGLE_CLIENT_ID);
    var useFacebook = isSet(FACEBOOK_APP_ID);
    if (!container || (!useGoogle && !useFacebook)) return null;
    addStyles();

    var block = document.createElement("div");
    block.className = "cks-social";
    var msg = document.createElement("p");
    msg.className = "cks-social-msg";
    msg.setAttribute("role", "status");
    msg.hidden = true;

    function say(text, isError) {
      if (!text) { msg.hidden = true; return; }
      msg.textContent = text;
      msg.className = "cks-social-msg" + (isError ? " is-error" : "");
      msg.hidden = false;
    }

    var buttons = [];
    function lock(on) { buttons.forEach(function (b) { b.disabled = on; }); }
    function succeed(email, provider) { lock(false); say(""); opts.onEmail(email, provider); }
    function problem(text) { lock(false); say(text || "", true); }

    function wireButton(btn, isLoaded, load, flow) {
      btn.addEventListener("click", function () {
        say("");
        if (!isLoaded()) {
          // The script has not arrived yet. Load it, then ask for one more tap so
          // the browser does not block the sign-in window.
          btn.disabled = true;
          load().then(function () { btn.disabled = false; say("Ready. Please tap the button once more."); })
                .catch(function () { btn.disabled = false; say("That sign-in could not load. Please use the email box.", true); });
          return;
        }
        lock(true);
        flow(succeed, problem);
      });
    }

    if (useGoogle) {
      var g = makeButton("Continue with Google", GOOGLE_LOGO);
      wireButton(g, function () { return !!(window.google && window.google.accounts && window.google.accounts.oauth2); }, loadGoogle, googleFlow);
      block.appendChild(g);
      buttons.push(g);
    }
    if (useFacebook) {
      var f = makeButton("Continue with Facebook", FACEBOOK_LOGO);
      wireButton(f, function () { return !!window.FB && fbReady; }, loadFacebook, facebookFlow);
      block.appendChild(f);
      buttons.push(f);
    }
    block.appendChild(msg);
    var or = document.createElement("p");
    or.className = "cks-or";
    or.textContent = "or use your email";
    block.appendChild(or);

    container.insertBefore(block, container.firstChild);

    // Preload the provider scripts when the box comes into view, or is touched.
    var started = false;
    function preload() {
      if (started) return;
      started = true;
      if (useGoogle) loadGoogle().catch(function () {});
      if (useFacebook) loadFacebook().catch(function () {});
    }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) { io.disconnect(); preload(); }
      }, { rootMargin: "200px" });
      io.observe(block);
    }
    ["pointerenter", "focusin", "touchstart"].forEach(function (ev) {
      block.addEventListener(ev, preload, { passive: true, once: true });
    });
    return block;
  }

  window.CKSSocial = { mount: mount, configured: function () { return isSet(GOOGLE_CLIENT_ID) || isSet(FACEBOOK_APP_ID); } };
})();
