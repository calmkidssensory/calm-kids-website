// Calm Kids Sensory - Quiet Time Starter Pack signup.
// Posts the visitor's email to our Google Apps Script web app (see
// calm-guides/emails/quiet-time-funnel.gs), which logs it and emails the pack.
// SETUP: after deploying that script as a Web App, paste its URL below.
// One-click Google / Facebook buttons are added by social-signup.js once the
// IDs in that file are filled in (see calm-guides/social-signup/SETUP.txt).
(function () {
  "use strict";

  var GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycby-LHGeJqaAX5LdaHxXbMV0LEl_HOdvSzgRNT-DDG9VvlwrFg1r6u67O0X9d2NM-moT/exec";
  var SCRIPT_SRC = (document.currentScript && document.currentScript.src) || "";

  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }

  function showError(note, msg) {
    if (!note) return;
    note.textContent = msg;
    note.hidden = false;
  }

  function showSuccess(form) {
    var ok = form.querySelector(".sampler-success");
    form.querySelectorAll("input, button[type=submit], .starter-consent, .cks-social").forEach(function (el) { el.hidden = true; });
    if (ok) ok.hidden = false;
  }

  function post(email) {
    // Apps Script web apps do not return CORS headers we can read, so the
    // request goes out "no-cors" and we show success once it leaves cleanly.
    var data = new FormData();
    data.append("email", email);
    data.append("website", "");
    return fetch(GAS_WEB_APP_URL, { method: "POST", mode: "no-cors", body: data });
  }

  function wire(form) {
    // Point the consent line at the privacy policy.
    var consent = form.querySelector(".starter-consent");
    if (consent && consent.innerHTML.indexOf("/privacy/") === -1) {
      consent.innerHTML += ' Read our <a href="/privacy/" style="color:inherit; text-decoration:underline;">Privacy Policy</a>.';
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var input = form.querySelector('input[name="email"]');
      var email = input ? input.value.trim() : "";
      var btn = form.querySelector('button[type="submit"]');
      var err = form.querySelector(".sampler-error");
      if (err) err.hidden = true;

      if (!isValidEmail(email)) {
        showError(err, "That email address does not look quite right yet.");
        return;
      }
      if (!GAS_WEB_APP_URL || GAS_WEB_APP_URL.indexOf("PASTE_YOUR") === 0) {
        showError(err, "Our starter pack mailbox is still being set up. Please check back soon.");
        return;
      }
      if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }

      post(email)
        .then(function () { showSuccess(form); })
        .catch(function () {
          if (btn) { btn.disabled = false; btn.textContent = "Send Me the Starter Pack"; }
          showError(err, "Something went quietly wrong. Please try again in a moment.");
        });
    });
  }

  // Adds Continue with Google / Facebook above the email box, when configured.
  function addSocial(form) {
    if (!window.CKSSocial) return;
    window.CKSSocial.mount(form, {
      onEmail: function (email) {
        var err = form.querySelector(".sampler-error");
        if (err) err.hidden = true;
        if (!isValidEmail(email)) { showError(err, "That email address does not look quite right. Please type it in the box instead."); return; }
        post(email)
          .then(function () { showSuccess(form); })
          .catch(function () { showError(err, "Something went quietly wrong. Please try again in a moment."); });
      }
    });
  }

  function loadSocialScript(done) {
    if (window.CKSSocial) { done(); return; }
    if (!SCRIPT_SRC) return;
    var s = document.createElement("script");
    s.src = SCRIPT_SRC.replace(/[^\/]*$/, "") + "social-signup.js";
    s.onload = done;
    document.head.appendChild(s);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var forms = document.querySelectorAll(".starter-form");
    forms.forEach(wire);
    if (forms.length) {
      loadSocialScript(function () { forms.forEach(addSocial); });
    }
  });
})();
