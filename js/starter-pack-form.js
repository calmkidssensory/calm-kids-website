// Calm Kids Sensory - Quiet Time Starter Pack signup.
// Posts the visitor's email to our Google Apps Script web app (see
// calm-guides/emails/quiet-time-funnel.gs), which logs it and emails the pack.
// SETUP: after deploying that script as a Web App, paste its URL below.
(function () {
  "use strict";

  var GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycby-LHGeJqaAX5LdaHxXbMV0LEl_HOdvSzgRNT-DDG9VvlwrFg1r6u67O0X9d2NM-moT/exec";

  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }

  function showError(note, msg) {
    if (!note) return;
    note.textContent = msg;
    note.hidden = false;
  }

  function wire(form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var input = form.querySelector('input[name="email"]');
      var email = input ? input.value.trim() : "";
      var btn = form.querySelector('button[type="submit"]');
      var ok = form.querySelector(".sampler-success");
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

      // Apps Script web apps do not return CORS headers we can read, so the
      // request goes out "no-cors" and we show success once it leaves cleanly.
      fetch(GAS_WEB_APP_URL, { method: "POST", mode: "no-cors", body: new FormData(form) })
        .then(function () {
          form.querySelectorAll("input, button[type=submit], .starter-consent").forEach(function (el) { el.hidden = true; });
          if (ok) ok.hidden = false;
        })
        .catch(function () {
          if (btn) { btn.disabled = false; btn.textContent = "Send Me the Starter Pack"; }
          showError(err, "Something went quietly wrong. Please try again in a moment.");
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".starter-form").forEach(wire);
  });
})();
