// Calm Kids Sensory — free sampler email capture.
//
// Wires every ".sampler-form" on a book page to submit quietly in the
// background (no page reload) to our Google Apps Script Web App, which logs
// the request to a Google Sheet and emails the sampler PDF link back to the
// visitor. See google-sheets-setup.txt for the script this talks to.
//
// SETUP: after deploying that script as a Web App, paste the deployment URL
// below, replacing the placeholder.
(function () {
  "use strict";

  var GAS_WEB_APP_URL = "PASTE_YOUR_GOOGLE_APPS_SCRIPT_WEB_APP_URL_HERE";

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function showError(errorNote, message) {
    if (!errorNote) return;
    errorNote.textContent = message;
    errorNote.hidden = false;
  }

  function wireForm(form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var emailInput = form.querySelector('input[name="email"]');
      var email = emailInput ? emailInput.value.trim() : "";
      var submitBtn = form.querySelector('button[type="submit"]');
      var successNote = form.querySelector(".sampler-success");
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

      var formData = new FormData(form);

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";
      }

      // Google Apps Script Web Apps don't send CORS headers we can read, so
      // this request goes out "no-cors": the browser still delivers it, we
      // just can't inspect the response. We show success once the request
      // leaves without a network error.
      fetch(GAS_WEB_APP_URL, {
        method: "POST",
        mode: "no-cors",
        body: formData,
      })
        .then(function () {
          var fields = form.querySelectorAll("input, button[type=submit]");
          fields.forEach(function (el) {
            el.hidden = true;
          });
          if (successNote) successNote.hidden = false;
        })
        .catch(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Send Me My Free Pages";
          }
          showError(errorNote, "Something went quietly wrong. Please try again in a moment.");
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".sampler-form").forEach(wireForm);
  });
})();
