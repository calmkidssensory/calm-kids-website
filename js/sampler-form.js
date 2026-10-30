// Calm Kids Sensory — free sampler email capture.
//
// Wires every ".sampler-form" on a book page to submit quietly in the
// background (no page reload) to our Google Apps Script Web App, which logs
// the request to a Google Sheet and emails the sampler PDF link back to the
// visitor. See google-sheets-setup.txt for the script this talks to.
//
// SETUP: after deploying that script as a Web App, paste the deployment URL
// below, replacing the placeholder.
//
// One-click Google / Facebook buttons are added by social-signup.js, which this
// file loads on demand. The buttons only appear once the IDs in that file are set.
(function () {
  "use strict";

  var GAS_WEB_APP_URL =
    "https://script.google.com/macros/s/AKfycbwq0lqvsKsPHtzsf8kl35VtJhiLXDsNFEN72c9ZQQrHNaKB5MiDRe8p96RqnkA6d7uJHA/exec";
  var SCRIPT_SRC = (document.currentScript && document.currentScript.src) || "";

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function showError(errorNote, message) {
    if (!errorNote) return;
    errorNote.textContent = message;
    errorNote.hidden = false;
  }

  function showSuccess(form) {
    var successNote = form.querySelector(".sampler-success");
    form.querySelectorAll("input, button[type=submit], .cks-social, .sampler-consent").forEach(function (el) {
      el.hidden = true;
    });
    if (successNote) successNote.hidden = false;
  }

  // Sends the form (book + slug fields) with the given email address.
  // Google Apps Script Web Apps don't send CORS headers we can read, so the
  // request goes out "no-cors": the browser still delivers it, we just can't
  // inspect the response. We show success once the request leaves without a
  // network error.
  function send(form, email) {
    var formData = new FormData(form);
    formData.set("email", email);
    return fetch(GAS_WEB_APP_URL, { method: "POST", mode: "no-cors", body: formData });
  }

  function wireForm(form) {
    // Small consent line with a link to the privacy policy.
    if (!form.querySelector(".sampler-consent")) {
      var consent = document.createElement("p");
      consent.className = "sampler-consent";
      consent.style.cssText = "font-size:0.78rem; line-height:1.5; color:var(--ink-faint, #9a9284); margin:8px 0 0; text-align:center;";
      consent.innerHTML = 'We will email your free pages. Read our <a href="/privacy/" style="color:inherit; text-decoration:underline;">Privacy Policy</a>.';
      var after = form.querySelector(".sampler-error");
      form.insertBefore(consent, after || null);
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var emailInput = form.querySelector('input[name="email"]');
      var email = emailInput ? emailInput.value.trim() : "";
      var submitBtn = form.querySelector('button[type="submit"]');
      var errorNote = form.querySelector(".sampler-error");

      if (errorNote) errorNote.hidden = true;

      if (!isValidEmail(email)) {
        showError(errorNote, "That email address doesn't look quite right yet.");
        return;
      }

      if (!GAS_WEB_APP_URL || GAS_WEB_APP_URL.indexOf("PASTE_YOUR") === 0) {
        showError(errorNote, "Our sampler mailbox is still being set up. Please check back soon.");
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";
      }

      send(form, email)
        .then(function () { showSuccess(form); })
        .catch(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Send Me My Free Pages";
          }
          showError(errorNote, "Something went quietly wrong. Please try again in a moment.");
        });
    });
  }

  // Adds Continue with Google / Facebook above the email box, when configured.
  function addSocial(form) {
    if (!window.CKSSocial) return;
    window.CKSSocial.mount(form, {
      onEmail: function (email) {
        var errorNote = form.querySelector(".sampler-error");
        if (errorNote) errorNote.hidden = true;
        if (!isValidEmail(email)) {
          showError(errorNote, "That email address doesn't look quite right. Please type it in the box instead.");
          return;
        }
        send(form, email)
          .then(function () { showSuccess(form); })
          .catch(function () {
            showError(errorNote, "Something went quietly wrong. Please try again in a moment.");
          });
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
    var forms = document.querySelectorAll(".sampler-form");
    forms.forEach(wireForm);
    if (forms.length) {
      loadSocialScript(function () { forms.forEach(addSocial); });
    }
  });
})();
