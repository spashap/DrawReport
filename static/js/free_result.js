/* The parent's verdict on one interpretation.

   Fire-and-forget: the buttons are replaced with a thank-you the moment they are pressed,
   without waiting for the request. A parent who taps "not my child" and then watches a
   spinner learns that their opinion is being processed rather than heard, and the whole
   point of this control is that it costs them nothing. If the request fails, we lose one
   data point - which is cheaper than making the reader wait. */
(function () {
  "use strict";
  document.querySelectorAll("[data-interp]").forEach(function (box) {
    var id = box.getAttribute("data-interp");
    box.querySelectorAll("[data-vote]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var v = btn.getAttribute("data-vote");
        box.querySelector(".free-vote").hidden = true;
        var q = box.querySelector(".free-vote-q");
        if (q) { q.hidden = true; }
        var thanks = box.querySelector("[data-thanks]");
        if (thanks) { thanks.hidden = false; }
        try {
          fetch("/free/vote/" + id, {
            method: "POST", body: new URLSearchParams({ vote: v })
          }).catch(function () {});
        } catch (e) {}
      });
    });
  });
})();
