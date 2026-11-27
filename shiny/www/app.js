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
  // The values found reliably arrive ticked: report them once the list is on the page
  if (window.jQuery) jQuery(document).on('shiny:value', function (e) {
    if (e.name === 'details_result') setTimeout(report, 0);
  });
})();

// Leaving or reloading the page ends the session and deletes its files, so the browser asks first while
// there are files or results (the server says when there are).
(function () {
  window.faireHasWork = false;
  document.addEventListener('DOMContentLoaded', function () {
    if (window.Shiny && Shiny.addCustomMessageHandler)
      Shiny.addCustomMessageHandler('has_work', function (on) { window.faireHasWork = Array.isArray(on) ? !!on[0] : !!on; });
  });
  window.addEventListener('beforeunload', function (e) {
    if (!window.faireHasWork) return;
    e.preventDefault();
    e.returnValue = '';
  });
})();

// The status of each FAIRe mapper step, from the journey (R/journey.R), shown after its name in the step
// list: a sign and a word, as in the journey bar, so it does not rest on colour alone.
(function () {
  var SIGN = {done: '\u2713', todo: '!', stale: '\u21bb', blocked: '\u2026', optional: '\u25cb', skip: '\u2013'};
  function show(st) {
    document.querySelectorAll('#mapper_steps .nav-link').forEach(function (a) {
      var key = (a.textContent.trim().match(/^([a-e])\./) || [])[1];
      if (!key) return;
      var s = st[key];
      var tag = a.querySelector('.step-status');
      if (!s || !s.status) { if (tag) tag.remove(); return; }
      if (!tag) { tag = document.createElement('span'); a.appendChild(tag); }
      tag.className = 'step-status st-' + s.status;
      tag.textContent = (SIGN[s.status] || '') + ' ' + s.word;
      tag.title = s.detail || '';
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    if (window.Shiny && Shiny.addCustomMessageHandler) Shiny.addCustomMessageHandler('step_status', show);
  });
})();

// An error about a field is shown under it too, and the field is brought into view; the note goes when the
// field changes. A check made as you type (field_check) shows a note under the field, or clears it.
(function () {
  function holder(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    return el.closest('.shiny-input-container') || el.closest('.form-group') || el.parentElement;
  }
  function note(id, msg, cls) {
    var h = holder(id);
    if (!h) return;
    var old = h.querySelector(':scope > .' + cls);
    if (old) old.remove();
    h.classList.toggle('has-' + cls, !!msg);
    if (!msg) return;
    var d = document.createElement('div');
    d.className = cls;
    d.setAttribute('role', cls === 'field-error' ? 'alert' : 'status');
    d.textContent = msg;
    h.appendChild(d);
    if (cls === 'field-error') {
      h.scrollIntoView({block: 'center', behavior: 'smooth'});
      var clear = function () { note(id, '', cls); h.removeEventListener('change', clear); h.removeEventListener('input', clear); };
      h.addEventListener('change', clear);
      h.addEventListener('input', clear);
    }
  }
  document.addEventListener('DOMContentLoaded', function () {
    if (!(window.Shiny && Shiny.addCustomMessageHandler)) return;
    Shiny.addCustomMessageHandler('field_error', function (m) { note(m.id, m.msg, 'field-error'); });
    Shiny.addCustomMessageHandler('field_check', function (m) { note(m.id, m.msg, 'field-check'); });
  });
})();

// Accessibility: focus goes back to the button that opened a dialog (such as a file preview) when it
// closes, and icons that only decorate a label are hidden from screen readers.
(function () {
  var opener = null;
  document.addEventListener('focusin', function (e) {
    if (!e.target.closest('.modal')) opener = e.target;
  });
  if (window.jQuery) {
    jQuery(document).on('hidden.bs.modal', function () {
      if (opener && document.body.contains(opener)) opener.focus();
    });
  }
  function quietIcons(root) {
    (root || document).querySelectorAll('i.fa[aria-label], i.fas[aria-label], i.far[aria-label], i.fa-solid[aria-label]')
      .forEach(function (i) {
        if (i.getAttribute('role') === 'img') return;
        i.removeAttribute('aria-label');
        i.setAttribute('aria-hidden', 'true');
      });
  }
  document.addEventListener('DOMContentLoaded', function () { quietIcons(); });
  if (window.jQuery) jQuery(document).on('shiny:value shiny:message', function () { setTimeout(quietIcons, 0); });

  // A table that scrolls can be scrolled from the keyboard: its scrolling part takes focus.
  if (window.jQuery) {
    jQuery(document).on('init.dt draw.dt', function (e, settings) {
      jQuery(settings.nTableWrapper).find('.dataTables_scrollBody').attr('tabindex', '0');
    });
  }
})();

// Sample types: Other already includes every sample type's fields, so it is ticked on its own. Ticking Other
// clears the other boxes, and ticking another box clears Other. Shiny reads the boxes when the clicked box
// changes, so a change event is sent again once the boxes are set.
(function () {
  var groups = ['fa_sample_type', 'map_sample_types'];
  document.addEventListener('change', function (e) {
    var box = e.target;
    if (!box || box.type !== 'checkbox' || !box.checked) return;
    var group = box.closest('.shiny-input-checkboxgroup');
    if (!group || groups.indexOf(group.id) < 0) return;
    var cleared = false;
    group.querySelectorAll('input[type=checkbox]').forEach(function (other) {
      if (other === box || !other.checked) return;
      if (box.value === 'other' || other.value === 'other') { other.checked = false; cleared = true; }
    });
    if (cleared && window.jQuery) window.jQuery(box).trigger('change');
  });
})();

// Brings an output into view, such as the workbook after it is written from the button below the tables
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    if (!(window.Shiny && Shiny.addCustomMessageHandler)) return;
    Shiny.addCustomMessageHandler('scroll_to', function (id) {
      var el = document.getElementById(Array.isArray(id) ? id[0] : id);
      if (el) el.scrollIntoView({block: 'start', behavior: 'smooth'});
    });
  });
})();

