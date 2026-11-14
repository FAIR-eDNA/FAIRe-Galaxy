// The method details to keep (step d): the ticked boxes, reported to the server as their row numbers.
(function () {
  function report() {
    var kept = [];
    document.querySelectorAll('.md-keep:checked').forEach(function (el) {
      kept.push(parseInt(el.id.replace('md_keep_', ''), 10));
    });
    if (window.Shiny && Shiny.setInputValue) Shiny.setInputValue('md_kept', kept);
  }
  document.addEventListener('change', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('md-keep')) report();
  });
  // Shiny announces its connection as a jQuery event, which addEventListener does not hear, so the handler is
  // registered once the page has loaded (Shiny takes handlers before it connects)
  function tick(msg) {
    var on = Array.isArray(msg) ? msg[0] : msg;   // R may send a one-item list
    // "reliable" ticks only the values found reliably: the others each need their own tick
    document.querySelectorAll('.md-keep').forEach(function (el) {
      if (on === 'reliable') { if (el.dataset.tier === 'reliable') el.checked = true; } else { el.checked = !!on; }
    });
    report();
  }
  document.addEventListener('DOMContentLoaded', function () {
    if (window.Shiny && Shiny.addCustomMessageHandler) Shiny.addCustomMessageHandler('md_tick', tick);
  });
})();
