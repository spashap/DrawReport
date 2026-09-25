/* Order form: reveal drawing blocks one at a time (up to the product max), photo preview,
   a double-submit guard, and the form_started goal.

   Ported in part from Golos static/js/order.js. Deliberately NOT ported here: the
   localStorage draft, the email-typo suggester and the custom combobox - each is a
   behaviour change, not part of making this form render and measure correctly. */
(function () {
  "use strict";
  var form = document.getElementById("order-form");
  if (!form) { return; }
  var blocks = Array.prototype.slice.call(form.querySelectorAll(".drawing-block"));
  var addBtn = document.getElementById("add-draw");

  function visibleCount() {
    return blocks.filter(function (b) { return !b.hidden; }).length;
  }
  function refresh() {
    if (addBtn) { addBtn.hidden = visibleCount() >= blocks.length; }
  }

  if (addBtn) {
    addBtn.addEventListener("click", function () {
      for (var i = 0; i < blocks.length; i++) {
        if (blocks[i].hidden) { blocks[i].hidden = false; break; }
      }
      refresh();
    });
  }

  blocks.forEach(function (block) {
    var rm = block.querySelector(".db-remove");
    if (rm) {
      rm.addEventListener("click", function (e) {
        e.preventDefault();
        block.hidden = true;
        block.querySelectorAll("input, textarea, select").forEach(function (el) { el.value = ""; });
        var img = block.querySelector("img.preview");
        if (img) { img.hidden = true; img.removeAttribute("src"); }
        refresh();
      });
    }

    var fileInput = block.querySelector('input[type="file"]');
    if (!fileInput) { return; }
    var txt = block.querySelector(".fd-text");
    var txt0 = txt ? txt.textContent : "";
    fileInput.addEventListener("change", function () {
      var img = block.querySelector("img.preview");
      var f = fileInput.files && fileInput.files[0];
      if (!f) { if (txt) { txt.textContent = txt0; } return; }
      if (f.size > 15 * 1024 * 1024) {
        fileInput.value = "";
        if (txt) { txt.textContent = "This photo is larger than 15 MB. Please choose a smaller one."; }
        if (window.drGoal) { window.drGoal("order_file_too_big"); }
        return;
      }
      if (img && f.type && f.type.indexOf("image/") === 0 && f.type !== "image/heic") {
        try { img.src = URL.createObjectURL(f); img.hidden = false; } catch (e) {}
      } else if (img) {
        img.hidden = true;
      }
      if (txt) { txt.textContent = "Photo added: " + f.name; }
    });
  });

  // Double-submit guard: a slow photo upload invites an impatient second tap.
  var submitBtn = form.querySelector('button[type="submit"]');
  form.addEventListener("submit", function (e) {
    if (e.defaultPrevented || !submitBtn) { return; }
    setTimeout(function () {       // after every other submit handler (goals included)
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending…";
    }, 0);
  });
  // Back/forward cache restores the disabled button: re-enable it.
  window.addEventListener("pageshow", function () {
    if (submitBtn && submitBtn.disabled) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.getAttribute("data-label") || submitBtn.textContent; }
  });
  if (submitBtn) { submitBtn.setAttribute("data-label", submitBtn.textContent); }

  // form_started: once per page load, on the first real input (typing, a select, a
  // file). Through drGoal like every other goal, so it carries the page path and is
  // stored as click:form_started - the marker app/admin_funnels.py counts. It used to be
  // a raw sendBeacon with no path, stored under a name the funnel never matched.
  var started = false;
  function onFirstInput() {
    if (started) { return; }
    started = true;
    if (window.drGoal) { window.drGoal("form_started"); }
  }
  form.addEventListener("input", onFirstInput);
  form.addEventListener("change", onFirstInput);

  refresh();
})();
