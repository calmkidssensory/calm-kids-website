// Calm Kids Sensory - "Choose the next calm pages" survey.
// One question per screen, tap-to-select cards, no required answers.
// Answers go to a Google Apps Script web app (see calm-guides/survey/survey-handler.gs).
// If the visitor opts in, their email goes to the existing Quiet Time Starter Pack
// endpoint instead, so survey answers and emails are never stored together.
(function () {
  "use strict";

  // SETUP: deploy survey-handler.gs as a Web App and paste its /exec URL here.
  var SURVEY_URL = "https://script.google.com/macros/s/AKfycbzVb1Hfq8UYxXwQM5_G-rVKH3IJKSy4evFSX0yrXHQCorPE3jxTWwXM27JKSRynuCjO/exec";
  // Same endpoint the Calm Guides signup form uses (js/starter-pack-form.js).
  var STARTER_URL = "https://script.google.com/macros/s/AKfycby-LHGeJqaAX5LdaHxXbMV0LEl_HOdvSzgRNT-DDG9VvlwrFg1r6u67O0X9d2NM-moT/exec";

  var TICK = '<svg viewBox="0 0 16 16" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 4.8"/></svg>';

  var STEPS = [
    { key: "who", title: "Who will you be coloring with?", hint: "Pick as many as fit.",
      groups: [{ key: "who", options: ["My child", "My students", "My clients", "Myself", "Someone I care for"] }] },
    { key: "age", title: "How old is the colorer?", hint: "A range is plenty. Pick all that apply.",
      groups: [{ key: "age", options: ["Under 5", "5 to 8", "9 to 12", "Teen", "Adult"] }] },
    { key: "hard", title: "What makes coloring hard to settle into?", hint: "Tap anything that sounds familiar.",
      groups: [{ key: "hard", options: ["Too many tiny details", "Lines feel too thin", "Pages feel busy", "Sessions run too long", "Subjects feel too intense", "It goes well already"] }] },
    { key: "themes", title: "Which calm themes should we draw next?", hint: "Pick up to two.",
      groups: [{ key: "themes", max: 2, options: ["Ocean and sea life", "Forest animals", "Gentle gardens", "Night sky and stars", "Farm animals", "Simple patterns", "Cozy home scenes", "Seasons and weather"] }] },
    { key: "how", title: "How do you like to color?", hint: "Both groups are optional.",
      groups: [
        { key: "tools", label: "Tools", options: ["Crayons", "Colored pencils", "Markers", "Watercolor", "On a tablet"] },
        { key: "format", label: "Format", options: ["Printable PDF", "Paperback book", "Either is fine"] }
      ] },
    { key: "last", title: "Anything else we should know?", hint: "Totally optional.", final: true }
  ];

  var HARD_TO_RECIPE = {
    "Too many tiny details": "Wide, open spaces",
    "Lines feel too thin": "Bold, forgiving lines",
    "Pages feel busy": "One gentle subject per page",
    "Sessions run too long": "Short, finishable pages",
    "Subjects feel too intense": "Soft, familiar subjects"
  };

  var answers = { who: [], age: [], hard: [], themes: [], tools: [], format: [] };
  var note = "";
  var email = "";
  var consent = false;
  var current = 0;
  var done = false;

  var stage, progress, dots, count;

  function el(tag, cls, html) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }

  function renderProgress() {
    dots.innerHTML = "";
    for (var i = 0; i < STEPS.length; i++) {
      dots.appendChild(el("span", "sv-dot" + (i < current ? " is-done" : i === current ? " is-now" : "")));
    }
    count.textContent = "Step " + (current + 1) + " of " + STEPS.length;
  }

  function buildGroup(group) {
    var wrap = group.label ? el("fieldset", "sv-group") : el("div", "sv-group");
    if (group.label) wrap.appendChild(el("legend", "", esc(group.label)));
    var grid = el("div", "sv-grid");
    var max = group.max || 0;

    function refresh() {
      var chosen = answers[group.key];
      var full = max && chosen.length >= max;
      grid.querySelectorAll(".sv-choice").forEach(function (lab) {
        var input = lab.querySelector("input");
        var on = chosen.indexOf(input.value) !== -1;
        lab.classList.toggle("is-on", on);
        var off = !!(full && !on);
        lab.classList.toggle("is-off", off);
        input.disabled = off;
      });
      var hint = stage.querySelector(".sv-hint");
      if (max && hint) {
        hint.textContent = full ? "Two picked. Tap one again to swap it." : "Pick up to two.";
      }
      updateNextLabel();
    }

    group.options.forEach(function (opt) {
      var lab = el("label", "sv-choice");
      var input = el("input");
      input.type = "checkbox";
      input.name = group.key;
      input.value = opt;
      input.addEventListener("change", function () {
        var list = answers[group.key];
        var at = list.indexOf(opt);
        if (input.checked && at === -1) list.push(opt);
        if (!input.checked && at !== -1) list.splice(at, 1);
        refresh();
      });
      lab.appendChild(input);
      lab.appendChild(el("span", "sv-tick", TICK));
      lab.appendChild(el("span", "sv-label", esc(opt)));
      grid.appendChild(lab);
    });
    wrap.appendChild(grid);
    // Restore any earlier picks when coming back to a step.
    grid.querySelectorAll("input").forEach(function (i) { i.checked = answers[group.key].indexOf(i.value) !== -1; });
    refresh();
    return wrap;
  }

  function anyPicked(step) {
    return step.groups.some(function (g) { return answers[g.key].length > 0; });
  }

  function updateNextLabel() {
    var btn = document.getElementById("sv-next");
    var step = STEPS[current];
    if (!btn || step.final) return;
    btn.textContent = anyPicked(step) ? "Next" : "Skip";
  }

  function render() {
    stage.innerHTML = "";
    progress.hidden = false;
    renderProgress();
    var step = STEPS[current];
    var box = el("div", "sv-step");
    var h = el("h2", "", esc(step.title));
    h.tabIndex = -1;
    box.appendChild(h);
    box.appendChild(el("p", "sv-hint", esc(step.hint)));
    stage.appendChild(box);

    if (step.final) {
      buildFinal(box);
    } else {
      step.groups.forEach(function (g) { box.appendChild(buildGroup(g)); });
    }

    var nav = el("div", "sv-nav");
    var back = el("button", "sv-btn ghost", "Back");
    back.type = "button";
    back.hidden = current === 0;
    back.addEventListener("click", function () { saveFinal(); current -= 1; render(); });
    var next = el("button", "sv-btn primary", step.final ? "Send my picks" : "Next");
    next.type = "button";
    next.id = "sv-next";
    next.addEventListener("click", step.final ? submit : function () { current += 1; render(); });
    nav.appendChild(back);
    nav.appendChild(next);
    box.appendChild(nav);
    box.appendChild(el("p", "sv-error", "")).hidden = true;
    box.lastChild.id = "sv-error";
    box.lastChild.setAttribute("role", "alert");

    if (!step.final) updateNextLabel();
    h.focus({ preventScroll: true });
    var top = document.getElementById("sv-card").getBoundingClientRect().top + window.pageYOffset - 24;
    if (window.pageYOffset > top) window.scrollTo({ top: top, behavior: "smooth" });
  }

  function buildFinal(box) {
    var label = el("label", "sv-label-block", 'A theme, a page style, or something that never works for you <span class="sv-optional">(optional)</span>');
    label.setAttribute("for", "sv-note");
    var ta = el("textarea", "sv-field");
    ta.id = "sv-note";
    ta.maxLength = 400;
    ta.placeholder = "Write as little or as much as you like";
    ta.value = note;
    box.appendChild(label);
    box.appendChild(ta);

    var pack = el("div", "sv-pack");
    pack.appendChild(el("h3", "", "Want the free Quiet Time Starter Pack?"));
    pack.appendChild(el("p", "", "A one-page calming corner guide and three printable coloring pages."));
    var em = el("input", "sv-field");
    em.type = "email";
    em.id = "sv-email";
    em.placeholder = "Your email address (optional)";
    em.setAttribute("aria-label", "Your email address, optional");
    em.autocomplete = "email";
    em.value = email;
    // One-click Google / Facebook, when set up: fills the email box and ticks the consent box.
    if (window.CKSSocial && window.CKSSocial.configured()) {
      var social = el("div", "sv-social");
      pack.appendChild(social);
      window.CKSSocial.mount(social, {
        onEmail: function (addr) {
          email = addr;
          consent = true;
          var emBox = document.getElementById("sv-email");
          var cbBox = document.getElementById("sv-consent");
          if (emBox) emBox.value = addr;
          if (cbBox) cbBox.checked = true;
          var hint = document.getElementById("sv-social-note");
          if (hint) hint.hidden = false;
        }
      });
      var added = el("p", "sv-privacy", "Email added. Press Send my picks to finish, and the Starter Pack will follow.");
      added.id = "sv-social-note";
      added.hidden = true;
      pack.appendChild(added);
    }
    pack.appendChild(em);
    var cl = el("label", "sv-consent");
    var cb = el("input");
    cb.type = "checkbox";
    cb.id = "sv-consent";
    cb.checked = consent;
    cl.appendChild(cb);
    cl.appendChild(el("span", "", "Yes, email me the Starter Pack and one follow-up note. I can unsubscribe at any time by replying to either email."));
    pack.appendChild(cl);
    pack.appendChild(el("p", "sv-privacy", 'Your survey answers are anonymous. Your email is only used to send the pack, and is never saved with your answers. Read our <a href="/privacy/" style="color:inherit; text-decoration:underline;">Privacy Policy</a>.'));
    box.appendChild(pack);

    var trap = el("div", "trap", '<label>Leave this field empty <input type="text" id="sv-trap" tabindex="-1" autocomplete="off" /></label>');
    trap.setAttribute("aria-hidden", "true");
    box.appendChild(trap);
  }

  function saveFinal() {
    var ta = document.getElementById("sv-note");
    if (ta) note = ta.value.trim();
    var em = document.getElementById("sv-email");
    if (em) email = em.value.trim();
    var cb = document.getElementById("sv-consent");
    if (cb) consent = cb.checked;
  }

  function showError(msg) {
    var e = document.getElementById("sv-error");
    if (!e) return;
    e.textContent = msg;
    e.hidden = false;
  }

  function post(url, data) {
    // Apps Script web apps send no CORS headers we can read, so requests go
    // out "no-cors" and success is shown once the request leaves cleanly.
    return fetch(url, { method: "POST", mode: "no-cors", body: data });
  }

  function submit() {
    saveFinal();
    var err = document.getElementById("sv-error");
    if (err) err.hidden = true;

    var trap = document.getElementById("sv-trap");
    var botty = trap && trap.value.trim() !== "";

    if (consent && !isValidEmail(email)) {
      showError("Please add a valid email address, or untick the Starter Pack box.");
      return;
    }
    if (!SURVEY_URL || SURVEY_URL.indexOf("PASTE_YOUR") === 0) {
      showError("Our survey inbox is still being set up. Please check back soon.");
      return;
    }

    var btn = document.getElementById("sv-next");
    if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }

    var fd = new FormData();
    fd.append("who", answers.who.join("; "));
    fd.append("age", answers.age.join("; "));
    fd.append("hard", answers.hard.join("; "));
    fd.append("themes", answers.themes.join("; "));
    fd.append("tools", answers.tools.join("; "));
    fd.append("format", answers.format.join("; "));
    fd.append("note", note);
    fd.append("page", "survey");
    fd.append("website", botty ? "bot" : "");

    post(SURVEY_URL, fd).then(function () {
      if (consent && !botty) {
        var sp = new FormData();
        sp.append("email", email);
        sp.append("website", "");
        post(STARTER_URL, sp).catch(function () {});
      }
      showDone();
    }).catch(function () {
      if (btn) { btn.disabled = false; btn.textContent = "Send my picks"; }
      showError("Something went quietly wrong. Please try again in a moment.");
    });
  }

  function recipeChips() {
    var chips = [];
    answers.hard.forEach(function (h) { if (HARD_TO_RECIPE[h] && chips.length < 3) chips.push(HARD_TO_RECIPE[h]); });
    if (!chips.length) chips.push("Calm pages with room to grow");
    answers.themes.forEach(function (t) { chips.push(t); });
    return chips;
  }

  function showDone() {
    done = true;
    progress.hidden = true;
    stage.innerHTML = "";
    var box = el("div", "sv-done");
    var h = el("h2", "", "Thank you. Your calm picks are in.");
    h.tabIndex = -1;
    box.appendChild(h);
    box.appendChild(el("p", "", "Here is the kind of page your answers point to."));
    var rec = el("div", "sv-recipe");
    rec.appendChild(el("h3", "", "Your calm recipe"));
    var chips = el("div", "sv-chips");
    recipeChips().forEach(function (c, i) {
      var chip = el("span", "sv-chip", esc(c));
      chip.style.animationDelay = (i * 90) + "ms";
      chips.appendChild(chip);
    });
    rec.appendChild(chips);
    box.appendChild(rec);
    if (consent) {
      box.appendChild(el("p", "", "Your Quiet Time Starter Pack is on its way. If it does not appear in a few minutes, please check your spam folder."));
    }
    var link = el("a", "sv-btn primary sv-link", "See the coloring books");
    link.href = "https://calmkidssensory.com/links/";
    box.appendChild(link);
    box.appendChild(el("p", "sv-note", "This list is a gentle suggestion, not medical or therapeutic advice."));
    stage.appendChild(box);
    h.focus({ preventScroll: true });
  }

  document.addEventListener("DOMContentLoaded", function () {
    stage = document.getElementById("sv-stage");
    progress = document.getElementById("sv-progress");
    dots = document.getElementById("sv-dots");
    count = document.getElementById("sv-count");
    if (!stage) return;
    render();
  });
})();
