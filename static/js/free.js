/* The free wizard: three questions, one screen each, then the summary, upload and wait.

   Design rules this file exists to keep:
   * ONE STEP VISIBLE AT A TIME. The steps are hidden with a class, not by scrolling -
     a parent on a phone must never see two questions at once.
   * The summary is fetched from the SERVER and injected as HTML. It is never assembled
     here: the one absolute rule of that text is that it is joined only at paragraph
     boundaries, and a bug in a client-side assembler would produce exactly the artifact
     the whole product exists to avoid.
   * Every dead end is an EVENT. A parent who answers everything and then hits a size or
     format limit used to vanish from the funnel with no reason recorded.
*/
(function () {
  "use strict";

  var T = window.FREE_TEXT || { stages: [], errors: {} };
  var wizard = document.getElementById("free-wizard");
  if (!wizard) { return; }

  var steps = Array.prototype.slice.call(wizard.querySelectorAll(".wizard__step"));
  var dots = Array.prototype.slice.call(document.querySelectorAll("#free-dots .car-dot"));
  var at = 0;
  var state = { name: "", band: "", address: "they", concern: "", duration: "", text: "" };

  function show(i) {
    at = i;
    steps.forEach(function (s, n) { s.classList.toggle("is-on", n === i); });
    dots.forEach(function (d, n) { d.classList.toggle("is-active", n <= Math.min(i, 2)); });
    window.scrollTo(0, 0);
    var focusable = steps[i].querySelector("input[type=text], textarea");
    if (focusable && i === 0) { try { focusable.focus({ preventScroll: true }); } catch (e) {} }
  }

  function val(sel) {
    var el = document.querySelector(sel + " input:checked");
    return el ? el.value : "";
  }

  function err(id, message) {
    var el = document.getElementById(id);
    if (!el) { return; }
    el.textContent = message || "";
    el.hidden = !message;
  }

  // --- Step 1 -> 2
  wizard.addEventListener("click", function (ev) {
    var next = ev.target.closest("[data-next]");
    if (next) {
      var step = parseInt(next.getAttribute("data-next"), 10);
      if (step === 0) {
        state.name = (document.getElementById("f-name").value || "").trim();
        state.band = val("#f-band");
        state.address = val("#f-address") || "they";
        if (!state.name) { err("f-err0", "Please add your child's first name."); return; }
        if (!state.band) { err("f-err0", "Please choose an age."); return; }
        err("f-err0", "");
        // The pronoun is carried into every question that follows, so a parent never
        // reads "he" about their daughter on the way through the wizard.
        applyPronoun();
        show(1);
      } else if (step === 2) {
        state.duration = val("#f-duration");
        state.text = (document.getElementById("f-text").value || "").trim();
        submitSummary();
      }
      return;
    }
    var back = ev.target.closest("[data-back]");
    if (back) { show(Math.max(0, at - 1)); }
  });

  // --- Step 2: choosing moves straight on. A "next" button here would be one tap the
  //     parent does not need to make.
  var concernBox = document.getElementById("f-concern");
  if (concernBox) {
    concernBox.addEventListener("change", function () {
      state.concern = val("#f-concern");
      if (!state.concern) { return; }
      var q = document.getElementById("f-dur-q");
      if (state.concern === "stopped" && T.stoppedQuestion && q) {
        q.textContent = pronoun(T.stoppedQuestion);
      }
      // "Nothing worries me" has no duration and no free text to add - skip straight to
      // the summary rather than asking how long nothing has been wrong.
      if (state.concern === "neutral") { submitSummary(); return; }
      setTimeout(function () { show(2); }, 120);
    });
  }

  // --- Pronoun agreement, mirroring config/free_texts.g() on the server.
  var FORMS = {
    she: { sub: "she", obj: "her", poss: "her", refl: "herself", s: "s", is: "is", was: "was", has: "has", does: "does" },
    he: { sub: "he", obj: "him", poss: "his", refl: "himself", s: "s", is: "is", was: "was", has: "has", does: "does" },
    they: { sub: "they", obj: "them", poss: "their", refl: "themselves", s: "", is: "are", was: "were", has: "have", does: "do" }
  };
  function pronoun(text) {
    var f = FORMS[state.address] || FORMS.they;
    return String(text).replace(/\{(\w+)\}/g, function (m, k) {
      return Object.prototype.hasOwnProperty.call(f, k) ? f[k] : m;
    });
  }
  function applyPronoun() {
    document.querySelectorAll("[data-raw]").forEach(function (el) {
      el.textContent = pronoun(el.getAttribute("data-raw"));
    });
    ["f-concern-q", "f-text-q"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) { return; }
      if (!el.getAttribute("data-raw0")) { el.setAttribute("data-raw0", el.textContent); }
      el.textContent = pronoun(el.getAttribute("data-raw0"));
    });
  }

  // --- The summary comes from the server.
  function submitSummary() {
    var body = new URLSearchParams({
      name: state.name, band: state.band, address: state.address,
      concern: state.concern, duration: state.duration, parent_text: state.text
    });
    var btn = wizard.querySelector('[data-next="2"]');
    if (btn) { btn.disabled = true; }
    fetch("/free/summary", { method: "POST", body: body })
      .then(function (r) { return r.text().then(function (t) { return { ok: r.ok, t: t }; }); })
      .then(function (res) {
        if (btn) { btn.disabled = false; }
        if (!res.ok) { err("f-err0", T.errors.other); show(0); return; }
        document.getElementById("f-summary").innerHTML = res.t;
        show(3);
        wireUpload();
      })
      .catch(function () {
        if (btn) { btn.disabled = false; }
        err("f-err0", T.errors.network);
      });
  }

  // --- Upload + email in one step.
  function wireUpload() {
    var box = document.getElementById("f-upload");
    if (!box) { return; }
    var token = box.getAttribute("data-token");
    var fileIn = document.getElementById("f-file");
    var go = document.getElementById("f-go");
    var preview = box.querySelector(".file-drop .preview");

    if (fileIn) {
      fileIn.addEventListener("change", function () {
        var f = fileIn.files && fileIn.files[0];
        if (!f || !preview) { return; }
        // A preview before upload: the commonest failure is photographing the wrong
        // thing, and seeing it is cheaper for everyone than a rejection afterwards.
        try {
          preview.src = URL.createObjectURL(f);
          preview.hidden = false;
          box.querySelector(".fd-icon").hidden = true;
        } catch (e) {}
      });
    }

    if (!go) { return; }
    go.addEventListener("click", function () {
      var f = fileIn && fileIn.files && fileIn.files[0];
      var email = (document.getElementById("f-email").value || "").trim();
      if (!f) { upErr(T.errors.no_file); return; }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { upErr(T.errors.email); return; }
      upErr("");
      go.disabled = true;
      var fd = new FormData();
      fd.append("file", f);
      fd.append("email", email);
      fetch("/free/upload/" + token, { method: "POST", body: fd })
        .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
        .then(function (res) {
          go.disabled = false;
          if (res.s === 200 && res.j.ok) {
            startWait(token, box.getAttribute("data-wait-hint"), f);
            return;
          }
          if (res.j && res.j.error === "limit" && res.j.token) {
            window.location.href = "/free/r/" + res.j.token;
            return;
          }
          upErr(T.errors[(res.j && res.j.error)] || T.errors.other);
        })
        .catch(function () { go.disabled = false; upErr(T.errors.network); });
    });

    var nd = document.getElementById("f-nodraw-btn");
    if (nd) {
      nd.addEventListener("click", function () {
        var email = (document.getElementById("f-nodraw-email").value || "").trim();
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { return; }
        fetch("/free/save-place/" + nd.getAttribute("data-token"), {
          method: "POST", body: new URLSearchParams({ email: email })
        }).then(function () {
          document.getElementById("f-nodraw-ok").hidden = false;
          nd.disabled = true;
        }).catch(function () {});
      });
    }

    function upErr(m) {
      var el = document.getElementById("f-uperr");
      el.textContent = m || "";
      el.hidden = !m;
    }
  }

  // --- The waiting screen. The bar is honest about being an estimate: it eases toward
  //     90% and stops there rather than pretending to know when the model will finish.
  function startWait(token, hint, file) {
    wizard.hidden = true;
    var wait = document.getElementById("free-wait");
    wait.hidden = false;
    window.scrollTo(0, 0);
    if (hint) { document.getElementById("w-hint").textContent = hint; }
    var photo = document.getElementById("w-photo");
    if (file && photo) {
      try { photo.src = URL.createObjectURL(file); } catch (e) { photo.hidden = true; }
    } else if (photo) { photo.hidden = true; }
    var link = document.getElementById("w-link");
    if (link) { link.href = link.textContent = location.origin + "/free/r/" + token; }

    var t0 = Date.now(), stage = 0;
    var bar = document.getElementById("w-bar");
    var stageEl = document.getElementById("w-stage");
    var tick = setInterval(function () {
      var secs = (Date.now() - t0) / 1000;
      var pct = Math.min(90, 100 * (1 - Math.exp(-secs / 25)));
      if (bar) { bar.style.width = pct.toFixed(0) + "%"; }
      var want = Math.min(T.stages.length - 1, Math.floor(secs / 9));
      if (want !== stage && T.stages[want]) {
        stage = want;
        stageEl.childNodes[0].nodeValue = T.stages[want] + " ";
      }
      if (secs > 75) { document.getElementById("w-late").hidden = false; }
    }, 1000);

    (function poll() {
      fetch("/free/status/" + token)
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j.status === "done" || j.status === "insufficient" || j.status === "failed") {
            clearInterval(tick);
            if (bar) { bar.style.width = "100%"; }
            window.location.href = j.url;
            return;
          }
          setTimeout(poll, 2000);
        })
        .catch(function () { setTimeout(poll, 4000); });
    })();
  }
})();