// After going to a stage from the journey bar or the next-step card, the page starts at its top and keyboard
// focus moves to its first heading, or to the part named (the missing project terms, say).
(function () {
  function land(id) {
    setTimeout(function () {
      var to = id && document.getElementById(Array.isArray(id) ? id[0] : id);
      if (!to) {
        var panes = Array.prototype.filter.call(document.querySelectorAll('.tab-pane.active'), function (p) { return p.offsetParent !== null; });
        var pane = panes[panes.length - 1];
        to = pane && pane.querySelector('.card-header, h4, h5');
        window.scrollTo({top: 0});
      } else {
        to.scrollIntoView({block: 'start', behavior: 'smooth'});
      }
      if (to) { if (!to.hasAttribute('tabindex')) to.setAttribute('tabindex', '-1'); to.focus({preventScroll: true}); }
    }, 350);
  }
  document.addEventListener('DOMContentLoaded', function () {
    if (window.Shiny && Shiny.addCustomMessageHandler) Shiny.addCustomMessageHandler('after_go', land);
  });
})();

// c. Review: a row whose decision is changed stays in view when its group (the mapper's accepted matches, or
// the decisions carried over) is hidden
document.addEventListener('change', function (e) {
  var row = e.target && e.target.closest && e.target.closest('#review-grid .rv-row');
  if (row && e.target.tagName === 'SELECT') row.classList.add('rv-changed');
});

// Bootstrap 5.2 and later open a navbar menu when a tab inside it is shown, which leaves Make a workbook
// dropped down over the page each time the Next step box, the journey bar or a Start page link opens a
// FAIRe mapper step. The menu is for choosing; once a tab is shown, any open navbar menu is closed.
(function () {
  function closeMenus() {
    document.querySelectorAll('.navbar .dropdown-menu.show').forEach(function (m) {
      var outer = m.closest('.dropdown');
      var toggle = outer && outer.querySelector('.dropdown-toggle');
      m.classList.remove('show');
      if (toggle) { toggle.classList.remove('show'); toggle.setAttribute('aria-expanded', 'false'); }
      if (outer) outer.removeAttribute('aria-expanded');
    });
  }
  document.addEventListener('shown.bs.tab', function () { setTimeout(closeMenus, 0); });
  if (window.jQuery) jQuery(document).on('shown.bs.tab', function () { setTimeout(closeMenus, 0); });
})();

// c. Review: opens or closes a fold of rows (the high-confidence matches, or the decisions carried over),
// and tells the app, so the fold stays as it is when the review is drawn again
window.faireToggleGroup = function (id) {
  var btn = document.getElementById(id + '_btn'), rows = document.getElementById(id + '_rows');
  if (!btn || !rows) return;
  var open = btn.getAttribute('aria-expanded') !== 'true';
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  rows.classList.toggle('collapsed', !open);
  if (window.Shiny && Shiny.setInputValue) Shiny.setInputValue(id, open);
};
