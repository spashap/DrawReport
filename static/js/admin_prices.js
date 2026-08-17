/* Live discount recalculation on the admin Prices page, so the percentage is visible
   before saving. A separate file rather than an inline <script> so the admin templates
   carry no logic of their own and the file is cache-busted by ?v= like the rest. */
(function () {
  "use strict";
  document.querySelectorAll('.form-card[data-product]').forEach(function (card) {
    var oldIn = card.querySelector('[data-price-old]');
    var newIn = card.querySelector('[data-price-new]');
    var note = card.querySelector('[data-discount-note]');
    if (!oldIn || !newIn || !note) { return; }
    function update() {
      var o = parseInt(oldIn.value, 10), n = parseInt(newIn.value, 10);
      if (!o) { note.textContent = 'No struck-through price is shown.'; return; }
      if (!n || o <= n) {
        note.textContent = 'The pre-discount price must be higher than the payable price.';
        return;
      }
      note.textContent = 'Discount shown on the site: −' + Math.round((o - n) * 100 / o) + '%';
    }
    oldIn.addEventListener('input', update);
    newIn.addEventListener('input', update);
  });
})();
