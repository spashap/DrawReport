/* The standalone waiting page (/free/r/<token> opened before the reading is ready).

   Separate from free.js because it has no wizard state: it only polls and redirects.
   It exists so the link we email works while the queue is still running, instead of
   showing the parent a half-rendered result page. */
(function () {
  "use strict";
  var box = document.getElementById("wait-standalone");
  if (!box) { return; }
  var token = box.getAttribute("data-token");
  var bar = document.getElementById("w-bar");
  var t0 = Date.now();

  setInterval(function () {
    var secs = (Date.now() - t0) / 1000;
    // Eases toward 90% and stops: the bar is honest about being an estimate rather than
    // pretending to know when the model will finish.
    if (bar) { bar.style.width = Math.min(90, 100 * (1 - Math.exp(-secs / 25))).toFixed(0) + "%"; }
  }, 1000);

  (function poll() {
    fetch("/free/status/" + token)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.status === "done" || j.status === "insufficient" || j.status === "failed") {
          if (bar) { bar.style.width = "100%"; }
          window.location.reload();
          return;
        }
        setTimeout(poll, 3000);
      })
      .catch(function () { setTimeout(poll, 5000); });
  })();
})();
