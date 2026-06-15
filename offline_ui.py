"""Universal offline interaction JS — one engine for every page."""

from __future__ import annotations

import json
from pathlib import Path

# Per-page button text → target
PAGE_BUTTON_TARGETS: dict[str, dict[str, str]] = {
    "contacts": {"new": "contacts-new.html", "create new customer": "contacts-new.html"},
    "salesorders": {"new": "salesorders-new.html", "create sales order": "salesorders-new.html"},
    "inventory-product-index": {"new": "inventory-product-product-creation.html", "create item": "inventory-product-product-creation.html"},
    "quotes": {"new": "quotes.html"},
    "invoices": {"new": "invoices.html"},
}

# Global button-text patterns (any page)
GLOBAL_BUTTON_TARGETS: dict[str, str] = {
    "create new customer": "contacts-new.html",
    "create customer": "contacts-new.html",
    "add customer": "contacts-new.html",
    "create sales order": "salesorders-new.html",
    "add sales order": "salesorders-new.html",
    "create item": "inventory-product-product-creation.html",
    "add item": "inventory-product-product-creation.html",
    "new item": "inventory-product-product-creation.html",
    "create invoice": "invoices.html",
    "new invoice": "invoices.html",
    "create quote": "quotes.html",
    "save": "contacts.html",
    "save and select": "contacts.html",
}

QUICK_CREATE_ITEMS: list[tuple[str, str]] = [
    ("inventory-product-product-creation.html", "New Item"),
    ("contacts-new.html", "New Customer"),
    ("salesorders-new.html", "New Sales Order"),
    ("invoices.html", "New Invoice"),
    ("quotes.html", "New Quote"),
]

# Hash fragment suffix → page (checked before prefix)
HASH_EXACT_ALIASES: dict[str, str] = {
    "#/contacts/new": "contacts-new.html",
    "#/salesorders/new": "salesorders-new.html",
    "#/inventory/product/product-creation": "inventory-product-product-creation.html",
    "#/inventory/product/new": "inventory-product-product-creation.html",
    "#/home/gettingstarted": "home-gettingstarted.html",
    "#/home/recentupdates": "home-recentupdates.html",
    "#/home/dashboard": "home-dashboard.html",
    "#/home": "home-dashboard.html",
}

# Hash prefix → best available list page
HASH_PREFIX_ROUTES: dict[str, str] = {
    "contacts": "contacts.html",
    "inventory/product": "inventory-product-index.html",
    "inventory": "inventory-product-index.html",
    "quotes": "quotes.html",
    "salesorders": "salesorders.html",
    "invoices": "invoices.html",
    "home": "home-dashboard.html",
}

HASH_NEW_ROUTES: dict[str, str] = {
    "contacts": "contacts-new.html",
    "salesorders": "salesorders-new.html",
    "inventory/product": "inventory-product-product-creation.html",
    "inventory": "inventory-product-product-creation.html",
}


def _hash_keys(route_map: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in route_map.items() if k.startswith("#/")}


