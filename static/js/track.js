/* First-party site analytics. Lives SEPARATELY from the GA4 snippet on purpose:
   if the beacon sat inside `{% if ga_id %}`, then without a third-party measurement
   id our own analytics - including the admin funnel - would silently switch off.
   Only our own data is collected here; we mirror goals into GA4 when it is present.

   Loaded from <head> WITHOUT defer: pages (order_success) call window.drGoal from an
   inline script while the document is still parsing, and defer would run this file
   later. The file is small and cached - that costs less than losing goals.

   What we send:
     goal    - clicks/submits on data-goal / data-goal-submit;
     engaged - first interaction OR 15s of visible time;
     scroll_25|50|75|100 - scroll depth (once per page);
     sec_<name> - a [data-track-section] block was actually on screen.
   We always add `p` (the page path): the request itself goes to /t/e, and without
   that field the database would say everything on the site happens on /t/e.
*/
(function () {
  "use strict";

  var sizeSent = false;

  function beacon(fields) {
    var data = fields || {};
    data.p = location.pathname;
    if (!sizeSent) {
      sizeSent = true;
      // SCREEN width from the client: the user-agent knows nothing about layout
      // (an iPad in desktop mode, a narrow laptop window) - and layout breaks by width.
      data.sw = String(window.innerWidth || (screen && screen.width) || 0);
      if ("ontouchstart" in window || navigator.maxTouchPoints > 0) { data.t = "1"; }
    }
    try { navigator.sendBeacon("/t/e", new URLSearchParams(data)); } catch (e) {}
  }
  window.drBeacon = beacon;

  window.drGoal = function (goal, params) {
    if (!goal) { return; }
    if (window.gtag) {
      try { gtag("event", goal, params || {}); } catch (e) {}
    }
    beacon({ g: goal });
  };

  // --- Click/submit goals. Delegated on document: a new button = a new data-goal
  //     attribute, no JS to write (works for dynamically added blocks too).
  document.addEventListener("click", function (ev) {
    var el = ev.target.closest && ev.target.closest("[data-goal]");
    if (el) { window.drGoal(el.getAttribute("data-goal")); }
  }, true);
  document.addEventListener("submit", function (ev) {
    var f = ev.target.closest && ev.target.closest("[data-goal-submit]");
    if (f) { window.drGoal(f.getAttribute("data-goal-submit")); }
  }, true);

  // --- Engagement: one beacon at the FIRST of - an interaction OR 15s of VISIBLE
  //     time. This is the GA4 engaged-session model. Background and prerendered tabs
  //     accumulate no time, so a prerender does not turn into a visitor.
  (function () {
    var sent = false, visibleSec = 0, THRESHOLD = 15, tick = null;
    var EVENTS = ["scroll", "wheel", "click", "keydown", "touchstart"];
    function cleanup() {
      EVENTS.forEach(function (e) { document.removeEventListener(e, fire, true); });
      if (tick) { clearInterval(tick); tick = null; }
    }
    function fire() {
      if (sent) { return; }
      sent = true;
      beacon({ engaged: "1" });
      cleanup();
    }
    EVENTS.forEach(function (e) {
      document.addEventListener(e, fire, { capture: true, passive: true });
    });
    tick = setInterval(function () {
      if (document.visibilityState === "visible" && ++visibleSec >= THRESHOLD) { fire(); }
    }, 1000);
  })();

  // --- Scroll depth. Measured against the SCROLLABLE distance, not the document
  //     height: otherwise 100% is unreachable on a short screen, while on a long
  //     mobile page the first 25% is reached in the very first swipe.
  //     If the page is shorter than the screen (nothing to scroll) we send NOTHING:
  //     "100% scrolled" would there mean "the person did nothing", and depth would
  //     stop meaning anything.
  (function () {
    var MARKS = [25, 50, 75, 100], next = 0, ticking = false;
    function scrollable() {
      var h = Math.max(document.body ? document.body.scrollHeight : 0,
                       document.documentElement.scrollHeight);
      return h - window.innerHeight;
    }
    function check() {
      ticking = false;
      var max = scrollable();
      if (max < 200) { return; }              // nothing to measure
      var pct = ((window.pageYOffset || document.documentElement.scrollTop) / max) * 100;
      while (next < MARKS.length && pct >= MARKS[next] - 1) {
        window.drGoal("scroll_" + MARKS[next]);
        next += 1;
      }
      if (next >= MARKS.length) {
        window.removeEventListener("scroll", onScroll, true);
      }
    }
    function onScroll() {
      if (!ticking) { ticking = true; requestAnimationFrame(check); }
    }
    window.addEventListener("scroll", onScroll, { capture: true, passive: true });
  })();

  // --- Block visibility: [data-track-section="name"] -> goal sec_<name>.
  //     We require HALF A SECOND on screen and half the block visible: on mobile an
  //     inertial swipe flies past the whole page in a second, and without the dwell
  //     "saw the pricing" would mean "scrolled past the pricing".
  (function () {
    if (!("IntersectionObserver" in window)) { return; }
    var DWELL = 500, timers = {};
    function start() {
      var nodes = document.querySelectorAll("[data-track-section]");
      if (!nodes.length) { return; }
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          var name = en.target.getAttribute("data-track-section");
          if (!name) { return; }
          if (en.isIntersecting) {
            if (timers[name]) { return; }
            timers[name] = setTimeout(function () {
              window.drGoal("sec_" + name);
              io.unobserve(en.target);            // once per page load
            }, DWELL);
          } else if (timers[name]) {
            clearTimeout(timers[name]);
            timers[name] = null;
          }
        });
      }, { threshold: 0.5 });
      nodes.forEach(function (n) { io.observe(n); });
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  })();
})();
