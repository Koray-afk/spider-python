"""Default offline interaction JavaScript (no Gemini required)."""

DEFAULT_INTERACTION_JS = r"""
(function() {
  'use strict';

  function findPanel(tab) {
    var ctrl = tab.getAttribute('aria-controls');
    if (!ctrl) return null;
    return document.getElementById(ctrl)
      || document.getElementById(ctrl.replace(/-tabpanel$/, '-panel'))
      || document.getElementById(ctrl.replace(/-tab$/, ''));
  }

  function activateTab(tab) {
    var tablist = tab.closest('[role=tablist]') || tab.parentElement;
    if (!tablist) return;
    tablist.querySelectorAll('[role=tab]').forEach(function(t) {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
      t.setAttribute('tabindex', '-1');
    });
    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    tab.setAttribute('tabindex', '0');
    var panel = findPanel(tab);
    if (!panel) return;
    var container = panel.parentElement;
    container.querySelectorAll('[role=tabpanel]').forEach(function(p) {
      p.classList.remove('active', 'show');
      p.style.display = 'none';
      p.hidden = true;
    });
    panel.classList.add('active', 'show');
    panel.style.display = '';
    panel.hidden = false;
  }

  function closeDropdowns() {
    document.querySelectorAll('.dropdown.show').forEach(function(d) {
      d.classList.remove('show');
      var m = d.querySelector('.dropdown-menu');
      if (m) { m.classList.remove('show'); m.style.display = 'none'; }
    });
  }

  function openDropdown(wrapper) {
    var menu = wrapper.querySelector('.dropdown-menu');
    if (!menu) return;
    wrapper.classList.add('show');
    menu.classList.add('show');
    menu.style.cssText += ';display:block!important;position:absolute;z-index:9990;'
      + 'background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:4px;'
      + 'box-shadow:0 4px 12px rgba(0,0,0,.12);padding:4px 0;min-width:140px;';
  }

  function toggleAccordion(el) {
    var panelId = el.getAttribute('aria-controls');
    var panel = panelId && document.getElementById(panelId);
    var open = el.getAttribute('aria-expanded') === 'true';
    el.setAttribute('aria-expanded', open ? 'false' : 'true');
    el.classList.toggle('collapsed', open);
    if (panel) {
      panel.hidden = open;
      panel.classList.toggle('show', !open);
      panel.style.display = open ? 'none' : '';
    }
  }

  function showToast(msg) {
    var old = document.getElementById('_offline_toast');
    if (old) old.remove();
    var el = document.createElement('div');
    el.id = '_offline_toast';
    el.textContent = msg;
    el.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);'
      + 'background:rgba(0,0,0,.8);color:#fff;padding:10px 20px;border-radius:20px;'
      + 'font:13px sans-serif;z-index:999999;pointer-events:none;';
    document.body.appendChild(el);
    setTimeout(function() { el.remove(); }, 2200);
  }

  function showModal(title) {
    var ex = document.getElementById('_offline_modal');
    if (ex) { ex.remove(); return; }
    var mo = document.createElement('div');
    mo.id = '_offline_modal';
    mo.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:99999;'
      + 'display:flex;align-items:center;justify-content:center;';
    mo.innerHTML = '<div style="background:#fff;border-radius:8px;padding:28px;min-width:300px;'
      + 'font-family:sans-serif;box-shadow:0 8px 32px rgba(0,0,0,.2)">'
      + '<h3 style="margin:0 0 8px">' + title + '</h3>'
      + '<p style="color:#888;margin:0 0 16px;font-size:14px">Action preview (offline clone)</p>'
      + '<button id="_offline_modal_close" style="padding:8px 18px;background:#408dfb;'
      + 'color:#fff;border:none;border-radius:4px;cursor:pointer">Close</button></div>';
    document.body.appendChild(mo);
    mo.addEventListener('click', function(e) {
      if (e.target === mo || e.target.id === '_offline_modal_close') mo.remove();
    });
  }

  document.addEventListener('click', function(e) {
    var t = e.target;
    var link = t.closest && t.closest('a[href]');
    if (link) {
      var href = link.getAttribute('href') || '';
      if (href.endsWith('.html')) return;
      if (href.indexOf('#/') === 0) {
        e.preventDefault();
        showToast('"' + href.replace('#/', '').split('?')[0] + '" not recorded yet');
        return;
      }
      if (href === '#' || href === '') { e.preventDefault(); return; }
    }

    var tab = t.closest && t.closest('[role=tab]');
    if (tab) { e.preventDefault(); activateTab(tab); return; }

    var dt = t.closest && t.closest('.dropdown-toggle');
    if (dt) {
      e.preventDefault();
      var wrap = dt.closest('.dropdown');
      var was = wrap && wrap.classList.contains('show');
      closeDropdowns();
      if (wrap && !was) openDropdown(wrap);
      return;
    }

    if (!t.closest || !t.closest('.dropdown')) closeDropdowns();

    if (!link) {
      var acc = t.closest && t.closest('.accordion-button, [aria-expanded][aria-controls]');
      if (acc && acc.getAttribute('role') !== 'tab') {
        var ctrl = acc.getAttribute('aria-controls');
        var panel = ctrl && document.getElementById(ctrl);
        if (panel && !panel.closest('[role=tabpanel]')) {
          e.preventDefault();
          toggleAccordion(acc);
          return;
        }
      }
    }

    var btn = t.closest && t.closest('button.btn-primary, .btn-primary, button[type=submit]');
    if (btn && !btn.disabled) {
      var txt = (btn.textContent || '').trim();
      if (/new|create|add|save|submit/i.test(txt)) {
        e.preventDefault();
        showModal(txt || 'Action');
      }
    }
  });

  document.querySelectorAll('[role=tablist]').forEach(function(tl) {
    var tabs = Array.from(tl.querySelectorAll('[role=tab]'));
    var active = tabs.find(function(t) {
      return t.getAttribute('aria-selected') === 'true' || t.classList.contains('active');
    }) || tabs[0];
    if (active) activateTab(active);
  });

  document.querySelectorAll('.dropdown-menu').forEach(function(m) {
    m.style.display = 'none';
    m.classList.remove('show');
  });

  document.querySelectorAll('[aria-expanded][aria-controls]').forEach(function(el) {
    if (el.getAttribute('role') === 'tab') return;
    var panel = document.getElementById(el.getAttribute('aria-controls') || '');
    if (!panel || panel.closest('[role=tabpanel]')) return;
    var open = el.getAttribute('aria-expanded') === 'true';
    panel.style.display = open ? '' : 'none';
    panel.hidden = !open;
  });

  document.querySelectorAll('a, button, [role=tab], .dropdown-toggle, [aria-expanded]')
    .forEach(function(el) { el.style.cursor = 'pointer'; });

  document.querySelectorAll('#main-nav-tab, .main-nav-lhs, .main-nav-lhs a')
    .forEach(function(el) { el.style.pointerEvents = 'auto'; });
})();
"""