def build_interaction_js(route_map: dict[str, str], sitemap: list | None = None) -> str:
    routes = {**_hash_keys(route_map), **HASH_EXACT_ALIASES}
    routes_json = json.dumps(routes, separators=(",", ":"))
    prefix_json = json.dumps(HASH_PREFIX_ROUTES, separators=(",", ":"))
    new_json = json.dumps(HASH_NEW_ROUTES, separators=(",", ":"))
    actions_json = json.dumps(PAGE_BUTTON_TARGETS, separators=(",", ":"))
    global_json = json.dumps(GLOBAL_BUTTON_TARGETS, separators=(",", ":"))
    quick_json = json.dumps(QUICK_CREATE_ITEMS, separators=(",", ":"))

    return f"""<script data-offline-ui="1">
(function() {{
  'use strict';

  var ROUTES = {routes_json};
  var PREFIX_ROUTES = {prefix_json};
  var NEW_ROUTES = {new_json};
  var PAGE_ACTIONS = {actions_json};
  var GLOBAL_ACTIONS = {global_json};
  var QUICK_CREATE = {quick_json};

  var FILTER_MENUS = {{
    "All Customers": ["All Customers","Active Customers","Inactive Customers","CRM Customers","Duplicate Customers","Customer Group"],
    "All Sales Orders": ["All Sales Orders","Open Sales Orders","Draft Sales Orders","Pending Sales Orders","Closed Sales Orders"],
    "All Items": ["All Items","Active Items","Inactive Items","Sales Items","Purchase Items","Inventory Items"],
    "All Invoices": ["All Invoices","Draft Invoices","Sent Invoices","Overdue Invoices","Paid Invoices"],
    "All Quotes": ["All Quotes","Draft Quotes","Sent Quotes","Accepted Quotes","Declined Quotes"]
  }};

  var MORE_ACTIONS = {{
    "contacts": ["Import Customers","Export Customers","Preferences","Refresh List"],
    "salesorders": ["Import Sales Orders","Export Sales Orders","Preferences","Refresh List"],
    "invoices": ["Import Invoices","Export Invoices","Preferences","Refresh List"],
    "quotes": ["Import Quotes","Export Quotes","Preferences","Refresh List"],
    "inventory-product-index": ["Import Items","Export Items","Preferences","Refresh List"],
    "default": ["Import","Export","Preferences","Refresh List"]
  }};

  var COMBOBOX_OPTIONS = {{
    "salutation": ["Mr.","Mrs.","Ms.","Miss.","Dr."],
    "currency": ["INR","USD","EUR","GBP","AUD"],
    "default": ["Option 1","Option 2","Option 3"]
  }};

  var ADD_NEW_MAP = {{
    "new customer": "contacts-new.html",
    "new item": "inventory-product-product-creation.html",
    "new sales order": "salesorders-new.html",
    "new invoice": "invoices.html",
    "new quote": "quotes.html"
  }};

  /* ── helpers ── */
  function slug() {{
    return (location.pathname.split('/').pop() || 'home.html').replace(/\\.html$/, '');
  }}

  function go(target) {{ if (target) location.href = target; }}

  function lookupRoute(href) {{
    if (!href) return null;
    var key = href.split('?')[0].replace(/\\/$/, '');
    if (ROUTES[href]) return ROUTES[href];
    if (ROUTES[key]) return ROUTES[key];
    if (!key.startsWith('#/')) return null;
    var path = key.slice(2);
    var parts = path.split('/');
    if (parts[parts.length - 1] === 'new') {{
      var base = parts.slice(0, -1).join('/');
      if (NEW_ROUTES[base]) return NEW_ROUTES[base];
      for (var ni = 0; ni < Object.keys(NEW_ROUTES).length; ni++) {{
        var nk = Object.keys(NEW_ROUTES).sort(function(a,b){{return b.length-a.length;}})[ni];
        if (path === nk + '/new' || path.indexOf(nk + '/') === 0) return NEW_ROUTES[nk];
      }}
    }}
    var prefixes = Object.keys(PREFIX_ROUTES).sort(function(a,b) {{ return b.length - a.length; }});
    for (var i = 0; i < prefixes.length; i++) {{
      var p = prefixes[i];
      if (path === p || path.indexOf(p + '/') === 0) return PREFIX_ROUTES[p];
    }}
    return null;
  }}

  function btnTarget(btn) {{
    var txt = (btn.textContent || '').trim().toLowerCase();
    var title = (btn.title || btn.getAttribute('aria-label') || '').trim().toLowerCase();
    var page = PAGE_ACTIONS[slug()] || {{}};
    if (page[txt]) return page[txt];
    if (title && page[title]) return page[title];
    for (var k in page) {{ if (txt.indexOf(k) !== -1) return page[k]; }}
    if (GLOBAL_ACTIONS[txt]) return GLOBAL_ACTIONS[txt];
    for (var g in GLOBAL_ACTIONS) {{ if (txt.indexOf(g) !== -1) return GLOBAL_ACTIONS[g]; }}
    if (title && ADD_NEW_MAP[title]) return ADD_NEW_MAP[title];
    return null;
  }}

  function toast(msg) {{
    var old = document.getElementById('_offline_toast');
    if (old) old.remove();
    var el = document.createElement('div');
    el.id = '_offline_toast';
    el.textContent = msg;
    el.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.82);color:#fff;padding:10px 20px;border-radius:20px;font:13px sans-serif;z-index:999999;pointer-events:none;';
    document.body.appendChild(el);
    setTimeout(function() {{ el.remove(); }}, 2400);
  }}

  /* ── tabs ── */
  function findPanel(tab) {{
    var c = tab.getAttribute('aria-controls');
    if (!c) return null;
    return document.getElementById(c) || document.getElementById(c.replace(/-tabpanel$/, '-panel'));
  }}

  function activateTab(tab) {{
    var tl = tab.closest('[role=tablist]') || tab.parentElement;
    if (!tl) return;
    tl.querySelectorAll('[role=tab]').forEach(function(t) {{
      t.classList.remove('active');
      t.setAttribute('aria-selected','false');
    }});
    tab.classList.add('active');
    tab.setAttribute('aria-selected','true');
    var panel = findPanel(tab);
    if (!panel) return;
    panel.parentElement.querySelectorAll('[role=tabpanel]').forEach(function(p) {{
      p.style.display = 'none'; p.hidden = true; p.classList.remove('show','active');
    }});
    panel.style.display = ''; panel.hidden = false; panel.classList.add('show','active');
  }}

  /* ── dropdowns ── */
  function findMenu(wrap, toggle) {{
    var m = wrap.querySelector(':scope > .dropdown-menu') || wrap.querySelector('.dropdown-menu');
    if (m) return m;
    if (wrap.nextElementSibling && wrap.nextElementSibling.classList.contains('dropdown-menu')) return wrap.nextElementSibling;
    var ctrl = toggle && toggle.getAttribute('aria-controls');
    if (ctrl) {{ var p = document.getElementById(ctrl); if (p) return p; }}
    return null;
  }}

  function buildMenu(wrap, toggle, items, opts) {{
    opts = opts || {{}};
    var menu = document.createElement('ul');
    menu.className = 'dropdown-menu' + (opts.end ? ' dropdown-menu-end' : '');
    menu.setAttribute('role','menu');
    items.forEach(function(label) {{
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.className = 'dropdown-item';
      a.href = opts.href || '#';
      a.textContent = label;
      a.setAttribute('role','menuitem');
      if (opts.pick) {{
        a.addEventListener('click', function(ev) {{
          ev.preventDefault();
          var t = wrap.querySelector('.filter-title') || toggle.querySelector('span') || toggle;
          if (t) t.textContent = label;
          closeDD();
        }});
      }} else if (opts.input) {{
        a.addEventListener('click', function(ev) {{ ev.preventDefault(); opts.input.value = label; closeDD(); }});
      }} else if (a.href === '#') {{
        a.addEventListener('click', function(ev) {{ ev.preventDefault(); closeDD(); }});
      }}
      li.appendChild(a); menu.appendChild(li);
    }});
    if (toggle && toggle.classList.contains('dropdown') && toggle.tagName === 'BUTTON') {{
      toggle.insertAdjacentElement('afterend', menu);
    }} else {{
      wrap.appendChild(menu);
    }}
    return menu;
  }}

  function quickMenu(wrap) {{
    var m = wrap.querySelector('.dropdown-menu');
    if (m) return m;
    return buildMenu(wrap, null, QUICK_CREATE.map(function(i){{return i[1];}}), {{
      href: null, end: true
    }});
  }}

  function ensureMenu(wrap, toggle) {{
    var ex = findMenu(wrap, toggle);
    if (ex) return ex;
    var txt = (toggle.textContent || '').trim().toLowerCase();
    var label = toggle.getAttribute('aria-label') || '';

    if (wrap.classList.contains('quik-add') || (toggle.classList.contains('dropdown-toggle') && txt.indexOf('new') !== -1)) {{
      var m = document.createElement('ul');
      m.className = 'dropdown-menu dropdown-menu-end';
      m.setAttribute('role','menu');
      QUICK_CREATE.forEach(function(item) {{
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.className = 'dropdown-item'; a.href = item[0]; a.textContent = item[1];
        li.appendChild(a); m.appendChild(li);
      }});
      wrap.appendChild(m); return m;
    }}
    if (toggle.classList.contains('criteriadashbadge')) {{
      if (txt.indexOf('accrual') !== -1) return buildMenu(wrap, toggle, ['Accrual','Cash'], {{pick:true}});
      return buildMenu(wrap, toggle, ['This Fiscal Year','Previous Fiscal Year','Last 6 Months','Last 12 Months'], {{pick:true}});
    }}
    if (wrap.classList.contains('list-title')) {{
      var t = toggle.querySelector('.filter-title') || toggle.querySelector('span');
      var l = t ? t.textContent.trim() : 'All';
      return buildMenu(wrap, toggle, FILTER_MENUS[l] || [l], {{pick:true}});
    }}
    if (label === 'More Actions') return buildMenu(wrap, toggle, (MORE_ACTIONS[slug()] || MORE_ACTIONS.default));
    if (wrap.classList.contains('orglist-topband')) {{
      var org = wrap.querySelector('.org-name-section');
      return buildMenu(wrap, toggle, [org ? org.textContent.trim() : 'Organization']);
    }}
    if (toggle.classList.contains('icon-button') && toggle.classList.contains('dropdown') && !toggle.classList.contains('user-notification')) {{
      return buildMenu(wrap, toggle, ['My Profile','Settings','Refer and Earn','Sign Out'], {{toggle:toggle}});
    }}
    if (wrap.classList.contains('ac-dropdown')) {{
      var inp = wrap.querySelector('input[role=combobox],input.ac-search-txt');
      if (inp) {{
        var k = ((inp.getAttribute('aria-label')||inp.placeholder||'')+'').toLowerCase();
        var opts = COMBOBOX_OPTIONS.default;
        if (k.indexOf('salutation') !== -1) opts = COMBOBOX_OPTIONS.salutation;
        else if (k.indexOf('currency') !== -1) opts = COMBOBOX_OPTIONS.currency;
        return buildMenu(wrap, toggle, opts, {{input:inp}});
      }}
    }}
    if (wrap.classList.contains('recent-activities')) return buildMenu(wrap, toggle, ['No recent activities']);
    return null;
  }}

  function openDD(wrap, toggle) {{
    ensureMenu(wrap, toggle);
    var menu = findMenu(wrap, toggle);
    if (!menu) return;
    wrap.classList.add('show'); menu.classList.add('show');
    menu.style.cssText = 'display:block!important;position:absolute;z-index:9990;left:0;top:100%;min-width:180px;';
    if (wrap.classList.contains('quik-add')) menu.style.right = '0'; menu.style.left = 'auto';
    if (toggle) toggle.setAttribute('aria-expanded','true');
  }}

  function closeDD(except) {{
    document.querySelectorAll('.dropdown.show,.orglist-topband.show').forEach(function(d) {{
      if (d === except) return;
      d.classList.remove('show');
      var m = d.querySelector('.dropdown-menu');
      if (m) {{ m.classList.remove('show'); m.style.display = 'none'; }}
      var t = d.querySelector('.dropdown-toggle,[role=button]');
      if (t) t.setAttribute('aria-expanded','false');
    }});
    document.querySelectorAll('button.dropdown.show').forEach(function(b) {{
      if (b === except) return;
      b.classList.remove('show');
      var sib = b.nextElementSibling;
      if (sib && sib.classList.contains('dropdown-menu')) {{ sib.classList.remove('show'); sib.style.display='none'; }}
    }});
  }}

  function ddCtx(el) {{
    var ac = el.closest('.ac-dropdown');
    if (ac && (el.closest('.zf-ac-toggler') || el.matches('input[role=combobox],input.ac-search-txt'))) {{
      return {{wrap:ac, toggle:ac.querySelector('input[role=combobox],input.ac-search-txt')||el}};
    }}
    var toggle = el.closest('.dropdown-toggle') || el.closest('button.dropdown') || el.closest('.orglist-topband [role=button]') || el.closest('.filter-dd-trigger');
    if (!toggle) return null;
    var wrap = toggle.closest('.dropdown') || toggle.closest('.orglist-topband') || (toggle.classList.contains('dropdown') ? toggle : null);
    return wrap ? {{wrap:wrap, toggle:toggle}} : null;
  }}

  /* ── accordion ── */
  function toggleAcc(btn) {{
    var id = btn.getAttribute('aria-controls');
    var panel = id && document.getElementById(id);
    var open = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', open ? 'false' : 'true');
    btn.classList.toggle('collapsed', open);
    if (panel) {{
      panel.hidden = open;
      panel.classList.toggle('show', !open);
      panel.style.display = open ? 'none' : '';
    }}
  }}

  /* ── home tabs ── */
  function homeTab(el) {{
    var t = (el.textContent || '').trim();
    if (t === 'Dashboard') return go('home-dashboard.html');
    if (t === 'Getting Started') return go('home-gettingstarted.html');
    if (t.indexOf('Recent Updates') !== -1) return go('home-recentupdates.html');
  }}

  /* ── main click handler ── */
  document.addEventListener('click', function(e) {{
    var t = e.target;

    /* let real links through */
    var a = t.closest('a[href]');
    if (a) {{
      var href = a.getAttribute('href') || '';
      if (href.endsWith('.html') || href.startsWith('http') || href.startsWith('mailto:')) return;
      if (href.indexOf('#/') === 0) {{
        var dest = lookupRoute(href);
        e.preventDefault();
        if (dest) go(dest);
        else toast('"' + href.replace('#/','').split('?')[0] + '" not recorded yet');
        return;
      }}
      if (href === '#' || href === '') {{ e.preventDefault(); return; }}
    }}

    /* home dashboard tabs */
    var ht = t.closest('#homescreen-tabs .nav-link,#homescreen-tabs button.nav-link');
    if (ht) {{ e.preventDefault(); if (ht.tagName==='A' && (ht.getAttribute('href')||'').endsWith('.html')) go(ht.getAttribute('href')); else homeTab(ht); return; }}

    /* dropdown item inside open menu */
    if (t.closest('.dropdown-menu .dropdown-item')) return;

    /* dropdown toggle */
    var ctx = ddCtx(t);
    if (ctx) {{
      e.preventDefault(); e.stopPropagation();
      var menu = findMenu(ctx.wrap, ctx.toggle);
      var open = !!(menu && menu.classList.contains('show'));
      closeDD(); if (!open) openDD(ctx.wrap, ctx.toggle); return;
    }}

    if (!t.closest('.dropdown-menu')) closeDD();

    /* aria tabs */
    var tab = t.closest('[role=tab]');
    if (tab) {{ e.preventDefault(); activateTab(tab); return; }}

    /* accordion */
    var acc = t.closest('.accordion-button,[aria-expanded][aria-controls]');
    if (acc && acc.getAttribute('role') !== 'tab' && !a) {{
      var p = document.getElementById(acc.getAttribute('aria-controls') || '');
      if (p && !p.closest('[role=tabpanel]')) {{ e.preventDefault(); toggleAcc(acc); return; }}
    }}

    /* sidebar + buttons */
    var btn = t.closest('button,.add-new[role=button],[role=button].add-new');
    if (btn && !btn.disabled) {{
      if (btn.classList.contains('dropdown-toggle') || btn.classList.contains('dropdown')) return;
      var dest = btnTarget(btn);
      if (dest) {{ e.preventDefault(); go(dest); return; }}
      var btxt = (btn.textContent || '').trim();
      if (/^(new|create|add)\\b/i.test(btxt) && btn.classList.contains('btn-primary')) {{
        e.preventDefault(); toast('"' + btxt + '" page not recorded yet');
      }}
    }}

    /* add-new icon links with hash */
    var addNew = t.closest('a.add-new');
    if (addNew) {{
      var ah = addNew.getAttribute('href') || '';
      if (ah.indexOf('#/') === 0) {{
        var ad = lookupRoute(ah);
        e.preventDefault();
        if (ad) go(ad); else toast('Not recorded yet');
        return;
      }}
    }}

    /* sidebar collapse */
    var col = t.closest('.collapse-expand');
    if (col) {{
      e.preventDefault();
      var lhs = document.querySelector('.main-nav-lhs');
      if (lhs) {{ lhs._c = !lhs._c; lhs.style.width = lhs._c ? '48px' : ''; lhs.style.overflow = lhs._c ? 'hidden' : ''; }}
    }}
  }}, false);

  document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') closeDD(); }});

  /* ── init ── */
  document.querySelectorAll('[role=tablist]').forEach(function(tl) {{
    var tabs = tl.querySelectorAll('[role=tab]');
    var active = Array.from(tabs).find(function(t) {{ return t.classList.contains('active') || t.getAttribute('aria-selected')==='true'; }}) || tabs[0];
    if (active) activateTab(active);
  }});

  document.querySelectorAll('.quik-add').forEach(function(w) {{ ensureMenu(w, w.querySelector('.dropdown-toggle')); }});
  document.querySelectorAll('.dropdown-menu').forEach(function(m) {{ m.style.display='none'; m.classList.remove('show'); }});

  document.querySelectorAll('.accordion-button[aria-controls]').forEach(function(btn) {{
    var panel = document.getElementById(btn.getAttribute('aria-controls') || '');
    if (!panel) return;
    var open = btn.getAttribute('aria-expanded') === 'true';
    panel.style.display = open ? '' : 'none';
    panel.hidden = !open;
  }});

  document.querySelectorAll('a,button,[role=tab],.dropdown-toggle,[aria-expanded],.add-new')
    .forEach(function(el) {{ el.style.cursor = 'pointer'; }});
  document.querySelectorAll('#main-nav-tab,.main-nav-lhs,.main-nav-lhs a,.nav-link[href$=".html"]')
    .forEach(function(el) {{ el.style.pointerEvents = 'auto'; }});

  var page = (location.pathname.split('/').pop() || '');
  document.querySelectorAll('a[href$=".html"]').forEach(function(link) {{
    if (link.getAttribute('href') === page) link.classList.add('active');
  }});
}})();
</script>"""


def load_sitemap(pages_dir: Path) -> list:
    path = pages_dir / "sitemap.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
