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
  document.addEventListener('shiny:connected', function () {
    Shiny.addCustomMessageHandler('md_tick', function (on) {
      document.querySelectorAll('.md-keep').forEach(function (el) { el.checked = !!on; });
      report();
    });
  });
})();
