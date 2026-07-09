"""Stitcher V1 — turn crawl snapshots into a navigable static SaaS clone.

Three responsibilities, nothing else:

1. Page navigation  — rewrite `<a href="#/route">` to `../<slug>/page.html`
                      (every anchor, even ones hidden inside collapsed menus)
2. Sidebar accordions — wire collapsible in-page menus (accordion buttons /
                      aria-controls toggles) so they expand/collapse client-side.
                      These are NEVER treated as interactions and NEVER load a
                      snapshot — the submenu already lives in the same page.
3. Interaction UI   — tag each trigger with `data-stitch-ui-id` and inject the
                      reconciled `ui_html` (from reconciliation.json) into the
                      current page on click — no reload. The captured snapshot
                      page is used only as a fallback when injection isn't
                      possible (no ui_html, parentSelector missing, or it throws).

The accordion vs. interaction split is generic (no app-specific selectors): a
toggle whose `aria-controls` target (or sibling panel) exists *in the same page*
is an accordion; a trigger whose content is created on click (dropdown / modal /
popover / drawer overlay) is reconciled and injected in place.

Injection wraps the UI in `.stitch-injected-ui` and the runtime provides generic
close behavior (click-outside, ESC, and `.close`/`.sidebar-close`/`[data-dismiss]`
/backdrop affordances). Interaction config travels to the browser as
`window.__STITCH_INTERACTIONS__`.
"""

import gzip
import json
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from config import get_app_config
from asset_localizer import (
    copy_assets_to_stitched,
    finalize_asset_tree,
    localize_html_assets,
    rewire_asset_prefix,
)
from stitch_maps import (
    ensure_maplibre_vendor_assets,
    load_map_state,
    page_has_maplibre,
)
from storage.storage_manager import (
    clean_stitched,
    get_assets_dir,
    get_crawl_dir,
    get_metadata_dir,
    get_sitemap_path,
    get_stitched_dir,
)

RUNTIME_JS = """// Stitcher runtime — page navigation, sidebar accordions, and reconciliation
// UI injection. Interaction clicks inject the reconciled UI into the CURRENT
// page (no reload); the captured snapshot page is used only as a fallback.
(function () {
  "use strict";

  // ── HubSpot static-clone bootstrap ────────────────────────────────────────
  // Add classes that HubSpot JS normally sets on <body> so the full nav CSS
  // layout activates (sidebar width, sticky toolbar offset, etc.).
  (function bootstrapHubSpotLayout() {
    var body = document.body;
    if (!body) return;
    // sticky-global-toolbar: activates fixed nav + content-top-offset rules
    if (!body.classList.contains("sticky-global-toolbar")) {
      body.classList.add("sticky-global-toolbar");
    }
    // HubSpot sets id="crm" on <body> on CRM pages for CRM-specific layout
    if (window.location.hostname.indexOf("hubspot") !== -1 ||
        document.querySelector("#hs-nav-v4")) {
      if (!body.id) body.id = "crm";
    }
  })();
  // ── End HubSpot bootstrap ─────────────────────────────────────────────────

  // ── Stripe dashboard static-clone bootstrap ───────────────────────────────
  (function bootstrapStripeLayout() {
    var html = document.documentElement;
    if (!html) return;
    if (window.location.hostname.indexOf("dashboard.stripe.com") === -1 &&
        !document.querySelector("#dashboardRoot")) {
      return;
    }
    if (!html.classList.contains("db-NewChrome")) {
      html.classList.add("db-NewChrome");
    }
    var body = document.body;
    if (body && !body.id) body.id = "merch";

    // Empty sail portal shells sit on top of the page (inset:0, z-index:299)
    // and swallow every click in the static clone.
    Array.prototype.forEach.call(
      document.querySelectorAll("body > .__sail-layer-containers"),
      function (layer) {
        if (!layer.children.length) {
          layer.style.display = "none";
          layer.style.pointerEvents = "none";
          return;
        }
        layer.style.pointerEvents = "none";
      }
    );

    var chrome = document.getElementById("chrome-layout");
    if (chrome) chrome.style.pointerEvents = "auto";

    var root = document.getElementById("dashboardRoot");
    if (root) root.style.pointerEvents = "auto";

    Array.prototype.forEach.call(
      document.querySelectorAll("#chrome-layout-backdrop, [data-testid='backdrop']"),
      function (el) {
        el.style.display = "none";
        el.style.pointerEvents = "none";
      }
    );

    if (!document.getElementById("stitch-workload-nav-style")) {
      var wlStyle = document.createElement("style");
      wlStyle.id = "stitch-workload-nav-style";
      wlStyle.textContent = [
        "#primary-nav [data-testid='workloads-nav-links'] > li,",
        "[data-testid='primary-nav'] [data-testid='workloads-nav-links'] > li,",
        "#primary-nav section:has([data-testid='workloads-nav']) > ul > li,",
        "[data-testid='primary-nav'] section:has([data-testid='workloads-nav']) > ul > li {",
        "  display: list-item !important; flex: 0 0 auto !important; flex-shrink: 0 !important; width: 100% !important;",
        "}",
        "a[data-testid^='toggle-workload-'], .toggle-workload-button {",
        "  flex: 0 0 auto !important; flex-grow: 0 !important; width: 100% !important;",
        "  height: 30px !important; min-height: 30px !important; max-height: 30px !important;",
        "  cursor: pointer !important; pointer-events: auto !important;",
        "}",
        "a[data-testid^='toggle-workload-'] .as-6x,",
        "a[data-testid^='toggle-workload-'] .as-20,",
        ".toggle-workload-button .as-g.as-6x {",
        "  width: auto !important; max-width: none !important; overflow: visible !important;",
        "  opacity: 1 !important; visibility: visible !important;",
        "}",
        "a[data-testid^='toggle-workload-'][aria-expanded='true'] {",
        "  background: rgba(26, 44, 68, 0.06) !important; border-radius: 6px;",
        "}",
        "a[data-testid^='toggle-workload-'][aria-expanded='true'] [data-arrow='true'] svg {",
        "  transform: rotate(180deg);",
        "}",
        "#primary-nav .stitch-workload-nav-panel.show,",
        "[data-testid='primary-nav'] .stitch-workload-nav-panel.show {",
        "  display: block !important; visibility: visible !important; overflow: visible !important;",
        "}",
        "#primary-nav .stitch-workload-nav-panel > li,",
        "[data-testid='primary-nav'] .stitch-workload-nav-panel > li {",
        "  display: block !important; width: 100% !important;",
        "}",
        "#primary-nav .stitch-workload-nav-panel a,",
        "[data-testid='primary-nav'] .stitch-workload-nav-panel a {",
        "  width: 100% !important; max-width: 100% !important; min-width: 0 !important;",
        "  flex: 1 1 auto !important; --s--flex-x: 1 1 auto !important; --s--flex-y: 0 0 auto !important;",
        "  --s--object-width: auto !important; height: auto !important; min-height: 28px !important;",
        "  color: rgb(26, 44, 68) !important;",
        "}",
        "#primary-nav .stitch-workload-nav-panel a span,",
        "[data-testid='primary-nav'] .stitch-workload-nav-panel a span {",
        "  width: auto !important; max-width: none !important; overflow: visible !important;",
        "  opacity: 1 !important; visibility: visible !important; color: inherit !important;",
        "}",
        "#primary-nav .stitch-workload-nav-panel:not(.show),",
        "[data-testid='primary-nav'] .stitch-workload-nav-panel[hidden] {",
        "  display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important;",
        "}",
      ].join("\\n");
      document.head.appendChild(wlStyle);
    }
  })();
  // ── End Stripe bootstrap ──────────────────────────────────────────────────

  // ── Likwid / Metronic static-clone bootstrap ───────────────────────────────
  (function bootstrapLikwidLayout() {
    if (!document.querySelector("#kt_app_sidebar")) return;

    // Ensure a real viewport meta tag so mobile browsers use the actual
    // device width instead of the ~980px desktop fallback — without this,
    // none of Metronic's responsive @media rules ever activate.
    if (!document.querySelector('meta[name="viewport"]')) {
      var viewportMeta = document.createElement("meta");
      viewportMeta.setAttribute("name", "viewport");
      viewportMeta.setAttribute("content", "width=device-width, initial-scale=1, shrink-to-fit=no");
      document.head.insertBefore(viewportMeta, document.head.firstChild);
    }

    if (!document.getElementById("stitch-likwid-nav-style")) {
      var lkStyle = document.createElement("style");
      lkStyle.id = "stitch-likwid-nav-style";
      lkStyle.textContent = [
        "#kt_app_sidebar .menu-link,",
        "#kt_app_sidebar [data-kt-menu-trigger],",
        "#kt_app_sidebar [data-stitch-accordion],",
        "#kt_app_sidebar a[data-stitch-go] {",
        "  pointer-events: auto !important; cursor: pointer !important;",
        "}",
        "#kt_app_sidebar .menu-item.menu-accordion:not(.show) > .menu-sub {",
        "  display: none !important;",
        "}",
        "#kt_app_sidebar .menu-item.menu-accordion.show > .menu-sub,",
        "#kt_app_sidebar .menu-item.menu-accordion > .menu-sub.show {",
        "  display: flex !important; flex-direction: column;",
        "}",
        ".modal:not(.show) { display: none !important; }",
        ".modal.show { display: block !important; }",
        // Frozen amCharts snapshots (pie/radar charts baked as <img> at crawl
        // time) carry hardcoded desktop pixel widths (e.g. 1199px) on an
        // absolutely-positioned wrapper div. Left alone, that wrapper forces
        // horizontal overflow on any narrower viewport, regardless of
        // breakpoint, so this is unscoped from the media query below.
        "[aria-hidden='true']:has(img[data-stitch-frozen-chart]) {",
        "  max-width: 100% !important; width: auto !important;",
        "}",
        "img[data-stitch-frozen-chart] {",
        "  max-width: 100% !important; width: auto !important; height: auto !important;",
        "}",
        ".stitch-table-scroll {",
        "  overflow-x: auto; max-width: 100%; -webkit-overflow-scrolling: touch;",
        "}",
        "@media (max-width: 991.98px) {",
        // Belt-and-suspenders: once the real viewport meta is honored, any
        // other baked desktop-width element (fixed-pixel panels, absolute
        // chart wrappers we didn't catch above, etc.) would otherwise force
        // real horizontal scrolling/shifting instead of just being clipped.
        "  html, body { overflow-x: hidden !important; max-width: 100vw; }",
        "  #lkh-chat-overlay { max-width: 100vw; }",
        // The drawer must stay BELOW the header (not top:0) — otherwise it
        // physically covers the hamburger button that opened it, and the
        // only way to close is tapping the dimmed overlay.
        "  #kt_app_header, #kt_app_sidebar_mobile_toggle { position: relative; z-index: 1201; }",
        "  #kt_app_sidebar {",
        "    display: flex !important; position: fixed !important; top: 60px; left: 0; bottom: 0;",
        "    width: 225px; max-width: 85vw; z-index: 1200;",
        "    transform: translateX(-100%); transition: transform .3s ease;",
        "    box-shadow: 8px 0 24px rgba(0, 0, 0, .25);",
        "  }",
        "  #kt_app_sidebar.stitch-sidebar-open { transform: translateX(0); }",
        "  #stitch-sidebar-overlay {",
        "    position: fixed; inset: 0; background: rgba(0, 0, 0, .35); z-index: 1150;",
        "    opacity: 0; visibility: hidden; transition: opacity .2s ease;",
        "  }",
        "  #stitch-sidebar-overlay.show { opacity: 1; visibility: visible; }",
        "  body.stitch-sidebar-drawer-open { overflow: hidden; }",
        "}",
      ].join("\\n");
      document.head.appendChild(lkStyle);
    }
    Array.prototype.forEach.call(
      document.querySelectorAll(".modal.fade"),
      function (modal) {
        if (!modal.classList.contains("show")) {
          modal.style.display = "none";
          modal.setAttribute("aria-hidden", "true");
        }
      }
    );

    // Wide data tables were captured at desktop width with no Bootstrap
    // `.table-responsive` wrapper. Rather than letting them force page-wide
    // horizontal scroll (or silently clipping columns via overflow-x:hidden
    // on body), wrap each one in its own horizontally-scrollable container
    // so the rest of the page stays put and no data becomes unreachable.
    Array.prototype.forEach.call(document.querySelectorAll("table"), function (table) {
      if (table.closest(".table-responsive, .stitch-table-scroll")) return;
      var wrapper = document.createElement("div");
      wrapper.className = "table-responsive stitch-table-scroll";
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });

    // Mobile hamburger → open/close the sidebar as a slide-in drawer with an
    // overlay backdrop. Metronic normally ships this via KTDrawer.js, which
    // isn't bundled in the static clone, so we reimplement the minimum here.
    var sidebarEl = document.getElementById("kt_app_sidebar");
    var mobileToggle = document.getElementById("kt_app_sidebar_mobile_toggle");
    if (sidebarEl && mobileToggle && !mobileToggle.__stitchDrawerBound) {
      mobileToggle.__stitchDrawerBound = true;
      var overlayEl = null;

      var isMobileWidth = function () {
        return window.matchMedia("(max-width: 991.98px)").matches;
      };

      var getOverlay = function () {
        if (overlayEl) return overlayEl;
        overlayEl = document.createElement("div");
        overlayEl.id = "stitch-sidebar-overlay";
        document.body.appendChild(overlayEl);
        overlayEl.addEventListener("click", closeSidebarDrawer);
        return overlayEl;
      };

      var openSidebarDrawer = function () {
        sidebarEl.classList.add("stitch-sidebar-open");
        document.body.classList.add("stitch-sidebar-drawer-open");
        getOverlay().classList.add("show");
        mobileToggle.setAttribute("aria-expanded", "true");
      };

      var closeSidebarDrawer = function () {
        sidebarEl.classList.remove("stitch-sidebar-open");
        document.body.classList.remove("stitch-sidebar-drawer-open");
        if (overlayEl) overlayEl.classList.remove("show");
        mobileToggle.setAttribute("aria-expanded", "false");
      };

      mobileToggle.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (sidebarEl.classList.contains("stitch-sidebar-open")) {
          closeSidebarDrawer();
        } else {
          openSidebarDrawer();
        }
      });

      // Tapping a real nav link inside the open drawer should close it
      // (but not accordion parents, which only expand/collapse a submenu).
      sidebarEl.addEventListener("click", function (e) {
        if (!isMobileWidth() || !sidebarEl.classList.contains("stitch-sidebar-open")) return;
        var link = e.target.closest
          ? e.target.closest("a[data-stitch-page], a[data-stitch-go], a[href]:not([href='#'])")
          : null;
        if (link && !link.closest(".menu-accordion")) closeSidebarDrawer();
      });

      document.addEventListener("keydown", function (e) {
        if ((e.key === "Escape" || e.keyCode === 27) && sidebarEl.classList.contains("stitch-sidebar-open")) {
          closeSidebarDrawer();
        }
      });

      window.addEventListener("resize", function () {
        if (!isMobileWidth()) closeSidebarDrawer();
      });
    }
  })();
  // ── End Likwid bootstrap ───────────────────────────────────────────────────

  // ── Rastaa dashboard: weather filter panel ─────────────────────────────────
  var raastaWeather = (function () {
    if (document.body.getAttribute("data-raasta-page") !== "dashboard") return null;

    function norm(el) {
      return (el.textContent || "").replace(/\\s+/g, " ").trim();
    }

    function findWeatherBtn() {
      var tagged = document.querySelector("[data-raasta-weather-toggle]");
      if (tagged) return tagged;
      var buttons = document.querySelectorAll("button");
      for (var i = 0; i < buttons.length; i++) {
        if (norm(buttons[i]) === "Weather") return buttons[i];
      }
      return null;
    }

    function findFilterRow() {
      var rows = document.querySelectorAll(".raasta-weather-filters, div.mt-3.flex.flex-nowrap");
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var btns = row.querySelectorAll("button");
        if (!btns.length) continue;
        for (var j = 0; j < btns.length; j++) {
          if (norm(btns[j]) === "All") return row;
        }
      }
      return null;
    }

    var weatherBtn = findWeatherBtn();
    var filterRow = findFilterRow();
    if (!weatherBtn || !filterRow) return null;

    weatherBtn.removeAttribute("data-stitch-ui-id");
    weatherBtn.setAttribute("data-raasta-weather-toggle", "");
    weatherBtn.setAttribute("type", "button");
    filterRow.classList.add("raasta-weather-filters");

    if (!document.getElementById("raasta-weather-style")) {
      var st = document.createElement("style");
      st.id = "raasta-weather-style";
      st.textContent = [
        ".raasta-weather-filters.raasta-weather-hidden { display: none !important; }",
        ".raasta-weather-filters button.raasta-wf-on {",
        "  border-color: rgb(96 165 250) !important;",
        "  background-color: rgb(59 130 246) !important;",
        "  color: #fff !important;",
        "  box-shadow: 0 0 14px rgba(59,130,246,0.4);",
        "}",
        "[data-raasta-weather-toggle], .raasta-weather-filters button {",
        "  pointer-events: auto !important; cursor: pointer !important;",
        "}",
      ].join("\\n");
      document.head.appendChild(st);
    }

    var chips = filterRow.querySelectorAll("button");
    var saved = [];
    for (var i = 0; i < chips.length; i++) {
      saved.push({ btn: chips[i], cls: chips[i].className, label: norm(chips[i]) });
      chips[i].setAttribute("type", "button");
    }

    var filtersVisible = true;
    var selected = "All";

    function selectFilter(label) {
      selected = label;
      for (var i = 0; i < saved.length; i++) {
        var item = saved[i];
        item.btn.className = item.cls;
        var on = item.label === label;
        if (on) item.btn.classList.add("raasta-wf-on");
        item.btn.setAttribute("aria-pressed", on ? "true" : "false");
      }
    }

    function setVisible(v) {
      filtersVisible = v;
      filterRow.classList.toggle("raasta-weather-hidden", !v);
      weatherBtn.setAttribute("aria-expanded", v ? "true" : "false");
    }

    selectFilter("All");
    setVisible(true);

    return {
      isWeatherClick: function (target) {
        return !!(target.closest && target.closest("[data-raasta-weather-toggle]"));
      },
      isFilterClick: function (target) {
        return target.closest ? target.closest(".raasta-weather-filters button") : null;
      },
      toggle: function () {
        setVisible(!filtersVisible);
      },
      select: function (btn) {
        selectFilter(norm(btn));
      },
    };
  })();
  // ── End Rastaa weather ─────────────────────────────────────────────────────

  // ── Rastaa riders: Add Driver modal + localStorage list ───────────────────
  var raastaRiders = (function () {
    if (document.body.getAttribute("data-raasta-page") !== "riders") return null;

    var STORAGE_KEY = "raasta_riders_v1";

    function norm(el) {
      return (el.textContent || "").replace(/\\s+/g, " ").trim();
    }

    function esc(s) {
      return String(s || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function loadRiders() {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (err) {
        return [];
      }
    }

    function saveRiders(list) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }

    function findListRoot() {
      var headings = document.querySelectorAll("h1");
      for (var i = 0; i < headings.length; i++) {
        if (norm(headings[i]) !== "Drivers") continue;
        var walk = headings[i].parentElement;
        for (var d = 0; d < 8 && walk; d++) {
          var list = walk.querySelector(".flex-1.overflow-auto");
          if (list) return list;
          walk = walk.parentElement;
        }
      }
      return null;
    }

    function updateCount(n) {
      var ps = document.querySelectorAll("p");
      for (var i = 0; i < ps.length; i++) {
        var t = norm(ps[i]);
        if (/drivers registered$/i.test(t)) {
          ps[i].textContent = n + " driver" + (n === 1 ? "" : "s") + " registered";
          return;
        }
      }
    }

    function riderName(r) {
      return [r.firstName, r.lastName].filter(Boolean).join(" ").trim() || "Unnamed Rider";
    }

    function initials(r) {
      var first = String(r.firstName || "").trim();
      var last = String(r.lastName || "").trim();
      if (first && last) return (first.charAt(0) + last.charAt(0)).toLowerCase();
      if (first.length >= 2) return first.slice(0, 2).toLowerCase();
      if (first) return first.charAt(0).toLowerCase();
      return "??";
    }

    function statusLabel(status) {
      if (status === "Offline") return "Inactive";
      return status || "Online";
    }

    function statusPillHtml(status) {
      var label = statusLabel(status);
      if (status === "Online") {
        return (
          '<span class="inline-block rounded-full px-2.5 py-1 text-[11px] font-medium bg-green-500/15 text-green-400">' +
          esc(label) +
          "</span>"
        );
      }
      return (
        '<span class="inline-block rounded-full px-2.5 py-1 text-[11px] font-medium bg-white/[0.06] text-white/40">' +
        esc(label) +
        "</span>"
      );
    }

    var GRID_ROW =
      "grid grid-cols-[2fr_1.5fr_1.5fr_1fr_1fr_100px] items-center";
    var EDIT_ICON =
      '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-pencil" aria-hidden="true"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"></path><path d="m15 5 4 4"></path></svg>';
    var DELETE_ICON =
      '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash2 lucide-trash-2" aria-hidden="true"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" x2="10" y1="11" y2="17"></line><line x1="14" x2="14" y1="11" y2="17"></line></svg>';

    function renderRiders() {
      var root = findListRoot();
      if (!root) return;
      var riders = loadRiders();
      updateCount(riders.length);
      if (!riders.length) {
        root.innerHTML =
          '<div class="text-sm text-white/25 py-8 text-center">No drivers yet.</div>';
        return;
      }
      var html = '<div class="rounded-2xl border border-white/[0.06] overflow-hidden">';
      html +=
        '<div class="' +
        GRID_ROW +
        ' border-b border-white/[0.06] bg-white/[0.02] px-5 py-3">';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider">Name</span>';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider">Phone</span>';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider">Email</span>';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider">Hub</span>';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider">Status</span>';
      html +=
        '<span class="text-[11px] font-medium text-white/40 uppercase tracking-wider text-right">Actions</span>';
      html += "</div>";
      for (var i = 0; i < riders.length; i++) {
        var r = riders[i];
        var name = riderName(r);
        var hub = r.hub ? esc(r.hub) : "—";
        var rowCls =
          GRID_ROW +
          " border-b border-white/[0.04] px-5 py-3.5 text-[13px] text-white/80 hover:bg-white/[0.02] transition";
        if (i === riders.length - 1) rowCls += " last:border-b-0";
        html +=
          '<div class="' +
          rowCls +
          '" data-raasta-rider-row="' +
          esc(r.id) +
          '">';
        html +=
          '<div class="flex items-center gap-3 min-w-0"><div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent text-[11px] font-semibold">' +
          esc(initials(r)) +
          '</div><span class="truncate font-medium text-white">' +
          esc(name) +
          "</span></div>";
        html +=
          '<span class="text-white/55 truncate">' + esc(r.phone || "—") + "</span>";
        html +=
          '<span class="text-white/55 truncate">' + esc(r.email || "—") + "</span>";
        html += '<span class="text-white/55 truncate">' + hub + "</span>";
        html += "<div>" + statusPillHtml(r.status) + "</div>";
        html += '<div class="flex items-center justify-end gap-1.5">';
        html +=
          '<button class="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.07] bg-white/[0.04] text-white/50 hover:bg-white/[0.08] hover:text-white transition" title="Edit" type="button" data-raasta-edit-rider="' +
          esc(r.id) +
          '">' +
          EDIT_ICON +
          "</button>";
        html +=
          '<button class="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.07] bg-transparent text-white/30 hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-400 transition" title="Delete" type="button" data-raasta-delete-rider="' +
          esc(r.id) +
          '">' +
          DELETE_ICON +
          "</button>";
        html += "</div></div>";
      }
      html += "</div>";
      root.innerHTML = html;
    }

    var editingId = null;

    function findModal() {
      return document.querySelector(".raasta-rider-modal");
    }

    function markModal(modal) {
      if (!modal) return null;
      modal.classList.add("raasta-rider-modal");
      return modal;
    }

    function openModal(riderId) {
      var existing = findModal();
      if (existing) existing.remove();
      editingId = riderId || null;
      var tpl = window.__RAASTA_RIDER_MODAL_HTML__;
      if (!tpl) return;
      var wrap = document.createElement("div");
      wrap.innerHTML = tpl;
      var modal = wrap.firstElementChild;
      if (!modal) return;
      markModal(modal);
      document.body.appendChild(modal);
      if (riderId) {
        var riders = loadRiders();
        var rider = null;
        for (var i = 0; i < riders.length; i++) {
          if (riders[i].id === riderId) {
            rider = riders[i];
            break;
          }
        }
        if (rider) populateForm(modal, rider);
      } else {
        resetModalChrome(modal);
      }
    }

    function ridersHomeHref() {
      if (location.pathname.indexOf("003-add-driver") !== -1) return "../../page.html";
      return null;
    }

    function closeModal() {
      var modal = findModal();
      if (modal) modal.remove();
      editingId = null;
      var home = ridersHomeHref();
      if (home) window.location.href = home;
    }

    function setField(form, prefix, value) {
      var el = fieldByLabel(form, prefix);
      if (el) el.value = value == null ? "" : value;
    }

    function resetModalChrome(modal) {
      var title = modal.querySelector("h3");
      if (title) title.textContent = "Add New Rider";
      var form = modal.querySelector("form");
      if (!form) return;
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.textContent = "Add Rider";
    }

    function populateForm(modal, rider) {
      var form = modal.querySelector("form");
      if (!form) return;
      setField(form, "First Name", rider.firstName);
      setField(form, "Last Name", rider.lastName);
      setField(form, "Phone Number", rider.phone);
      setField(form, "Email", rider.email);
      setField(form, "Vehicle Type", rider.vehicleType || "");
      setField(form, "Initial Status", rider.status || "Online");
      var title = modal.querySelector("h3");
      if (title) title.textContent = "Edit Rider";
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.textContent = "Save Rider";
    }

    function deleteRider(riderId) {
      if (!riderId) return;
      var riders = loadRiders().filter(function (r) {
        return r.id !== riderId;
      });
      saveRiders(riders);
      renderRiders();
    }

    function fieldByLabel(form, prefix) {
      var labels = form.querySelectorAll("label");
      for (var i = 0; i < labels.length; i++) {
        if (norm(labels[i]).indexOf(prefix) === 0) {
          var box = labels[i].parentElement;
          return box ? box.querySelector("input, select, textarea") : null;
        }
      }
      return null;
    }

    function readForm(modal) {
      var form = modal.querySelector("form");
      if (!form) return null;
      var vehicle = fieldByLabel(form, "Vehicle Type");
      var status = fieldByLabel(form, "Initial Status");
      var first = fieldByLabel(form, "First Name");
      var last = fieldByLabel(form, "Last Name");
      var phone = fieldByLabel(form, "Phone Number");
      var email = fieldByLabel(form, "Email");
      return {
        firstName: first ? first.value : "",
        lastName: last ? last.value : "",
        phone: phone ? phone.value : "",
        email: email ? email.value : "",
        vehicleType: vehicle ? vehicle.value : "",
        status: status ? status.value : "Online",
      };
    }

    function submitRider(modal) {
      var data = readForm(modal);
      if (!data || !String(data.firstName).trim() || !String(data.phone).trim()) {
        return false;
      }
      var riders = loadRiders();
      var payload = {
        firstName: String(data.firstName).trim(),
        lastName: String(data.lastName).trim(),
        phone: String(data.phone).trim(),
        email: String(data.email).trim(),
        vehicleType: data.vehicleType || "",
        status: data.status || "Online",
        hub: "",
      };
      if (editingId) {
        var updated = false;
        for (var i = 0; i < riders.length; i++) {
          if (riders[i].id === editingId) {
            riders[i] = Object.assign({}, riders[i], payload, { id: editingId });
            updated = true;
            break;
          }
        }
        if (!updated) riders.push(Object.assign({ id: editingId, createdAt: new Date().toISOString() }, payload));
      } else {
        riders.push(
          Object.assign(
            { id: String(Date.now()), createdAt: new Date().toISOString() },
            payload
          )
        );
      }
      saveRiders(riders);
      editingId = null;
      var home = ridersHomeHref();
      if (modal) modal.remove();
      if (home) {
        window.location.href = home;
        return true;
      }
      renderRiders();
      return true;
    }

    var overlays = document.querySelectorAll("div.fixed.inset-0");
    for (var o = 0; o < overlays.length; o++) {
      if (norm(overlays[o]).indexOf("Add New Rider") !== -1) {
        markModal(overlays[o]);
        break;
      }
    }

    renderRiders();

    return {
      handleClick: function (target, e) {
        var editBtn = target.closest("[data-raasta-edit-rider]");
        if (editBtn) {
          e.preventDefault();
          e.stopPropagation();
          openModal(editBtn.getAttribute("data-raasta-edit-rider"));
          return true;
        }

        var delBtn = target.closest("[data-raasta-delete-rider]");
        if (delBtn) {
          e.preventDefault();
          e.stopPropagation();
          deleteRider(delBtn.getAttribute("data-raasta-delete-rider"));
          return true;
        }

        if (target.closest("[data-raasta-add-rider]")) {
          e.preventDefault();
          e.stopPropagation();
          openModal(null);
          return true;
        }

        var modal = findModal();
        if (!modal || !modal.contains(target)) return false;

        var cancelBtn = target.closest("button");
        if (cancelBtn && norm(cancelBtn) === "Cancel") {
          e.preventDefault();
          e.stopPropagation();
          closeModal();
          return true;
        }

        if (cancelBtn && cancelBtn.querySelector(".lucide-x")) {
          e.preventDefault();
          e.stopPropagation();
          closeModal();
          return true;
        }

        var backdrop = modal.firstElementChild;
        if (backdrop && target === backdrop) {
          e.preventDefault();
          e.stopPropagation();
          closeModal();
          return true;
        }

        if (
          cancelBtn &&
          (norm(cancelBtn) === "Add Rider" || norm(cancelBtn) === "Save Rider")
        ) {
          e.preventDefault();
          e.stopPropagation();
          submitRider(modal);
          return true;
        }

        if (target.closest("form") && modal.contains(target.closest("form"))) {
          var submit = target.closest("button[type='submit']");
          if (submit) {
            e.preventDefault();
            e.stopPropagation();
            submitRider(modal);
            return true;
          }
        }

        return false;
      },
    };
  })();
  // ── End Rastaa riders ──────────────────────────────────────────────────────
  // ── Salesforge static-clone bootstrap ─────────────────────────────────────
  (function bootstrapSalesforgeLayout() {
    if (window.location.hostname.indexOf("salesforge.ai") === -1 &&
        !document.querySelector('[data-testid="salesforge-app"]') &&
        !document.title.toLowerCase().includes("salesforge")) {
      return;
    }

    // Ensure left sidebar nav links are clickable in the static clone.
    if (!document.getElementById("stitch-salesforge-nav-style")) {
      var sfStyle = document.createElement("style");
      sfStyle.id = "stitch-salesforge-nav-style";
      sfStyle.textContent = [
        "nav a, aside a, [role='navigation'] a {",
        "  pointer-events: auto !important; cursor: pointer !important;",
        "}",
        "button, [role='tab'], [role='button'] {",
        "  pointer-events: auto !important; cursor: pointer !important;",
        "}",
        // Hide bottom-right chat/support widget — prevents click-blocking overlay.
        "#gleap-frame-container, #gleap-button-container,",
        "[id*='gleap'], [class*='gleap'],",
        "[id*='intercom'], [class*='intercom-'],",
        "#launcher, .intercom-lightweight-app,",
        "#crisp-chatbox, .crisp-client,",
        "[class*='chat-widget'], [class*='chatWidget'],",
        "[class*='support-widget'] {",
        "  display: none !important; pointer-events: none !important;",
        "}",
        // Hide React portal/backdrop shells that block clicks.
        "[data-radix-portal] > :empty, [data-overlay-container] > :empty {",
        "  display: none !important;",
        "}",
      ].join("\\n");
      document.head.appendChild(sfStyle);
    }

    // Remove any full-screen invisible overlay elements left by React portals.
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-radix-portal], [data-overlay-container]"),
      function (portal) {
        if (!portal.children.length) {
          portal.style.display = "none";
          portal.style.pointerEvents = "none";
        }
      }
    );
  })();
  // ── End Salesforge bootstrap ───────────────────────────────────────────────

  function configFor(id) {
    var all = window.__STITCH_INTERACTIONS__ || {};
    return all[id] || null;
  }

  function isExternalHref(href) {
    return /^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0;
  }

  function eventTargetDeep(e) {
    var list = (document.elementsFromPoint &&
      document.elementsFromPoint(e.clientX, e.clientY)) || [e.target];
    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      if (!el || el.nodeType !== 1 || !el.closest) continue;
      if (
        el.closest(
          "a[data-stitch-page], a[data-stitch-go], [data-stitch-go], " +
          "[data-stitch-accordion], [data-stitch-ui-id], [data-stitch-tab-id], " +
          "a[href], button, [role='button']"
        )
      ) {
        return el;
      }
    }
    return e.target;
  }

  function showDemoHint(msg) {
    var text = msg || "This section is outside the recorded demo path";
    var existing = document.getElementById("__stitch_demo_hint__");
    if (existing) {
      existing.textContent = text;
      existing.style.opacity = "1";
      clearTimeout(existing._hideTimer);
      existing._hideTimer = setTimeout(function() {
        existing.style.opacity = "0";
      }, 2800);
      return;
    }
    var el = document.createElement("div");
    el.id = "__stitch_demo_hint__";
    el.textContent = text;
    el.style.cssText = [
      "position:fixed",
      "bottom:24px",
      "left:50%",
      "transform:translateX(-50%)",
      "background:rgba(30,30,30,0.88)",
      "color:#fff",
      "font-size:13px",
      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
      "padding:8px 18px",
      "border-radius:8px",
      "box-shadow:0 4px 18px rgba(0,0,0,0.28)",
      "z-index:2147483647",
      "pointer-events:none",
      "transition:opacity 0.35s ease",
      "white-space:nowrap",
    ].join(";");
    document.body.appendChild(el);
    el._hideTimer = setTimeout(function() {
      el.style.opacity = "0";
    }, 2800);
  }

  function findPanel(toggle) {
    if (toggle.classList && toggle.classList.contains("menu-accordion")) {
      var sub = toggle.querySelector(".menu-sub");
      if (sub) return sub;
    }
    var id = toggle.getAttribute("data-stitch-accordion");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) {
      var ac = toggle.getAttribute("aria-controls");
      if (ac) panel = document.getElementById(ac);
    }
    if (!panel) panel = toggle.nextElementSibling;
    return panel;
  }

  function showBootstrapModal(modal) {
    if (!modal) return;
    modal.classList.add("show");
    modal.style.display = "block";
    modal.removeAttribute("aria-hidden");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("role", "dialog");
    document.body.classList.add("modal-open");
    var backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop fade show";
    backdrop.setAttribute("data-stitch-modal-backdrop", modal.id || "");
    document.body.appendChild(backdrop);
  }

  function hideBootstrapModal(modal) {
    if (!modal) return;
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    modal.removeAttribute("aria-modal");
    var id = modal.id || "";
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-stitch-modal-backdrop="' + id + '"]'),
      function (el) { if (el.parentNode) el.parentNode.removeChild(el); }
    );
    if (!document.querySelector(".modal.show")) {
      document.body.classList.remove("modal-open");
    }
  }

  function activateBootstrapTab(tabLink) {
    var href = tabLink.getAttribute("href") || "";
    if (!href || href.charAt(0) !== "#") return;
    var pane = document.querySelector(href);
    if (!pane) return;
    var nav = tabLink.closest('[role="tablist"]');
    if (nav) {
      Array.prototype.forEach.call(nav.querySelectorAll("[data-bs-toggle='tab']"), function (t) {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
        t.setAttribute("tabindex", "-1");
      });
    }
    tabLink.classList.add("active");
    tabLink.setAttribute("aria-selected", "true");
    tabLink.removeAttribute("tabindex");
    var container = pane.parentElement;
    if (container) {
      Array.prototype.forEach.call(container.querySelectorAll(".tab-pane"), function (p) {
        p.classList.remove("show", "active");
      });
    }
    pane.classList.add("show", "active");
  }

  function switchLikwidPipeline(pipeBtn) {
    var boards = { leads: "pipe-leads", funnel: "pipe-funnel", deals: "pipe-deals" };
    var text = (pipeBtn.textContent || "").toLowerCase();
    var key = text.indexOf("funnel") >= 0 ? "funnel" : text.indexOf("deal") >= 0 ? "deals" : "leads";
    Object.keys(boards).forEach(function (k) {
      var el = document.getElementById(boards[k]);
      if (el) el.style.display = k === key ? "" : "none";
    });
    document.querySelectorAll(".up-pipe-btn").forEach(function (b) {
      b.classList.remove("up-pipe-active");
    });
    pipeBtn.classList.add("up-pipe-active");
  }

  function activateLeadStage(btn) {
    document.querySelectorAll("button.ld-stage").forEach(function (b) {
      b.classList.remove("ld-stage-active");
    });
    btn.classList.add("ld-stage-active");
  }

  function toggleBootstrapDropdown(toggle) {
    var dd = toggle.closest(".dropdown") || toggle.parentElement;
    var menu = dd && dd.querySelector(".dropdown-menu");
    if (!menu) return;
    var open = menu.classList.contains("show");
    document.querySelectorAll(".dropdown-menu.show").forEach(function (m) {
      m.classList.remove("show");
    });
    if (!open) menu.classList.add("show");
  }

  function switchEmployeeTab(tabLink) {
    var text = (tabLink.textContent || "").toLowerCase();
    var team = document.getElementById("tab-team");
    var rules = document.getElementById("tab-rules");
    if (!team || !rules) return;
    var showRules = text.indexOf("assignment") >= 0 || text.indexOf("rules") >= 0;
    team.style.display = showRules ? "none" : "";
    rules.style.display = showRules ? "" : "none";
    var nav = tabLink.closest(".nav");
    if (nav) {
      nav.querySelectorAll(".nav-link").forEach(function (a) {
        a.classList.remove("active");
      });
    }
    tabLink.classList.add("active");
  }

  // Block POST forms — static server returns 501; handle in-page instead.
  document.addEventListener(
    "submit",
    function (e) {
      var form = e.target;
      if (!form || !form.tagName || form.tagName.toUpperCase() !== "FORM") return;
      var method = (form.getAttribute("method") || "get").toLowerCase();
      if (method === "get" && typeof window.__stitchLikwidFlowSubmit === "function") {
        if (window.__stitchLikwidFlowSubmit(form, e)) return;
      }
      if (method === "get" && typeof window.__stitchReplicaSubmit === "function") {
        if (window.__stitchReplicaSubmit(form, e)) return;
      }
      if (method === "get" && typeof window.__stitchGenericSubmit === "function") {
        if (window.__stitchGenericSubmit(form, e)) return;
      }
      if (method !== "post") return;
      e.preventDefault();
      e.stopPropagation();
      if (typeof window.__stitchLikwidFlowSubmit === "function" && window.__stitchLikwidFlowSubmit(form, e)) {
        return;
      }
      if (typeof window.__stitchReplicaSubmit === "function" && window.__stitchReplicaSubmit(form, e)) {
        return;
      }
      if (typeof window.__stitchGenericSubmit === "function" && window.__stitchGenericSubmit(form, e)) {
        return;
      }
      var sub = e.submitter || form.querySelector("[type='submit'], button:not([type])");
      if (sub && sub.classList.contains("ld-stage")) {
        activateLeadStage(sub);
        return;
      }
      if (sub && sub.hasAttribute("data-stitch-ui-id")) {
        injectInteraction(sub);
        return;
      }
      showDemoHint();
    },
    true
  );

  function collapseWorkloadPanel(toggle) {
    if (!toggle) return;
    toggle.setAttribute("aria-expanded", "false");
    var panelId = toggle.getAttribute("aria-controls");
    var panel = panelId ? document.getElementById(panelId) : null;
    if (panel) {
      panel.classList.remove("show");
      panel.setAttribute("hidden", "true");
      panel.setAttribute("aria-hidden", "true");
    }
  }

  function expandWorkloadPanel(toggle) {
    if (!toggle) return;
    toggle.setAttribute("aria-expanded", "true");
    var panelId = toggle.getAttribute("aria-controls");
    var panel = panelId ? document.getElementById(panelId) : null;
    if (panel) {
      panel.classList.add("show");
      panel.removeAttribute("hidden");
      panel.setAttribute("aria-hidden", "false");
    }
  }

  function toggleStripeWorkloadNav(toggle) {
    var expanded = toggle.getAttribute("aria-expanded") === "true";
    if (expanded) collapseWorkloadPanel(toggle);
    else expandWorkloadPanel(toggle);
  }

  function clearPopperStyles(el) {
    if (!el || !el.style) return;
    el.style.transform = "";
    el.style.inset = "";
    el.style.top = "";
    el.style.left = "";
    el.style.right = "";
    el.style.bottom = "";
    el.style.margin = "";
    el.removeAttribute("data-popper-placement");
    el.removeAttribute("data-popper-reference-hidden");
  }

  function wantsEndAlignment(trigger, placement) {
    if (placement && /end|right/i.test(placement)) return true;
    if (trigger.closest && trigger.closest(".float-end")) return true;
    var dd = trigger.closest && trigger.closest(".dropdown");
    return !!(dd && dd.classList.contains("float-end"));
  }

  function repositionNearTrigger(panel, trigger) {
    var placement = panel.getAttribute("data-popper-placement") || "";
    clearPopperStyles(panel);
    var rect = trigger.getBoundingClientRect();
    panel.style.position = "fixed";
    panel.style.zIndex = "2000";
    panel.style.margin = "0";
    panel.style.top = rect.bottom + "px";
    panel.style.bottom = "auto";

    var menuWidth = panel.offsetWidth || panel.getBoundingClientRect().width || 220;
    var end = wantsEndAlignment(trigger, placement);
    if (end) {
      panel.style.left = Math.max(8, rect.right - menuWidth) + "px";
    } else {
      panel.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - menuWidth - 8)) + "px";
    }
    panel.style.right = "auto";
  }

  function repositionStripeAccountMenu(panel, trigger) {
    var pop = panel.querySelector('[data-testid="popover-layer"]');
    var target = pop || panel;
    clearPopperStyles(panel);
    panel.style.position = "static";
    panel.style.height = "auto";
    panel.style.maxHeight = "none";
    panel.style.overflow = "visible";
    panel.style.width = "auto";
    panel.style.transform = "none";
    panel.style.pointerEvents = "none";
    if (pop) {
      clearPopperStyles(pop);
      pop.style.overflow = "visible";
      pop.style.height = "auto";
      pop.style.maxHeight = "none";
      pop.style.display = "block";
    }
    Array.prototype.forEach.call(
      panel.querySelectorAll(
        '[role="menuitem"], [data-testid="exit-legacy-testmode-button"], .as-bm'
      ),
      function (el) {
        el.style.position = "static";
        el.style.transform = "none";
        el.style.inset = "";
        el.style.top = "";
        el.style.left = "";
        el.style.right = "";
        el.style.bottom = "";
        el.style.width = "";
        el.style.display = el.getAttribute("data-testid") === "exit-legacy-testmode-button"
          ? "flex"
          : "flex";
        el.style.alignItems = "center";
        el.style.width = el.getAttribute("data-testid") === "exit-legacy-testmode-button"
          ? "calc(100% - 24px)"
          : "100%";
        el.style.maxWidth = "100%";
        el.style.height = "auto";
        el.style.minHeight = "36px";
        el.style.gridTemplateColumns = "none";
        el.style.margin = el.getAttribute("data-testid") === "exit-legacy-testmode-button"
          ? "8px 12px"
          : "0";
        el.style.boxSizing = "border-box";
      }
    );
    target.style.position = "fixed";
    target.style.zIndex = "2000";
    target.style.margin = "0";
    target.style.transform = "none";
    target.style.pointerEvents = "auto";
    target.style.display = "block";
    target.style.width = "288px";
    target.style.minWidth = "288px";
    target.style.maxWidth = "320px";
    target.style.boxSizing = "border-box";
    var rect = trigger.getBoundingClientRect();
    var menuWidth = target.offsetWidth || target.getBoundingClientRect().width || 288;
    target.style.top = (rect.bottom + 4) + "px";
    target.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - menuWidth - 8)) + "px";
    target.style.right = "auto";
    target.style.bottom = "auto";
  }

  function isCenteredPanel(panel) {
    var cls = panel.className || "";
    return (
      /quick-add-menu|dropdown-menu-center|multi-col-dropdown/.test(cls) ||
      panel.classList.contains("modal-dialog")
    );
  }

  function repositionCenteredPanel(panel) {
    clearPopperStyles(panel);
    panel.style.position = "fixed";
    panel.style.zIndex = "2000";
    panel.style.margin = "0";
    panel.style.display = "block";
    panel.style.pointerEvents = "auto";
    panel.style.transform = "none";

    var rect = panel.getBoundingClientRect();
    var w = panel.offsetWidth || rect.width || 0;
    var h = panel.offsetHeight || rect.height || 0;
    panel.style.left = Math.max(8, (window.innerWidth - w) / 2) + "px";
    panel.style.top = Math.max(56, (window.innerHeight - h) / 2) + "px";
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }

  function repositionInjectedUI(container, trigger) {
    // HubSpot modals (Schedule meeting, etc.) ship their own fixed overlay CSS.
    // Skip dropdown repositioning and keep the modal stack clickable.
    var hsModal = container.querySelector(
      '[data-component-name="ModalDialog"], [role="dialog"]'
    );
    if (hsModal) {
      container.style.position = "static";
      container.style.pointerEvents = "auto";
      container.style.background = "transparent";
      container.style.border = "0";
      container.style.padding = "0";
      container.style.margin = "0";
      container.querySelectorAll(
        '[role="presentation"], [role="dialog"], [data-action="close"], [aria-label="Close" i], button, [role="button"]'
      ).forEach(function (el) {
        el.style.pointerEvents = "auto";
      });
      return;
    }

    container.style.position = "static";
    container.style.pointerEvents = "none";
    container.style.background = "transparent";
    container.style.border = "0";
    container.style.padding = "0";
    container.style.margin = "0";

    function apply() {
      var panels = container.querySelectorAll(
        ".dropdown-menu, .modal-dialog, .popover, .popover-container, .popper[role='tooltip'], .tooltip, .popper.tooltip, [role='menu'], ul[class*='MenuButton'], ul[class*='StyledMenu'], [data-component-name='UIPopover'], [class*='Popover__StyledPopoverContainer'], [class*='AbstractDropdown__DropdownContent'], [data-floating-ui-portal] > div"
      );
      Array.prototype.forEach.call(panels, function (panel) {
        if (/backdrop|modal-backdrop|arrow/i.test(panel.className || "")) return;
        var wrapper = panel.parentElement;
        if (wrapper && wrapper !== container && wrapper.style && wrapper.style.transform) {
          clearPopperStyles(wrapper);
          wrapper.style.position = "static";
          wrapper.style.overflow = "visible";
        }
        clearPopperStyles(panel);
        panel.style.pointerEvents = "auto";
        if (
          panel.classList.contains("dropdown-menu") ||
          panel.classList.contains("show") ||
          panel.getAttribute("role") === "menu" ||
          panel.getAttribute("data-component-name") === "UIPopover" ||
          /AbstractDropdown__DropdownContent|Popover__StyledPopoverContainer|Popover__StyledFloatingContainer/.test(panel.className || "")
        ) {
          panel.style.display = "block";
        }
        // Stripe Sail menus ship with popper translate()/fixed coords baked in.
        if (panel.classList.contains("sn-token-provider") || panel.querySelector('[data-testid="popover-layer"]')) {
          clearPopperStyles(panel);
          Array.prototype.forEach.call(panel.querySelectorAll("[style]"), function (node) {
            if (/transform|position:\s*fixed/i.test(node.getAttribute("style") || "")) {
              clearPopperStyles(node);
            }
          });
        }
        // Stripe account switcher: outer role=menu is a shell; content lives in popover-layer.
        if (
          panel.getAttribute("role") === "menu" &&
          (panel.querySelector('[data-testid="popover-layer"]') ||
            panel.querySelector('[data-testid="exit-legacy-testmode-button"]'))
        ) {
          repositionStripeAccountMenu(panel, trigger);
          panel.querySelectorAll("a, button, [role='menuitem']").forEach(function (el) {
            el.style.pointerEvents = "auto";
          });
          return;
        }
        if (isCenteredPanel(panel)) {
          repositionCenteredPanel(panel);
        } else {
          repositionNearTrigger(panel, trigger);
        }
        panel.querySelectorAll("a, button, .dropdown-item, [role='menuitem'], [role='option']").forEach(function (el) {
          el.style.pointerEvents = "auto";
        });
      });
    }
    apply();
    requestAnimationFrame(apply);
  }

  function handleInjectedUIClick(e, t) {
    var injected = t.closest(".stitch-injected-ui");
    if (!injected) return false;

    var goTrigger = t.closest("[data-stitch-go]");
    if (goTrigger) {
      e.preventDefault();
      e.stopPropagation();
      window.location.assign(goTrigger.getAttribute("data-stitch-go") || "");
      return true;
    }

    var a = t.closest("a[href]");
    if (a) {
      var href = (a.getAttribute("href") || "").trim();
      if (a.hasAttribute("data-stitch-unresolved")) {
        e.preventDefault();
        e.stopPropagation();
        console.log("[STITCH] Overlay link (uncrawled route)", a.getAttribute("data-stitch-route") || href);
        showDemoHint();
        return true;
      }
      if (href && href !== "#" && href.indexOf("javascript:") !== 0) {
        if (isExternalHref(href)) {
          e.preventDefault();
          e.stopPropagation();
          return true;
        }
        e.preventDefault();
        e.stopPropagation();
        window.location.assign(href);
        return true;
      }
    }

    // Stripe account menu flyouts (workspace/sandbox/create) are not in the clone.
    var acctFlyout = t.closest(
      '[data-testid="account-switcher-sandboxes-menu"],' +
      '[data-testid="account-switcher-create-button"],' +
      '[data-testid="account-switcher-workspace"],' +
      '[data-testid="account-switcher-sign-out-button"]'
    );
    if (acctFlyout) {
      e.preventDefault();
      e.stopPropagation();
      console.log("[STITCH] Account menu (no flyout)", acctFlyout.getAttribute("data-testid") || "");
      showDemoHint("Demo mode — account flyouts are outside the recorded path");
      return true;
    }

    var menuItem = t.closest(".dropdown-item, [role='menuitem'], [role='option']");
    if (menuItem) {
      e.preventDefault();
      e.stopPropagation();
      var scope = menuItem.closest(".dropdown-menu, [role='menu']") || menuItem.parentElement;
      if (scope) {
        Array.prototype.forEach.call(
          scope.querySelectorAll(".dropdown-item.selected-option, .dropdown-item.active, [role='menuitem'].selected-option"),
          function (sib) { sib.classList.remove("selected-option", "active"); }
        );
      }
      menuItem.classList.add("selected-option");
      var btn = menuItem.tagName === "BUTTON" ? menuItem : menuItem.querySelector("button");
      if (btn) btn.classList.add("selected-option");
      console.log("[STITCH] Menu item (demo selection)", (menuItem.textContent || "").trim().slice(0, 48));
      showDemoHint("Demo mode \u2014 create flows are outside the recorded path");
      return true;
    }

    return true;
  }

  function isCloseControl(el) {
    if (!el || el.nodeType !== 1) return false;
    var tag = el.tagName.toLowerCase();
    if (tag !== "button" && tag !== "a" && el.getAttribute("role") !== "button") {
      if (!/backdrop|overlay-mask/.test(el.className || "")) return false;
    }
    var cls = el.className || "";
    if (/\\b(close|btn-close|sidebar-close|modal-close|popover-close-button|close-details)\\b/i.test(cls)) {
      return true;
    }
    if (/close-button|btn-close|close-details|popover-close|modal-backdrop|backdrop/.test(cls)) {
      return true;
    }
    var label = (el.getAttribute("aria-label") || "").toLowerCase();
    if (label.indexOf("close") >= 0 || label === "back") return true;
    if (el.hasAttribute("data-dismiss") || el.hasAttribute("data-bs-dismiss")) return true;
    return false;
  }

  function removeBakedOverlay(root) {
    if (!root) return;
    if (root.parentNode) root.parentNode.removeChild(root);
    else root.style.display = "none";
    document.querySelectorAll(".private-overlay-highlight, .hDDpEi").forEach(function (el) {
      if (el.parentNode) el.parentNode.removeChild(el);
    });
    document.querySelectorAll("[data-floating-ui-inert]").forEach(function (el) {
      el.removeAttribute("data-floating-ui-inert");
    });
    document.querySelectorAll(".stitch-tour-highlight-reset").forEach(function (el) {
      el.classList.remove("stitch-tour-highlight-reset");
    });
  }

  function dismissBakedOverlay(target) {
    if (!target || !target.closest) return false;
    if (target.closest(".stitch-injected-ui")) return false;

    var closeEl = target.closest("[data-action='close'], [aria-label='Close' i]");
    if (closeEl) {
      var pop =
        closeEl.closest("[data-component-name='UIPopover']") ||
        closeEl.closest("[data-floating-ui-portal]");
      if (pop) {
        removeBakedOverlay(pop.closest("[data-floating-ui-portal]") || pop);
        return true;
      }
    }

    var popover = target.closest("[data-component-name='UIPopover']");
    if (popover && isCloseControl(target)) {
      removeBakedOverlay(popover.closest("[data-floating-ui-portal]") || popover);
      return true;
    }

    var btn = target.closest("button, [role='button']");
    if (btn && (btn.textContent || "").trim().toLowerCase() === "dismiss") {
      var card = btn.closest("[class*='CardWrapper'], [class*='CardSection']");
      if (card) {
        removeBakedOverlay(card.closest("[class*='CardWrapper']") || card);
        return true;
      }
    }
    return false;
  }

  function bindCloseControls(container) {
    container.querySelectorAll("button, a, [role='button'], div, span").forEach(function (el) {
      if (!isCloseControl(el)) return;
      el.addEventListener(
        "click",
        function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          removeUI(container);
        },
        true
      );
    });
  }

  function removeUI(container) {
    if (!container) return;
    if (container.__stitchOutside)
      document.removeEventListener("click", container.__stitchOutside, false);
    if (container.__stitchKey)
      document.removeEventListener("keydown", container.__stitchKey, true);
    if (container.parentNode) container.parentNode.removeChild(container);
  }

  function bindClose(container, trigger) {
    bindCloseControls(container);
    // Click anywhere outside the injected UI (and not on the trigger) closes it.
    function outside(ev) {
      if (
        !container.contains(ev.target) &&
        ev.target !== trigger &&
        !(trigger && trigger.contains && trigger.contains(ev.target))
      ) {
        if (container.__stitchRemoving) return;
        container.__stitchRemoving = true;
        removeUI(container);
      }
    }
    container.__stitchOutside = outside;
    // Defer so the click that opened the UI doesn't immediately close it.
    setTimeout(function () {
      document.addEventListener("click", outside, false);
    }, 0);
    // ESC closes too (generic, framework-agnostic).
    function onKey(ev) {
      if (ev.key === "Escape" || ev.keyCode === 27) removeUI(container);
    }
    container.__stitchKey = onKey;
    document.addEventListener("keydown", onKey, true);
  }

  function injectInteraction(trigger) {
    var id = trigger.getAttribute("data-stitch-ui-id");
    var cfg = configFor(id);
    var fallback = cfg && cfg.fallback;
    try {
      if (!cfg || !cfg.uiHtml) throw new Error("no reconciled ui_html");

      // Toggle: a second click on the same trigger closes the open UI.
      var open = document.querySelector(
        '.stitch-injected-ui[data-stitch-ui-id="' + id + '"]'
      );
      if (open) {
        removeUI(open);
        return;
      }

      var parent = cfg.parentSelector
        ? document.querySelector(cfg.parentSelector)
        : document.body;
      if (!parent) {
        console.warn("[STITCH] parentSelector not found, falling back to body:", cfg.parentSelector);
        parent = document.body;
      }

      var container = document.createElement("div");
      container.className = "stitch-injected-ui";
      container.setAttribute("data-stitch-ui-id", id);
      container.setAttribute("data-stitch-type", cfg.type || "");
      if (cfg.uiCss) {
        var styleEl = document.createElement("style");
        styleEl.setAttribute("data-stitch-injected-css", id);
        styleEl.textContent = cfg.uiCss;
        container.appendChild(styleEl);
      }
      if (cfg.backdropHtml) container.insertAdjacentHTML("beforeend", cfg.backdropHtml);
      container.insertAdjacentHTML("beforeend", cfg.uiHtml);

      var method = (cfg.insertMethod || "append").toLowerCase();
      if (method === "replace") {
        parent.innerHTML = "";
        parent.appendChild(container);
      } else if (method === "prepend" || method === "insert" || method === "afterbegin") {
        parent.insertAdjacentElement("afterbegin", container);
      } else {
        parent.insertAdjacentElement("beforeend", container);
      }

      bindClose(container, trigger);
      repositionInjectedUI(container, trigger);
      console.log("[STITCH] Inject UI", id, "type=" + (cfg.type || "?"), "→", cfg.parentSelector);
    } catch (err) {
      console.warn("[STITCH] UI injection failed → snapshot fallback", id, err);
      if (fallback) {
        window.location.href = fallback;
      } else {
        showDemoHint();
      }
    }
  }

  document.addEventListener(
    "click",
    function (e) {
      var t = eventTargetDeep(e);
      if (!t || !t.closest) return;

      // Clicks inside an open injected overlay: navigate local links / demo-select items.
      if (handleInjectedUIClick(e, t)) return;

      // Stripe Products sidebar (Payments, Billing, Reporting, Apps, More).
      var workloadToggle = t.closest("[data-testid^='toggle-workload-']");
      if (workloadToggle) {
        e.preventDefault();
        e.stopPropagation();
        toggleStripeWorkloadNav(workloadToggle);
        console.log(
          "[STITCH] Products nav",
          workloadToggle.getAttribute("data-testid"),
          workloadToggle.getAttribute("aria-expanded") === "true" ? "expanded" : "collapsed"
        );
        return;
      }

      // 0. Bootstrap modal dismiss (close button / backdrop).
      var dismiss = t.closest("[data-bs-dismiss='modal'], .modal .btn-close");
      if (dismiss) {
        var openModal = dismiss.closest(".modal.show") ||
          (dismiss.getAttribute("data-bs-dismiss") === "modal" && document.querySelector(".modal.show"));
        if (openModal) {
          e.preventDefault();
          e.stopPropagation();
          hideBootstrapModal(openModal);
          return;
        }
      }

      // 0b. Bootstrap tabs (Metronic nav-tabs).
      var tabLink = t.closest("[data-bs-toggle='tab']");
      if (tabLink && tabLink.getAttribute("href")) {
        e.preventDefault();
        e.stopPropagation();
        activateBootstrapTab(tabLink);
        console.log("[STITCH] Tab", tabLink.getAttribute("href"));
        return;
      }

      // 0c. Bootstrap modals already present in the page snapshot. Takes
      // priority over data-stitch-ui-id — if the modal target exists in the
      // DOM, open it natively instead of replaying a (possibly mis-wired)
      // captured interaction snapshot.
      var modalTrigger = t.closest("[data-bs-toggle='modal']");
      if (modalTrigger) {
        var targetSel = modalTrigger.getAttribute("data-bs-target") || "";
        var modalEl = targetSel ? document.querySelector(targetSel) : null;
        if (modalEl) {
          e.preventDefault();
          e.stopPropagation();
          showBootstrapModal(modalEl);
          console.log("[STITCH] Modal", targetSel);
          return;
        }
      }

      // 0d. Likwid pipeline view switcher (Leads / Funnel / Deals).
      var pipeBtn = t.closest(".up-pipe-btn");
      if (pipeBtn) {
        e.preventDefault();
        e.stopPropagation();
        switchLikwidPipeline(pipeBtn);
        console.log("[STITCH] Pipeline", (pipeBtn.textContent || "").trim());
        return;
      }

      // 0e. Bootstrap dropdown toggles (pipeline cards, employee menus, etc.).
      var ddToggle = t.closest("[data-bs-toggle='dropdown']");
      if (ddToggle && !ddToggle.hasAttribute("data-stitch-ui-id")) {
        e.preventDefault();
        e.stopPropagation();
        toggleBootstrapDropdown(ddToggle);
        return;
      }

      // 0f. Lead detail stage buttons (NVS) — avoid POST submit.
      var stageBtn = t.closest("button.ld-stage");
      if (stageBtn) {
        e.preventDefault();
        e.stopPropagation();
        activateLeadStage(stageBtn);
        console.log("[STITCH] Lead stage", stageBtn.getAttribute("name") || "");
        return;
      }

      // 0g. Employee list — Sales Team vs Assignment Rules tabs.
      var empTab = t.closest(".nav-line-tabs a.nav-link, .nav-line-tabs-2x a.nav-link");
      if (empTab && document.getElementById("tab-team") && document.getElementById("tab-rules")) {
        e.preventDefault();
        e.stopPropagation();
        switchEmployeeTab(empTab);
        return;
      }

      // 0h. BI dashboard filter chips (Categories / Vendors / date).
      var filterBtn = t.closest("button.filter-btn");
      if (filterBtn && !filterBtn.closest(".stitch-injected-ui")) {
        e.preventDefault();
        e.stopPropagation();
        var bar = filterBtn.closest(".filters-left, .filters-bar, .card-toolbar") || filterBtn.parentElement;
        if (bar) {
          bar.querySelectorAll(".filter-btn").forEach(function (b) {
            b.classList.remove("filter-btn-active");
          });
        }
        filterBtn.classList.add("filter-btn-active");
        console.log("[STITCH] Filter", (filterBtn.textContent || "").trim());
        return;
      }

      // 0j. Rastaa dashboard — weather toggle + filter chips (not stitch interactions).
      if (raastaWeather) {
        var rwFilter = raastaWeather.isFilterClick(t);
        if (rwFilter) {
          e.preventDefault();
          e.stopPropagation();
          raastaWeather.select(rwFilter);
          return;
        }
        if (raastaWeather.isWeatherClick(t)) {
          e.preventDefault();
          e.stopPropagation();
          raastaWeather.toggle();
          return;
        }
      }

      // 0k. Rastaa riders — Add Driver modal, Cancel, save to localStorage.
      if (raastaRiders && raastaRiders.handleClick(t, e)) {
        return;
      }

      // 0i. Likwid Flow sidebar links (Inventory submenu, Procurement, etc.) — must run
      // before accordion handler, which also matches clicks inside [data-stitch-accordion].
      var likwidSideNav = t.closest("#kt_app_sidebar a[data-stitch-page], #kt_app_sidebar a[data-stitch-go]");
      if (likwidSideNav) {
        if (likwidSideNav.hasAttribute("data-stitch-unresolved")) {
          e.preventDefault();
          e.stopPropagation();
          console.log("[STITCH] Sidebar Link (unresolved route)", likwidSideNav.getAttribute("data-stitch-route") || "#");
          showDemoHint();
          return;
        }
        var likwidHref = likwidSideNav.getAttribute("data-stitch-go") || likwidSideNav.getAttribute("href") || "";
        if (likwidHref && likwidHref !== "#" && likwidHref.indexOf("javascript:") !== 0) {
          if (isExternalHref(likwidHref)) {
            e.preventDefault();
            e.stopPropagation();
            return;
          }
          e.preventDefault();
          e.stopPropagation();
          window.location.assign(likwidHref);
          console.log("[STITCH] Sidebar Link", likwidHref);
          return;
        }
      }

      // 1. Sidebar accordion toggle — purely in-page, never loads a snapshot.
      var acc = t.closest("[data-stitch-accordion]");
      if (acc && !t.closest(".menu-sub a")) {
        e.preventDefault();
        e.stopPropagation();
        var expanded = acc.getAttribute("aria-expanded") === "true";
        acc.setAttribute("aria-expanded", expanded ? "false" : "true");
        if (expanded) acc.classList.add("collapsed");
        else acc.classList.remove("collapsed");
        if (acc.classList.contains("menu-accordion")) {
          if (expanded) acc.classList.remove("show");
          else acc.classList.add("show");
        }
        var panel = findPanel(acc);
        if (panel) {
          if (expanded) {
            panel.classList.remove("show");
            panel.setAttribute("hidden", "true");
          } else {
            panel.classList.add("show");
            panel.removeAttribute("hidden");
          }
        }
        console.log("[STITCH] Accordion Toggle", acc.getAttribute("data-stitch-accordion") || (panel && panel.id) || "?", expanded ? "→ collapse" : "→ expand");
        return;
      }

      // 1b. Woven page links beat ancestor interaction wrappers (mis-bound triggers).
      var navA = t.closest("a[data-stitch-page], a[data-stitch-go]");
      if (navA) {
        if (navA.hasAttribute("data-stitch-unresolved")) {
          e.preventDefault();
          e.stopPropagation();
          console.log("[STITCH] Sidebar Link (unresolved route)", navA.getAttribute("data-stitch-route") || "#");
          showDemoHint();
          return;
        }
        var navHref = navA.getAttribute("data-stitch-go") || navA.getAttribute("href") || "";
        if (navHref && navHref !== "#" && navHref.indexOf("javascript:") !== 0) {
          if (isExternalHref(navHref)) {
            e.preventDefault();
            e.stopPropagation();
            return;
          }
          e.preventDefault();
          e.stopPropagation();
          window.location.assign(navHref);
          console.log("[STITCH] Sidebar Link", navHref);
          return;
        }
      }

      // 2. Interaction → inject reconciled UI into the current page (no reload).
      var uiTrigger = t.closest("[data-stitch-ui-id]");
      if (uiTrigger && !uiTrigger.classList.contains("stitch-injected-ui") && !uiTrigger.classList.contains("up-pipe-btn")) {
        e.preventDefault();
        e.stopPropagation();
        injectInteraction(uiTrigger);
        return;
      }

      // 3. Tab switch — replace content region in-place.
      var tabTrigger = t.closest("[data-stitch-tab-id]");
      if (tabTrigger) {
        e.preventDefault();
        e.stopPropagation();
        var tabId = tabTrigger.getAttribute("data-stitch-tab-id");
        var tabCfg = (window.__STITCH_TABS__ || {})[tabId];
        if (tabCfg && tabCfg.contentSelector && tabCfg.contentHtml) {
          var panel = document.querySelector(tabCfg.contentSelector);
          if (panel) panel.innerHTML = tabCfg.contentHtml;
          var par = tabTrigger.parentElement;
          if (par) {
            Array.prototype.forEach.call(
              par.querySelectorAll("[data-stitch-tab-id]"),
              function (sib) {
                sib.classList.remove("active", "selected");
                sib.setAttribute("aria-selected", "false");
              }
            );
          }
          tabTrigger.classList.add("active");
          tabTrigger.setAttribute("aria-selected", "true");
          console.log("[STITCH] Tab Switch", tabId, "→", tabCfg.contentSelector);
        }
        return;
      }

      // 4. Non-anchor page navigation discovered during crawl.
      var goTrigger = t.closest("[data-stitch-go]");
      if (goTrigger) {
        e.preventDefault();
        e.stopPropagation();
        window.location.assign(goTrigger.getAttribute("data-stitch-go") || "");
        return;
      }

      // 5. Page navigation: local rewritten anchors work natively. Block any
      //    leftover production/external link so nothing escapes the clone.
      var a = t.closest("a[href]");
      if (a) {
        var href = a.getAttribute("href") || "";
        if (a.hasAttribute("data-stitch-unresolved")) {
          console.log("[STITCH] Sidebar Link (unresolved route)", a.getAttribute("data-stitch-route") || "#");
          showDemoHint();
        } else if (a.hasAttribute("data-stitch-page")) {
          console.log("[STITCH] Sidebar Link", href);
        }
        if (/^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0) {
          e.preventDefault();
        }
        return;
      }

      // 5b. Baked-in HubSpot coaching popovers / dismissible banners (crawl snapshot).
      if (dismissBakedOverlay(t)) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }

      // 6. Unwired button — show demo hint so the viewer knows the click was
      //    registered but is outside the recorded demo path.
      var btn = t.closest("button,input[type='button'],input[type='submit'],[role='button']");
      if (
        btn &&
        !btn.closest(".stitch-injected-ui") &&
        !btn.hasAttribute("data-stitch-ui-id") &&
        !btn.hasAttribute("data-raasta-weather-toggle") &&
        !btn.hasAttribute("data-raasta-add-rider") &&
        !btn.hasAttribute("data-raasta-edit-rider") &&
        !btn.hasAttribute("data-raasta-delete-rider") &&
        !btn.closest(".raasta-weather-filters") &&
        !btn.closest(".raasta-rider-modal") &&
        !btn.hasAttribute("data-stitch-go") &&
        !btn.hasAttribute("data-stitch-tab-id") &&
        !btn.hasAttribute("data-stitch-accordion")
      ) {
        showDemoHint();
      }
    },
    true
  );

  // ── Stripe sidebar shortcuts normalizer ──────────────────────────────────
  // Each Stripe page was crawled independently and captured its own dynamic
  // shortcuts list. This normalises the labels + hrefs to a canonical set at
  // runtime without touching CSS classes (which are per-page and must stay).
  (function standardizeShortcuts() {
    var ul = document.querySelector('[data-testid="shortcuts-nav-links"]');
    if (!ul) return;
    var parts = window.location.pathname.split("/").filter(Boolean);
    var ups = parts.length - 1;
    var prefix = "";
    for (var i = 0; i < ups; i++) prefix += "../";
    var canonical = [
      ["recent-nav-item-radar",          "Radar",         "test-radar/page.html"],
      ["recent-nav-item-paymentLinks",   "Payment Links", "acct-1Tn1qNH9lf8tLTJg-test-payment-links/page.html"],
      ["recent-nav-item-businessNetwork","Profiles",      "acct-1Tn1qNH9lf8tLTJg-test-profiles/page.html"],
      ["recent-nav-item-reports",        "Reports",       "acct-1Tn1qNH9lf8tLTJg-test-reporting/page.html"],
      ["recent-nav-item-apps",           "Apps",          "acct-1Tn1qNH9lf8tLTJg-test-apps-installed/page.html"],
    ];
    canonical.forEach(function(c) {
      var li = ul.querySelector('[data-testid="' + c[0] + '"]');
      if (!li) return;
      var spans = li.querySelectorAll("span");
      for (var i = spans.length - 1; i >= 0; i--) {
        if (!spans[i].children.length && spans[i].textContent.trim()) {
          spans[i].textContent = c[1];
          break;
        }
      }
      var a = li.querySelector("a[href]");
      if (a) a.setAttribute("href", prefix + c[2]);
    });
  })();
  // ── End Stripe sidebar shortcuts normalizer ───────────────────────────────

  console.log("[STITCH] runtime ready");
})();
"""

_INERT_PREFIXES = ("javascript:", "mailto:", "tel:", "data:", "blob:")


def _is_raasta_app(app_name: str) -> bool:
    return app_name == "raasta" or app_name.startswith("raasta")


_RAASTA_MAP_PAGES = frozenset({"home", "dashboard"})
_RAASTA_PUNE_CENTER = [73.8567, 18.5204]
_RAASTA_MELBOURNE_CENTER = [144.971, -37.807]

# Inline raster style — no style.json network fetch (main cause of 5s+ delay).
_RAASTA_FAST_MAP_STYLE: dict = {
    "version": 8,
    "sources": {
        "osm": {
            "type": "raster",
            "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            "tileSize": 256,
            "maxzoom": 19,
        }
    },
    "layers": [{"id": "osm", "type": "raster", "source": "osm"}],
}

_RAASTA_MAP_LAYOUT_CSS = """\
.maplibregl-map {
  position: relative !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 320px !important;
}
.maplibregl-canvas,
.maplibregl-map .maplibregl-canvas-container {
  width: 100% !important;
  height: 100% !important;
}
@media (min-width: 768px) {
  .raasta-map-panel { display: block !important; }
}
"""

_RAASTA_PAGE_MAP_DEFAULTS: dict[str, dict] = {
    "home": {"center": _RAASTA_PUNE_CENTER, "zoom": 11, "demo_markers": 0},
    "dashboard": {"center": _RAASTA_MELBOURNE_CENTER, "zoom": 11.5, "demo_markers": 30},
}


def _raasta_demo_delivery_geojson(count: int, center: list[float]) -> dict:
    import math

    lng, lat = center[0], center[1]
    features = []
    for i in range(count):
        angle = (i / max(count, 1)) * math.pi * 2
        ring = 0.35 + (i % 5) * 0.13
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        lng + math.cos(angle) * 0.045 * ring,
                        lat + math.sin(angle) * 0.032 * ring,
                    ],
                },
                "properties": {"id": i + 1},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _raasta_stitch_map_states(slug: str, page_dir: Path | None, html: str) -> list[dict]:
    """Rastaa-only: build map configs for stitch (inline style, no remote style.json)."""
    states = load_map_state(page_dir)
    if states and any(s.get("style") or s.get("geojsonSources") for s in states):
        return states

    page_default = _RAASTA_PAGE_MAP_DEFAULTS.get(slug)
    if not page_default:
        return []

    count = max(1, html.count("maplibregl-map"))
    out: list[dict] = []
    for _ in range(count):
        geojson_sources: list[dict] = []
        if page_default.get("demo_markers"):
            geojson_sources.append(
                {
                    "sourceId": "raasta-demo-deliveries",
                    "data": _raasta_demo_delivery_geojson(
                        int(page_default["demo_markers"]),
                        page_default["center"],
                    ),
                }
            )
        out.append(
            {
                "center": list(page_default["center"]),
                "zoom": page_default["zoom"],
                "bearing": 0,
                "pitch": 0,
                "style": _RAASTA_FAST_MAP_STYLE,
                "geojsonSources": geojson_sources,
            }
        )
    return out


def _inject_raasta_maps(soup: BeautifulSoup, to_root: str, slug: str, map_states: list[dict]) -> bool:
    """Rastaa-only: inject map assets early in <head> for fast first paint."""
    if not map_states:
        return False

    head = soup.head
    body = soup.body
    if not head or not body:
        return False

    body["data-raasta-page"] = slug

    if not head.find("style", id="raasta-map-layout-css"):
        style_tag = soup.new_tag("style", id="raasta-map-layout-css")
        style_tag.string = _RAASTA_MAP_LAYOUT_CSS
        head.append(style_tag)

    js_rel = "vendor/maplibre/maplibre-gl.js"
    css_rel = "vendor/maplibre/maplibre-gl.css"
    js_src = f"{to_root}assets/{js_rel}"
    css_href = f"{to_root}assets/{css_rel}"

    if not head.find("link", href=lambda h: h and "maplibre-gl.css" in h):
        preload = soup.new_tag("link", rel="preload", href=js_src)
        preload["as"] = "script"
        head.append(preload)
        head.append(soup.new_tag("link", rel="stylesheet", href=css_href))

    if not any(
        "__RASTAA_MAPS__" in (tag.string or "")
        for tag in head.find_all("script")
    ):
        data = json.dumps(map_states, ensure_ascii=True).replace("</", "<\\/")
        cfg_tag = soup.new_tag("script")
        cfg_tag.string = f"window.__RASTAA_MAPS__ = {data};"
        head.append(cfg_tag)

    if not head.find("script", src=lambda s: s and "maplibre-gl.js" in s):
        ml = soup.new_tag("script", src=js_src)
        head.append(ml)

    maps_src = f"{to_root}raasta_maps.js"
    if not body.find("script", src=lambda s: s and s.endswith("raasta_maps.js")):
        body.append(soup.new_tag("script", src=maps_src))

    return True


def _unwire_raasta_weather_interaction(
    soup: BeautifulSoup, configs: dict[str, dict]
) -> None:
    """Dashboard Weather is handled by raasta_ui.js — drop stitch interaction wiring."""
    for btn in soup.find_all("button"):
        text = btn.get_text(" ", strip=True)
        if text != "Weather":
            continue
        ui_id = btn.get("data-stitch-ui-id")
        if ui_id:
            configs.pop(ui_id, None)
            del btn["data-stitch-ui-id"]
        btn["data-raasta-weather-toggle"] = ""
        break


def _extract_raasta_rider_modal_html(page_dir: Path) -> str:
    """Pull the Add Rider overlay from the crawled interaction snapshot."""
    ipath = page_dir / "interactions" / "003-add-driver" / "page.html"
    if not ipath.is_file():
        return ""
    try:
        soup = BeautifulSoup(ipath.read_text(encoding="utf-8"), "html.parser")
    except Exception:
        return ""
    for div in soup.find_all("div"):
        classes = div.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        cls = " ".join(classes)
        if "fixed" in cls and "inset-0" in cls and "z-[10000]" in cls:
            if "Add New Rider" not in div.get_text(" ", strip=True):
                continue
            if isinstance(div.get("class"), list):
                div["class"] = [*div["class"], "raasta-rider-modal"]
            else:
                div["class"] = f"{div['class']} raasta-rider-modal"
            return str(div)
    return ""


def _unwire_raasta_add_driver_interaction(
    soup: BeautifulSoup, configs: dict[str, dict]
) -> None:
    """Riders Add Driver is handled in runtime.js — drop stitch interaction wiring."""
    for btn in soup.find_all("button"):
        if btn.get_text(" ", strip=True) != "Add Driver":
            continue
        ui_id = btn.get("data-stitch-ui-id")
        if ui_id:
            configs.pop(ui_id, None)
            del btn["data-stitch-ui-id"]
        btn["data-raasta-add-rider"] = ""
        break


def _inject_raasta_riders_page(
    soup: BeautifulSoup, configs: dict[str, dict], page_dir: Path
) -> None:
    """Rastaa riders list: tag page + embed modal HTML for in-page Add Driver."""
    body = soup.body
    if not body:
        return
    body["data-raasta-page"] = "riders"
    _unwire_raasta_add_driver_interaction(soup, configs)
    modal_html = _extract_raasta_rider_modal_html(page_dir)
    if not modal_html:
        return
    if body.find("script", id="raasta-rider-modal-tpl"):
        return
    script = soup.new_tag("script", id="raasta-rider-modal-tpl")
    script.string = f"window.__RAASTA_RIDER_MODAL_HTML__ = {json.dumps(modal_html)};"
    body.append(script)


def _tag_raasta_riders_interaction_page(soup: BeautifulSoup) -> None:
    """Tag the baked-in Add Rider overlay on the interaction snapshot page."""
    body = soup.body
    if body:
        body["data-raasta-page"] = "riders"
    for div in soup.find_all("div"):
        classes = div.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        cls = " ".join(classes)
        if "fixed" in cls and "inset-0" in cls and "z-[10000]" in cls:
            if "Add New Rider" not in div.get_text(" ", strip=True):
                continue
            existing = div.get("class") or []
            if isinstance(existing, str):
                existing = existing.split()
            if "raasta-rider-modal" not in existing:
                div["class"] = [*existing, "raasta-rider-modal"]
            break


def _inject_raasta_ui(soup: BeautifulSoup, to_root: str, slug: str) -> None:
    """Rastaa dashboard: load stitched raasta_ui.js (Trips flyout + weather filters)."""
    body = soup.body
    if not body:
        return
    body["data-raasta-page"] = slug
    ui_src = f"{to_root}raasta_ui.js"
    if body.find("script", src=lambda s: s and s.endswith("raasta_ui.js")):
        return
    body.append(soup.new_tag("script", src=ui_src))


_ENTRY_TITLE_HINTS = ("dashboard",)
_ENTRY_SLUG_HINTS = (
    "contacts-list-view-all",  # HubSpot — contacts list is the best landing page
    "global-home",             # HubSpot — home overview
    "test-dashboard",          # Stripe sandbox home
    "home-dashboard",          # Zoho
    "dashboard",
    "home",
)

# Generic class tokens that mark an element as an accordion *toggle* (the
# clickable header), independent of any particular app. No Zoho-specific names.
_ACCORDION_CLASS_TOKENS = {
    "accordion-button",
    "accordion-title",
    "accordion-toggle",
    "accordion-header",
    "accordion-trigger",
    "menu-accordion",
}

# Inline style declarations that freeze interactivity. Pages crawled mid-load
# often capture these on nav containers, permanently disabling the clone.
_POINTER_EVENTS_NONE_RE = re.compile(r"pointer-events\s*:\s*none\s*;?", re.I)
_USER_SELECT_NONE_RE = re.compile(r"user-select\s*:\s*none\s*;?", re.I)
_INTERACTIVE_TAGS = ("a", "button", "input", "select", "textarea")

# Belt-and-suspenders CSS override injected into every page so nav stays live
# even if some inline freeze slipped through.
_INTERACTION_FIX_CSS = """#main-nav-tab,
#main-nav-tab *,
.main-nav-lhs,
.main-nav-lhs * {
    pointer-events:auto !important;
}
.quick-add-menu.dropdown-menu-center,
.stitch-injected-ui .quick-add-menu.dropdown-menu-center {
    position: fixed !important;
    inset: auto !important;
    top: 50% !important;
    left: 50% !important;
    right: auto !important;
    bottom: auto !important;
    transform: translate(-50%, -50%) !important;
    margin: 0 !important;
    z-index: 2000;
}
.stitch-injected-ui .dropdown-menu,
.stitch-injected-ui .dropdown-menu .dropdown-item,
.stitch-injected-ui .dropdown-menu button,
.stitch-injected-ui .dropdown-menu a,
.stitch-injected-ui [role="menu"],
.stitch-injected-ui [role="menuitem"],
.stitch-injected-ui [role="menu"] button,
.stitch-injected-ui [data-component-name="UIPopover"],
.stitch-injected-ui [class*="AbstractDropdown__DropdownContent"],
.stitch-injected-ui [class*="Popover__StyledPopoverContainer"],
.stitch-injected-ui .popover-container,
.stitch-injected-ui .popover {
    pointer-events: auto !important;
}
/* HubSpot main content — keep toolbar, filters, and table rows clickable. */
#hs-global-toolbar button,
#hs-global-toolbar [role="button"],
[data-test-id="filter-bar-container"] button,
[data-test-id="filter-bar-container"] [role="button"],
[data-selenium-test="FiltersBar-container"] button,
.PrivateButton__StyledButton-eRHhiA,
[data-stitch-ui-id],
[data-stitch-go],
[data-stitch-tab-id],
[role="menuitem"] {
    pointer-events: auto !important;
    cursor: pointer;
}

/* Production overlays/widgets — broken or distracting in the static clone. */
#annmsgstrip,
.zread_strip,
books_svgs,
.micshide,
#zcwindows,
.zcoverlay,
.zsiq_theme1,
#zsiq_float,
#zsiq_chat_wrap,
iframe#avcliqiframe,
#wmstoolbar,
#micsbackdrop,
#tooltip-popover-wrapper,
#zgs20_globalsearch,
#zgs20_gsSearchResultsArea,
#zgs20_gsResultsHolder,
#zgs20_gsSearchTopBandHolder,
.zgs19_gsOverlay,
#zgs20_gsOverlay,
.popover-container,
.finance-app .rhs-sidebar,
.finance-app .rhs-menu,
.finance-app #rhs-menu-bar,
.finance-app .rhs-sidebar-menu {
    display: none !important;
    pointer-events: none !important;
}
/* Empty captured flyout shells from live app — break flex layout in the clone. */
.finance-app .slide-sidebar,
.finance-app .sidebar-container {
    display: none !important;
    pointer-events: none !important;
}

/* ── HubSpot-specific fixes ──────────────────────────────────────────────────
   styled-components injects icon sizing at runtime; strip_scripts() empties
   those <style> tags. These rules provide safe fallback sizing for all SVGs
   that land in the static snapshot without explicit width/height attributes. */
svg:not([width]):not([height]) {
    width: 16px;
    height: 16px;
    overflow: hidden;
    flex-shrink: 0;
}
#hs-global-toolbar svg,
#hs-nav-v4 svg,
[data-test-id="nav-primary"] svg {
    max-width: 32px !important;
    max-height: 32px !important;
    overflow: hidden !important;
    flex-shrink: 0;
}
/* Toolbar must remain clickable for interaction wiring to work. */
#hs-global-toolbar,
#hs-global-toolbar * {
    pointer-events: auto !important;
}
/* Live-only HubSpot widgets that are broken or distracting in the static clone. */
#hs-feedback-fetcher,
.growth-dynamic-namespace,
#hs-nav-v4 iframe,
.UIPlaceholderBubble__Placeholder-mfCgX {
    display: none !important;
    pointer-events: none !important;
}
/* HubSpot blanket pointer-events restore — nav, sidebar, buttons, tabs */
#hs-nav-v4 a, #hs-nav-v4 button, #hs-nav-v4 [role="tab"],
#hs-nav-v4 [role="menuitem"], #hs-nav-v4 li,
[data-test-id="nav-primary"] a,
[data-test-id="nav-primary"] button,
[data-test-id="nav-primary"] [role="tab"],
#hs-global-toolbar a, #hs-global-toolbar button,
.private-page__outer button,
.private-page__outer a,
.private-page__outer [role="tab"],
.private-page__outer [role="menuitem"] {
    pointer-events: auto !important;
    cursor: pointer !important;
}
/* Kill invisible overlay divs that intercept clicks above interactive content */
.UIOverlay--invisible,
[data-overlay-type],
.private-overlay--invisible {
    pointer-events: none !important;
    display: none !important;
}
/* HubSpot loading/skeleton states — API never resolves in the static clone */
[data-test-id="loading-spinner"],
.private-loading-page,
.private-spinner-container,
.loading-page-wrapper,
.UIOverlay--blocker,
[data-loading="true"] {
    display: none !important;
}
/* Coaching popovers / tour highlights frozen open during crawl */
body > [data-floating-ui-portal],
.private-overlay-highlight {
    display: none !important;
    pointer-events: none !important;
}
/* HubSpot tour scrim overlay baked during crawl (e.g. AEO coaching walkthrough).
   Only target .hDDpEi — do NOT hide [class*="Overlay__StyledInner"] globally;
   legitimate modals (Schedule meeting, etc.) use the same overlay wrapper when
   injected at runtime via .stitch-injected-ui. Baked .hDDpEi nodes are also
   removed in _strip_baked_onboarding_ui(); this rule is a belt-and-suspenders
   fallback for any that survive on main page snapshots. */
.hDDpEi {
    display: none !important;
    pointer-events: none !important;
}
.stitch-tour-highlight-reset {
    z-index: auto !important;
    border: none !important;
    margin-block: 0 !important;
}

/* HubSpot: hide live-only widgets; captured CSS handles layout when present. */
#notificationBannerContainer,
[data-test-id="notificationBannerContainer"],
div#growth-dynamic-ui,
#hs-feedback-fetcher,
.copilot-sidebar-container,
.quartz-grid-sidebar-container,
iframe[name*="chatspot"],
iframe[name*="mini-trial-guide"] {
    display: none !important;
}

/* ── Stripe dashboard fixes ───────────────────────────────────────────────── */
/* Full-viewport sail portal shells (inset:0, z-index:299) block all clicks. */
body > .__sail-layer-containers:empty {
    display: none !important;
    pointer-events: none !important;
}
body > .__sail-layer-containers {
    pointer-events: none !important;
}
/* Captured Stripe CSS sets .as-4g { pointer-events:none } on #chrome-layout. */
#chrome-layout,
#chrome-layout.as-4g,
#chrome-layout *,
.as-4g {
    pointer-events: auto !important;
}
#dashboardRoot {
    pointer-events: auto !important;
    visibility: visible !important;
    opacity: 1 !important;
}
/* Do not hide the whole Stripe shell when captured mid-load */
#dashboardRoot [data-loading="true"],
#dashboardRoot [aria-busy="true"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}
#dashboardRoot [class*="Spinner"],
#dashboardRoot [role="progressbar"] {
    display: none !important;
}
#primary-nav,
#primary-nav a,
[data-testid="primary-nav"] a,
a[data-stitch-page],
#dashboardRoot a,
#dashboardRoot button,
#dashboardRoot [role="button"],
#dashboardRoot [role="tab"],
#dashboardRoot [role="menuitem"],
[class*="db-Nav"] a,
[class*="db-Nav"] button,
[class*="sail-Nav"] a,
[class*="sail-Nav"] button,
[data-stitch-accordion],
[data-stitch-ui-id],
[data-stitch-go],
[data-stitch-tab-id] {
    pointer-events: auto !important;
    cursor: pointer !important;
}
/* Invisible PressableCore overlays block button clicks in the static clone */
.PressableCore-overlay,
.PressableCore-overlay--isVisible {
    pointer-events: none !important;
}
/* Stripe metrics iframe + hidden portal containers */
iframe[name*="StripeMetrics"],
iframe[name*="privateStripeMetrics"],
.__sail-layer-containers[style*="display: none"] {
    display: none !important;
    pointer-events: none !important;
}
#dashboardRoot [class*="Spinner"],
#dashboardRoot [class*="LoadingOverlay"],
#dashboardRoot [role="progressbar"] {
    display: none !important;
}
#chrome-layout-backdrop,
[data-testid="backdrop"] {
    display: none !important;
    pointer-events: none !important;
}

/* Stripe Products section: prevent flex-grow / space-between from stretching nav rows. */
#primary-nav [data-testid="workloads-nav"],
[data-testid="primary-nav"] [data-testid="workloads-nav"],
#primary-nav section:has([data-testid="workloads-nav"]) .primary-nav-section-header,
[data-testid="primary-nav"] section:has([data-testid="workloads-nav"]) .primary-nav-section-header {
    justify-content: flex-start !important;
    --s--distribute: flex-start !important;
    text-align: left !important;
}
#primary-nav [data-testid="workloads-nav-links"],
[data-testid="primary-nav"] [data-testid="workloads-nav-links"],
#primary-nav section:has([data-testid="workloads-nav"]) > ul,
[data-testid="primary-nav"] section:has([data-testid="workloads-nav"]) > ul {
    flex: 0 0 auto !important;
    flex-grow: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    justify-content: flex-start !important;
    --s--distribute: flex-start !important;
}
#primary-nav [data-testid="workloads-nav-links"] > li,
[data-testid="primary-nav"] [data-testid="workloads-nav-links"] > li,
#primary-nav section:has([data-testid="workloads-nav"]) > ul > li,
[data-testid="primary-nav"] section:has([data-testid="workloads-nav"]) > ul > li {
    flex: 0 0 auto !important;
    flex-grow: 0 !important;
    --s--flex-y: 0 0 auto !important;
}
#primary-nav section:has([data-testid="workloads-nav"]),
[data-testid="primary-nav"] section:has([data-testid="workloads-nav"]) {
    flex: 0 0 auto !important;
    flex-grow: 0 !important;
}

/* Injected Stripe Products submenu (crawl snapshots omit collapsed panel HTML). */
#primary-nav [data-testid="workloads-nav-links"] > li,
[data-testid="primary-nav"] [data-testid="workloads-nav-links"] > li,
#primary-nav section:has([data-testid="workloads-nav"]) > ul > li,
[data-testid="primary-nav"] section:has([data-testid="workloads-nav"]) > ul > li {
    display: list-item !important;
    flex: 0 0 auto !important;
    flex-shrink: 0 !important;
    width: 100% !important;
    min-height: 0 !important;
}
#primary-nav .stitch-workload-nav-panel,
[data-testid="primary-nav"] .stitch-workload-nav-panel {
    list-style: none;
    margin: 0;
    padding: 0;
    overflow: hidden;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
}
#primary-nav .stitch-workload-nav-panel.show,
[data-testid="primary-nav"] .stitch-workload-nav-panel.show {
    display: block !important;
    padding: 0 0 4px !important;
    visibility: visible !important;
    overflow: visible !important;
    justify-content: flex-start !important;
    --s--distribute: flex-start !important;
}
#primary-nav .stitch-workload-nav-panel:not(.show),
[data-testid="primary-nav"] .stitch-workload-nav-panel[hidden] {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
#primary-nav .stitch-workload-nav-panel > li,
[data-testid="primary-nav"] .stitch-workload-nav-panel > li {
    display: block !important;
    list-style: none;
    margin: 0;
    padding: 0 12px 0 36px;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    flex: 0 0 auto !important;
    --s--flex-y: 0 0 auto !important;
}
#primary-nav .stitch-workload-nav-panel a,
[data-testid="primary-nav"] .stitch-workload-nav-panel a {
    display: flex !important;
    align-items: center;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    flex: 1 1 auto !important;
    --s--flex-x: 1 1 auto !important;
    --s--flex-y: 0 0 auto !important;
    --s--object-width: auto !important;
    box-sizing: border-box;
    text-decoration: none !important;
    color: rgb(26, 44, 68) !important;
    white-space: nowrap;
    padding: 2px 8px;
    border-radius: 6px;
    min-height: 28px;
    height: auto !important;
    font-size: 14px;
    line-height: 20px;
}
#primary-nav .stitch-workload-nav-panel a span,
[data-testid="primary-nav"] .stitch-workload-nav-panel a span {
    width: auto !important;
    max-width: none !important;
    min-width: 0 !important;
    overflow: visible !important;
    flex: 1 1 auto !important;
    --s--flex-x: 1 1 auto !important;
    opacity: 1 !important;
    visibility: visible !important;
    color: inherit !important;
}
#primary-nav .stitch-workload-nav-panel a:hover,
[data-testid="primary-nav"] .stitch-workload-nav-panel a:hover {
    background: rgba(26, 44, 68, 0.06);
}
#primary-nav .stitch-workload-nav-panel a[aria-current="page"],
#primary-nav .stitch-workload-nav-panel a.stitch-nav-active,
[data-testid="primary-nav"] .stitch-workload-nav-panel a[aria-current="page"],
[data-testid="primary-nav"] .stitch-workload-nav-panel a.stitch-nav-active {
    background: rgb(246, 245, 255) !important;
    color: rgb(99, 91, 255) !important;
    font-weight: 500;
}
#primary-nav [data-testid^="toggle-workload-"],
[data-testid="primary-nav"] [data-testid^="toggle-workload-"],
.toggle-workload-button {
    cursor: pointer !important;
    flex: 0 0 auto !important;
    flex-grow: 0 !important;
    width: 100% !important;
    height: 30px !important;
    min-height: 30px !important;
    max-height: 30px !important;
}
#primary-nav [data-testid^="toggle-workload-"] .as-6x,
#primary-nav [data-testid^="toggle-workload-"] .as-20,
[data-testid="primary-nav"] [data-testid^="toggle-workload-"] .as-6x,
[data-testid="primary-nav"] [data-testid^="toggle-workload-"] .as-20,
.toggle-workload-button .as-g.as-6x {
    width: auto !important;
    max-width: none !important;
    overflow: visible !important;
    opacity: 1 !important;
    visibility: visible !important;
}
#primary-nav [data-testid^="toggle-workload-"][aria-expanded="true"],
[data-testid="primary-nav"] [data-testid^="toggle-workload-"][aria-expanded="true"] {
    background: rgba(26, 44, 68, 0.06) !important;
    border-radius: 6px;
}
#primary-nav [data-testid^="toggle-workload-"][aria-expanded="true"] [data-arrow="true"] svg,
[data-testid="primary-nav"] [data-testid^="toggle-workload-"][aria-expanded="true"] [data-arrow="true"] svg {
    transform: rotate(180deg);
}

/* Stripe account switcher dropdown (injected reconciliation fragment). */
.stitch-injected-ui .sn-token-provider[role="menu"],
.stitch-injected-ui [role="menu"].sn-token-provider {
    position: static !important;
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
    width: auto !important;
    transform: none !important;
    pointer-events: none !important;
}
.stitch-injected-ui [data-testid="popover-layer"] {
    height: auto !important;
    max-height: none !important;
    overflow: hidden !important;
    display: block !important;
    pointer-events: auto !important;
    width: 288px !important;
    min-width: 288px !important;
    max-width: 320px !important;
    box-sizing: border-box !important;
    background: #fff !important;
    border: 1px solid rgb(212, 222, 233) !important;
    border-radius: 8px !important;
    box-shadow: rgba(0, 0, 0, 0.12) 0px 5px 15px 0px,
                rgba(48, 49, 61, 0.08) 0px 15px 35px 0px !important;
    padding: 4px 0 8px !important;
}
.stitch-injected-ui [data-testid="account-switcher-workspace"] {
    display: none !important;
}
.stitch-injected-ui [data-testid="popover-layer"] [role="menuitem"],
.stitch-injected-ui [data-testid="popover-layer"] a[role="menuitem"],
.stitch-injected-ui [data-testid="popover-layer"] a[role="button"] {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 36px !important;
    height: auto !important;
    box-sizing: border-box !important;
    position: static !important;
    transform: none !important;
    grid-template-columns: unset !important;
    grid-template-rows: unset !important;
    margin-left: 0 !important;
    padding-left: 12px !important;
    padding-right: 12px !important;
}
.stitch-injected-ui .as-bm,
.stitch-injected-ui [data-testid="exit-legacy-testmode-button"] {
    position: static !important;
    transform: none !important;
    inset: auto !important;
    top: auto !important;
    left: auto !important;
    right: auto !important;
    bottom: auto !important;
    width: calc(100% - 24px) !important;
    max-width: calc(100% - 24px) !important;
    margin: 8px 12px !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    box-sizing: border-box !important;
    border: 1px solid rgb(212, 222, 233) !important;
    border-radius: 6px !important;
    min-height: 36px !important;
    background: #fff !important;
    color: rgb(26, 44, 68) !important;
    text-decoration: none !important;
    overflow: hidden !important;
}
.stitch-injected-ui [data-testid="exit-legacy-testmode-button"]::before,
.stitch-injected-ui [data-testid="exit-legacy-testmode-button"]::after {
    display: none !important;
    content: none !important;
}
.stitch-injected-ui [data-testid="popover-layer"] [role="menuitem"]:hover {
    background: rgba(26, 44, 68, 0.06) !important;
}

/* ── CRM list/table fallbacks (thin captures only) ─────────────────────────── */
[data-test-id="AvatarDisplay-avatarContent"] {
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    max-width: 32px !important;
    max-height: 32px !important;
    border-radius: 50% !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}
.AvatarContent__HiddenSvg-cXPETG,
[class*="AvatarContent__HiddenSvg"] {
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
/* Likwid / Metronic sidebar accordions */
#kt_app_sidebar .menu-item.menu-accordion:not(.show) > .menu-sub {
    display: none !important;
}
#kt_app_sidebar .menu-item.menu-accordion.show > .menu-sub,
#kt_app_sidebar .menu-item.menu-accordion > .menu-sub.show {
    display: flex !important;
    flex-direction: column;
}
#kt_app_sidebar .menu-link,
#kt_app_sidebar [data-kt-menu-trigger],
#kt_app_sidebar [data-stitch-accordion] {
    pointer-events: auto !important;
    cursor: pointer !important;
}
.modal:not(.show) {
    display: none !important;
}"""

FALLBACK_404 = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found — stitched clone</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f172a;
         color: #e2e8f0; display: flex; min-height: 100vh; margin: 0;
         align-items: center; justify-content: center; }
  .card { text-align: center; max-width: 32rem; padding: 2rem; }
  h1 { font-size: 4rem; margin: 0; color: #38bdf8; }
  p { color: #94a3b8; line-height: 1.6; }
  a { color: #38bdf8; }
  code { background: #1e293b; padding: .15rem .4rem; border-radius: .25rem; }
</style>
</head>
<body>
  <div class="card">
    <h1>404</h1>
    <p><strong>Missing stitched page.</strong></p>
    <p>This page was not captured by the crawler, or the link points somewhere
       outside the local clone.</p>
    <p><a href="/">&larr; Back to the entry page</a></p>
  </div>
</body>
</html>
"""


_STITCH_LOGIN_MARKERS = (
    "<title>HubSpot Login",
    'data-application-name="LoginUI"',
    "Your authentication has expired",
    "data-error-type=\"SESSION_TIMED_OUT\"",
)


def _slug_is_login_page(stitched_dir: Path, slug: str) -> bool:
    """Return True if the stitched page.html for *slug* is a login redirect."""
    p = stitched_dir / slug / "page.html"
    if not p.exists():
        return False
    try:
        snippet = p.read_text(encoding="utf-8", errors="ignore")[:3000]
        return any(m in snippet for m in _STITCH_LOGIN_MARKERS)
    except Exception:
        return False


def _resolve_entry(
    navigation: dict,
    valid_slugs: set[str],
    stitched_dir: Path | None = None,
) -> str | None:
    """Pick the entry page: prefer well-known home slugs, then dashboard title, then home.
    Skips any page whose stitched HTML is actually a login/auth-expired page.
    """
    def _ok(slug: str) -> bool:
        if slug.startswith("reports-dashboard"):
            return False
        if stitched_dir and _slug_is_login_page(stitched_dir, slug):
            return False
        return True

    # Check slug hints first — ordered from best to acceptable.
    for hint in _ENTRY_SLUG_HINTS:
        for slug in sorted(navigation):
            if hint in slug.lower() and _ok(slug):
                return slug
    # Fall back to any page whose title contains a dashboard hint.
    for slug, info in sorted(navigation.items()):
        title = (info.get("title", "") or "").lower()
        if not any(h in title for h in _ENTRY_TITLE_HINTS):
            continue
        if slug.endswith("-home") and not slug.endswith("-home-dashboard"):
            continue
        if "gettingstarted" in slug or "recentupdates" in slug:
            continue
        if not _ok(slug):
            continue
        return slug
    for slug in sorted(navigation):
        if _ok(slug):
            return slug
    return next((s for s in sorted(valid_slugs) if _ok(s)), None)


def _write_entry_redirect(stitched_dir: Path, entry_slug: str) -> None:
    target = f"./{entry_slug}/page.html"
    stitched_dir.joinpath("index.html").write_text(
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={target}">'
        f'<script>location.href="{target}";</script>'
        f'</head><body>Redirecting to <a href="{target}">the clone</a>…</body></html>\n',
        encoding="utf-8",
    )


def _norm_class(value) -> str:
    if isinstance(value, (list, tuple)):
        value = " ".join(value)
    return " ".join((value or "").split())


def _norm_route(raw: str) -> str:
    """Normalize an SPA route to a comparable key (drops query, lowercased).

    Handles both hash-route SPAs (Zoho: /app/id#/contacts) and path-based SPAs
    (HubSpot: /contacts/246549280/contacts/list/view/all).
    """
    if not raw:
        return ""
    if "#" in raw:
        # Hash-route SPA: use the fragment as the route key.
        raw = raw.split("#", 1)[1]
    else:
        # Path-based SPA: use the full URL path as the route key.
        raw = urlparse(raw).path
    raw = raw.split("?", 1)[0].strip()
    if not raw:
        return ""
    return "/" + raw.strip("/").lower()


def _route_key_with_query(raw: str, preserve_params: list[str] | None) -> str:
    """Build a normalized route key that keeps configured query params (e.g. ?name=cotton)."""
    if not raw or not preserve_params:
        return ""
    href = raw.strip()
    if href.startswith("/"):
        href = f"http://local{href}"
    parsed = urlparse(href)
    if not parsed.query:
        return ""
    qs = parse_qs(parsed.query, keep_blank_values=True)
    parts: list[str] = []
    for key in preserve_params:
        if key in qs and qs[key]:
            parts.append(f"{key.lower()}={qs[key][0].strip().lower()}")
    if not parts:
        return ""
    path = _norm_route(parsed.path or "/")
    return f"{path}?{'&'.join(parts)}"


def _query_label_slug_index(
    page_dirs: list[Path], valid_slugs: set[str], preserve_params: list[str] | None
) -> dict[str, str]:
    """Map display labels from preserved query params (e.g. name=Cotton) → page slug."""
    if not preserve_params:
        return {}
    label_key = "name" if "name" in preserve_params else preserve_params[0]
    out: dict[str, str] = {}
    for page_dir in page_dirs:
        slug = page_dir.name
        if slug not in valid_slugs:
            continue
        meta = page_dir / "metadata.json"
        if not meta.is_file():
            continue
        try:
            url = json.loads(meta.read_text(encoding="utf-8")).get("url", "")
            qs = parse_qs(urlparse(url).query, keep_blank_values=True)
            if label_key in qs and qs[label_key]:
                out[qs[label_key][0].strip()] = slug
        except Exception:
            continue
    return out


def _resolve_nav_target_slug(
    nav: dict,
    valid_slugs: set[str],
    route_index: dict[str, str],
) -> str | None:
    """Map a navigation record to a crawled page slug.

    Navigations often record target_slug with query params baked in (e.g.
    dashboard_id=defaultdashboard) even when only the base route was captured.
    Fall back to route_index lookup, then longest valid slug prefix."""
    slug = nav.get("target_slug", "")
    if slug and slug in valid_slugs:
        return slug

    target_url = nav.get("target_url", "")
    if target_url:
        for key in (_norm_route(target_url), _norm_route(target_url.split("?")[0])):
            if key and key in route_index:
                resolved = route_index[key]
                if resolved in valid_slugs:
                    return resolved
        fragment = urlparse(target_url).fragment
        if fragment:
            key = _norm_route("#" + fragment.split("?")[0])
            if key and key in route_index:
                resolved = route_index[key]
                if resolved in valid_slugs:
                    return resolved

    if slug:
        prefixes = [s for s in valid_slugs if slug == s or slug.startswith(s + "-")]
        if prefixes:
            return max(prefixes, key=len)

    return None


def _hubspot_extra_route_keys(url: str, slug: str) -> list[str]:
    """Map HubSpot sidebar object routes to crawled list-page URLs.

    The vertical nav links to /objects/0-1 (contacts) and /objects/0-2
    (companies) but crawls often save the longer /contacts/list/view/all paths.
    """
    path = urlparse(url or "").path
    m = re.search(r"/contacts/(\d+)/", path)
    portal = m.group(1) if m else ""
    if not portal:
        m2 = re.search(r"/global-home/(\d+)", path)
        portal = m2.group(1) if m2 else ""
    keys: list[str] = []
    if "contacts-list-view-all" in slug and portal:
        keys += [
            f"/contacts/{portal}/objects/0-1",
            f"/contacts/{portal}/objects/0-1/views/all/list",
        ]
    if "companies-list-view-all" in slug and portal:
        keys += [
            f"/contacts/{portal}/objects/0-2",
            f"/contacts/{portal}/objects/0-2/views/all/list",
        ]
    if "deals-board-view-all" in slug and portal:
        keys += [
            f"/contacts/{portal}/objects/0-3",
            f"/contacts/{portal}/deals/board/view/all",
        ]
    if slug.startswith("global-home") and portal:
        keys.append(f"/global-home/{portal}")
    return [_norm_route(k) for k in keys if k]


# Stripe Products sidebar: panel ids referenced by toggle-workload-* aria-controls.
# Injected at stitch time when crawl snapshots omit collapsed submenu HTML.
_STRIPE_WORKLOAD_NAV: dict[str, list[tuple[str, str]]] = {
    "payments-navigation-links": [
        ("/test/acceptance", "Analytics"),
        ("/test/disputes", "Disputes"),
        ("/test/radar", "Radar"),
        ("/test/payment-links", "Payment Links"),
        ("/test/terminal", "Terminal"),
    ],
    "billing-navigation-links": [
        ("/test/billing", "Overview"),
        ("/test/subscriptions", "Subscriptions"),
        ("/test/invoices", "Invoices"),
        ("/test/revenue-recovery", "Revenue recovery"),
        ("/test/billing/revenue", "Revenue"),
    ],
    "reporting-navigation-links": [
        ("/test/reports", "Reports"),
        ("/test/sigma/queries", "Sigma"),
        ("/test/revenue-recognition", "Revenue Recognition"),
        ("/test/data-management", "Data management"),
        ("/test/reporting", "Overview"),
    ],
    "apps-navigation-links": [
        ("/test/apps/installed", "Installed"),
        ("/test/apps/created", "Created"),
    ],
    "more-navigation-links": [
        ("/test/tax/reporting", "Tax"),
        ("/test/features", "Features"),
        ("/test/sigma/queries", "Sigma"),
        ("/test/sandboxes", "Sandboxes"),
        ("/test/optimization", "Optimization"),
    ],
}

# Minimal submenu markup — avoid as-6s/as-69 Sail classes that pin links to 24px icon width.
_STRIPE_WORKLOAD_SUB_LINK_CLASSES = ["stitch-workload-nav-link"]
_STRIPE_WORKLOAD_SUB_LINK_OUTER_CLASSES = ["stitch-workload-nav-link-outer"]
_STRIPE_WORKLOAD_SUB_LINK_LABEL_CLASSES = ["stitch-workload-nav-link-label"]
_STRIPE_WORKLOAD_PANEL_CLASSES = ["stitch-workload-nav-panel"]


def _make_stripe_workload_nav_link(soup: BeautifulSoup, href: str, label: str):
    """Build a Products submenu row matching Stripe primary-nav link markup."""
    li = soup.new_tag("li", attrs={"class": ["⚙", "as-g"]})
    a = soup.new_tag("a", href=href)
    a["class"] = list(_STRIPE_WORKLOAD_SUB_LINK_CLASSES)
    a["tabindex"] = "1"
    outer = soup.new_tag("span", attrs={"class": list(_STRIPE_WORKLOAD_SUB_LINK_OUTER_CLASSES)})
    label_span = soup.new_tag("span", attrs={"class": list(_STRIPE_WORKLOAD_SUB_LINK_LABEL_CLASSES)})
    label_span.string = label
    outer.append(label_span)
    a.append(outer)
    li.append(a)
    return li


def _resolve_stripe_nav_slug(route: str, route_index: dict[str, str]) -> str | None:
    """Return crawled slug for a Stripe sidebar route pattern, if any."""
    for key in (_norm_route(route), _norm_route(route.split("?")[0])):
        if key and key in route_index:
            return route_index[key]
    norm = _norm_route(route)
    if norm:
        for key, slug in route_index.items():
            if key == norm or key.endswith(norm):
                return slug
    return None


def _inject_stripe_workload_nav_panels(
    soup: BeautifulSoup, route_index: dict[str, str]
) -> int:
    """Create missing Products submenu panels so workload toggles can accordion."""
    if not soup.find(id="dashboardRoot"):
        return 0
    injected = 0
    for toggle in soup.find_all(attrs={"data-testid": re.compile(r"^toggle-workload-")}):
        panel_id = (toggle.get("aria-controls") or "").strip()
        if not panel_id:
            continue
        items = _STRIPE_WORKLOAD_NAV.get(panel_id)
        panel = soup.find(id=panel_id)
        if panel is not None and "stitch-workload-nav-panel" in (panel.get("class") or []):
            if not items:
                continue
            panel.clear()
            panel["class"] = list(_STRIPE_WORKLOAD_PANEL_CLASSES)
            for route, label in items:
                if not _resolve_stripe_nav_slug(route, route_index):
                    continue
                panel.append(_make_stripe_workload_nav_link(soup, route, label))
            injected += 1
            continue
        if panel is None:
            if not items:
                continue
            panel = soup.new_tag("ul", id=panel_id)
            panel["class"] = list(_STRIPE_WORKLOAD_PANEL_CLASSES)
            for route, label in items:
                if not _resolve_stripe_nav_slug(route, route_index):
                    continue
                panel.append(_make_stripe_workload_nav_link(soup, route, label))
            if not panel.contents:
                continue
            host = toggle.find_parent("li") or toggle.parent
            if host is None:
                continue
            host.append(panel)
            injected += 1
            continue
        if not items:
            continue
        existing_routes = {
            _norm_route(a.get("data-stitch-route") or a.get("href") or "")
            for a in panel.find_all("a", href=True)
        }
        for route, label in items:
            if _norm_route(route) in existing_routes:
                continue
            if not _resolve_stripe_nav_slug(route, route_index):
                continue
            panel.append(_make_stripe_workload_nav_link(soup, route, label))
            injected += 1
    return injected


def _collapse_panel(panel) -> None:
    """Hide an accordion panel and clear stitch visibility classes."""
    panel["hidden"] = "true"
    panel["aria-hidden"] = "true"
    classes = panel.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    panel["class"] = [c for c in classes if c != "show"]


def _stripe_slug_matches(page_slug: str, link_slug: str) -> bool:
    """True when two crawled slugs refer to the same Stripe page."""
    if page_slug == link_slug:
        return True
    prefix = "acct-1Tn1qNH9lf8tLTJg-"

    def _short(slug: str) -> str:
        return slug[len(prefix):] if slug.startswith(prefix) else slug

    return _short(page_slug) == _short(link_slug)


def _finalize_stripe_workload_nav(
    soup: BeautifulSoup, page_slug: str | None, route_index: dict[str, str] | None = None
) -> None:
    """Expand only the Products submenu that contains the current page."""
    if not page_slug or not soup.find(id="dashboardRoot"):
        return
    active_panel_id = ""
    for panel in soup.find_all("ul", class_=lambda c: c and "stitch-workload-nav-panel" in c):
        for link in panel.find_all("a", attrs={"data-stitch-page": True}):
            link_slug = link.get("data-stitch-page") or ""
            if _stripe_slug_matches(page_slug, link_slug):
                link["aria-current"] = "page"
                link["class"] = list(dict.fromkeys(
                    (link.get("class") or []) + ["stitch-nav-active"]
                ))
                active_panel_id = panel.get("id") or active_panel_id
    for toggle in soup.find_all(attrs={"data-testid": re.compile(r"^toggle-workload-")}):
        panel_id = (toggle.get("aria-controls") or "").strip()
        panel = soup.find(id=panel_id) if panel_id else None
        if panel is None:
            continue
        expanded = panel_id == active_panel_id
        toggle["aria-expanded"] = "true" if expanded else "false"
        if expanded:
            _show_panel(panel)
        else:
            _collapse_panel(panel)


def _stripe_extra_route_keys(url: str, slug: str) -> list[str]:
    """Map Stripe sidebar routes to crawled page slugs when paths differ."""
    path = urlparse(url or "").path
    keys: list[str] = []
    # Products → Payments sub-nav aliases (acceptance is the real analytics page)
    if "acceptance" in slug or path.endswith("/acceptance"):
        keys += [
            "/test/acceptance",
            "/acceptance",
            "/test/payments/analytics",
            "/payments/analytics",
        ]
    if "disputes" in slug and "payments" not in slug:
        keys += ["/test/disputes", "/disputes"]
    if "payment-links" in slug:
        keys += ["/test/payment-links", "/payment-links"]
    if "terminal" in slug and "settings" not in slug:
        keys += ["/test/terminal", "/terminal"]
    if slug.startswith("test-dashboard") or path.endswith("/dashboard"):
        keys += ["/test/dashboard", "/dashboard"]
    if "test-payments" in slug and "analytics" not in slug and "disputes" not in slug:
        keys += ["/test/payments", "/payments"]
    if "coupons" in slug:
        keys += ["/test/coupons", "/coupons"]
    if "subscriptions" in slug and "create" not in slug and "simulations" not in slug:
        keys += ["/test/subscriptions", "/subscriptions"]
    if "invoices" in slug and "create" not in slug:
        keys += ["/test/invoices", "/invoices"]
    if slug.endswith("test-billing") or path.endswith("/billing"):
        keys += ["/test/billing", "/billing"]
    if "billing-revenue" in slug or path.endswith("/billing/revenue"):
        keys += ["/test/billing/revenue", "/billing/revenue"]
    if "test-reporting" in slug or path.rstrip("/") == "/test/reporting":
        keys += ["/test/reporting", "/reporting"]
    if "test-reports" in slug and "hub" not in slug and "balance" not in slug:
        keys += ["/test/reports", "/reports"]
    if "reports-hub" in slug or path.endswith("/reports/hub"):
        keys += ["/test/reports/hub", "/reports/hub"]
    if "reports-balance" in slug or path.endswith("/reports/balance"):
        keys += ["/test/reports/balance", "/reports/balance"]
    if "reports-reconciliation" in slug or path.endswith("/reports/reconciliation"):
        keys += ["/test/reports/reconciliation", "/reports/reconciliation"]
    if "revenue-recognition" in slug:
        keys += ["/test/revenue-recognition", "/revenue-recognition"]
    if "apps-installed" in slug or path.endswith("/apps/installed"):
        keys += ["/test/apps/installed", "/apps/installed"]
    if "apps-created" in slug or path.endswith("/apps/created"):
        keys += ["/test/apps/created", "/apps/created"]
    if "tax-reporting" in slug or path.endswith("/tax/reporting"):
        keys += ["/test/tax/reporting", "/tax/reporting"]
    if "test-features" in slug or path.endswith("/features"):
        keys += ["/test/features", "/features"]
    if "sigma-queries" in slug or "/sigma/queries" in path:
        keys += ["/test/sigma/queries", "/sigma/queries"]
    if "test-sandboxes" in slug or path.endswith("/sandboxes"):
        keys += ["/test/sandboxes", "/sandboxes"]
    if "test-optimization" in slug or path.endswith("/optimization"):
        keys += ["/test/optimization", "/optimization"]
    return [_norm_route(k) for k in keys if k]


def _build_route_index(
    page_dirs: list[Path],
    sitemap: list[dict],
    valid_slugs: set[str],
    *,
    preserve_query_params: list[str] | None = None,
) -> dict[str, str]:
    """Map normalized route (with and without query) → slug for every crawled
    page. Sourced primarily from each page's own metadata.json url (so the
    index is complete even when the sitemap is missing entries), with sitemap
    urls merged in as aliases."""
    index: dict[str, str] = {}

    def add(url: str, slug: str) -> None:
        if not slug or slug not in valid_slugs:
            return
        parsed = urlparse(url or "")
        keys: set[str] = set()
        if parsed.fragment:
            frag = parsed.fragment.split("?")[0]
            keys.add(_norm_route("#" + frag))
            keys.add(_norm_route(frag))
        if parsed.path:
            keys.add(_norm_route(parsed.path))
            keys.add(_norm_route(url))
        qkey = _route_key_with_query(url, preserve_query_params)
        if qkey:
            keys.add(qkey)
        for alias in _hubspot_extra_route_keys(url, slug):
            keys.add(alias)
        for alias in _stripe_extra_route_keys(url, slug):
            keys.add(alias)
        for key in keys:
            if key:
                index.setdefault(key, slug)

    for page_dir in page_dirs:
        meta = page_dir / "metadata.json"
        if meta.exists():
            try:
                add(json.loads(meta.read_text(encoding="utf-8")).get("url", ""), page_dir.name)
            except Exception:
                pass
    for entry in sitemap:
        add(entry.get("url", ""), entry.get("slug", ""))
    return index


def _resolve_anchor(
    href: str,
    route_index: dict[str, str],
    *,
    preserve_query_params: list[str] | None = None,
) -> str | None:
    """Return the target slug for an anchor href, or None if not a crawled page."""
    if not href:
        return None
    qkey = _route_key_with_query(href, preserve_query_params)
    if qkey and qkey in route_index:
        return route_index[qkey]
    full = _norm_route(href)
    if full in route_index:
        return route_index[full]
    base = _norm_route(href.split("?")[0])
    return route_index.get(base)


def _rewrite_anchors(
    soup: BeautifulSoup,
    route_index: dict[str, str],
    to_root: str,
    *,
    preserve_query_params: list[str] | None = None,
) -> dict[str, str]:
    """Rewrite every <a href> to a local page or neutralize it. Returns the
    slug→relative-path map of resolved page links for the navigation manifest."""
    page_links: dict[str, str] = {}
    for a in soup.find_all("a"):
        if not a.has_attr("href"):
            continue
        href = (a.get("href") or "").strip()
        low = href.lower()
        if low in ("", "#") or low.startswith("#") or low.startswith(_INERT_PREFIXES):
            continue

        slug = _resolve_anchor(href, route_index, preserve_query_params=preserve_query_params)
        if slug:
            rel = f"{to_root}{slug}/page.html"
            a["href"] = rel
            a["data-stitch-page"] = slug
            page_links[slug] = rel
        else:
            # Internal hash route we never crawled, or an absolute production
            # URL — make it inert so navigation never escapes the clone. Keep
            # the original route on the element so the runtime can log it (helps
            # identify uncrawled sidebar routes).
            a["data-stitch-route"] = href
            a["href"] = "#"
            a["data-stitch-unresolved"] = "1"
    return page_links


def _wire_label_sidebar_lists(
    soup: BeautifulSoup,
    label_to_slug: dict[str, str],
    to_root: str,
    used: set[int],
) -> dict[str, str]:
    """Wire sidebar <li> items whose label matches a crawled page (query ?name=… apps)."""
    page_links: dict[str, str] = {}
    if not label_to_slug:
        return page_links
    labels = set(label_to_slug)
    for ul in soup.find_all("ul"):
        matches: list[tuple[Tag, str]] = []
        for li in ul.find_all("li", recursive=False):
            if id(li) in used or li.get("data-stitch-go"):
                continue
            label_el = li.find(["h5", "h4", "span", "a"])
            if not label_el:
                continue
            text = label_el.get_text(strip=True)
            if text in labels:
                matches.append((li, text))
        if len(matches) < 2:
            continue
        for li, text in matches:
            slug = label_to_slug.get(text)
            if not slug:
                continue
            used.add(id(li))
            rel = f"{to_root}{slug}/page.html"
            li["data-stitch-go"] = rel
            li["data-stitch-page"] = slug
            page_links[slug] = rel
    return page_links


def _is_descendant(node, ancestor) -> bool:
    p = node.parent
    while p is not None:
        if p is ancestor:
            return True
        p = p.parent
    return False


def _next_element_sibling(node):
    sib = node.next_sibling
    while sib is not None and not getattr(sib, "name", None):
        sib = sib.next_sibling
    return sib


def _show_panel(panel) -> None:
    """Make a collapsed accordion panel visible: drop `hidden`, add `.show`,
    clear any inline `display:none`."""
    if panel.has_attr("hidden"):
        del panel["hidden"]
    if panel.has_attr("aria-hidden"):
        panel["aria-hidden"] = "false"
    classes = panel.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    classes = list(classes)
    if "show" not in classes:
        classes.append("show")
    panel["class"] = classes
    style = panel.get("style") or ""
    if "display" in style.lower():
        cleaned = re.sub(r"display\s*:\s*none\s*;?", "", style, flags=re.I).strip()
        if cleaned:
            panel["style"] = cleaned
        else:
            del panel["style"]


def _resolve_panel(soup: BeautifulSoup, toggle, is_class_toggle: bool):
    """Find the in-page panel a toggle controls.

    Priority: Metronic `.menu-sub` child → `aria-controls` → element with that id
    (must exist in this page and not be a descendant of the toggle). For class-based
    accordions without a resolvable aria-controls, fall back to the next element sibling.

    Returns None when the controlled content does not exist in the page — that
    is the signal it's a dynamic interaction trigger (dropdown/modal/popover),
    not a sidebar accordion.
    """
    classes = set(_norm_class(toggle.get("class")).split())
    if "menu-accordion" in classes:
        panel = toggle.find(class_=lambda c: c and "menu-sub" in _norm_class(c).split())
        if panel is not None:
            return panel

    ac = toggle.get("aria-controls")
    if ac:
        target = soup.find(id=ac)
        if target is not None:
            if _is_descendant(target, toggle):
                return None
            if target.name in ("table", "tbody", "thead"):
                return None
            if (target.get("role") or "").lower() in ("grid", "table", "tabpanel"):
                return None
            if not is_class_toggle and not toggle.has_attr("aria-expanded"):
                return None
            return target
        # aria-controls present but target absent → dynamic content. Only a
        # class-marked accordion may fall through to sibling resolution.
        if not is_class_toggle:
            return None
    if is_class_toggle:
        sib = _next_element_sibling(toggle)
        if sib is not None and not _is_descendant(sib, toggle):
            return sib
    return None


def _skip_accordion_toggle(el) -> bool:
    """Exclude DataTables pagination, selects, and comboboxes from accordion wiring."""
    name = getattr(el, "name", None) or ""
    if name in ("select", "option", "textarea", "input"):
        return True
    role = (el.get("role") or "").lower()
    if role in ("combobox", "listbox", "option", "gridcell"):
        return True
    classes = set(_norm_class(el.get("class")).split())
    if classes & {"page-link", "select2-selection", "select2-selection__arrow"}:
        return True
    if el.find_parent(class_=lambda c: c and "dt-paging" in _norm_class(c)):
        return True
    if el.find_parent(class_=lambda c: c and "select2" in _norm_class(c)):
        return True
    return False


def _ensure_panel_id(panel, prefix: str = "stitch-acc") -> str:
    pid = (panel.get("id") or "").strip()
    if pid:
        return pid
    pid = f"{prefix}-{id(panel) & 0xFFFFFF:06x}"
    panel["id"] = pid
    return pid


def _wire_accordions(soup: BeautifulSoup, used: set[int], expand_default: bool) -> int:
    """Tag sidebar accordion toggles so the runtime expands/collapses their
    in-page panel. Toggles are added to `used` so interaction wiring never
    rebinds them to a snapshot. One toggle per panel (outermost in document
    order); inner clicks reach it via event bubbling / `closest`.

    Returns the number of accordions wired.
    """
    wired_panels: set[int] = set()
    count = 0
    for el in soup.find_all(True):
        if id(el) in used:
            continue
        if _skip_accordion_toggle(el):
            continue
        classes = set(_norm_class(el.get("class")).split())
        is_class_toggle = bool(classes & _ACCORDION_CLASS_TOKENS)
        has_aria = (
            el.has_attr("aria-expanded")
            and el.has_attr("aria-controls")
            and not _skip_accordion_toggle(el)
        )
        if not (is_class_toggle or has_aria):
            continue
        testid = el.get("data-testid") or ""
        if testid.startswith("toggle-workload-"):
            continue

        panel = _resolve_panel(soup, el, is_class_toggle)
        if panel is None:
            continue  # dynamic interaction trigger or nothing to toggle
        if id(panel) in wired_panels:
            continue  # already covered by an outer toggle for this panel

        wired_panels.add(id(panel))
        panel_id = _ensure_panel_id(panel)
        el["data-stitch-accordion"] = panel_id
        used.add(id(el))
        count += 1

        if "collapsed" in classes:
            el["class"] = [c for c in (el.get("class") or []) if c != "collapsed"]
        if expand_default:
            el["aria-expanded"] = "true"
            if "menu-accordion" in classes:
                el_classes = list(el.get("class") or [])
                if "show" not in el_classes:
                    el_classes.append("show")
                el["class"] = el_classes
            _show_panel(panel)
        elif el.has_attr("aria-expanded"):
            el["aria-expanded"] = "false"
    return count


def _unwire_stripe_workload_accordions(soup: BeautifulSoup) -> None:
    """Products workload headers keep a fixed expand state per page — no accordion toggle."""
    for toggle in soup.find_all(attrs={"data-testid": re.compile(r"^toggle-workload-")}):
        if toggle.has_attr("data-stitch-accordion"):
            del toggle["data-stitch-accordion"]


_OVERSIZED_TRIGGER_IDS = frozenset({
    "dashboardRoot", "merch", "chrome-layout-backdrop", "main-body",
    "backboneModals", "nojsRoot",
})
_OVERSIZED_TRIGGER_TESTIDS = frozenset({
    "world-root", "workbench-root",
})
_OVERSIZED_TRIGGER_CLASS_FRAGMENTS = (
    "db-DashboardRoot",
    "db-World-root",
    "db-World-wrapper",
)


def _is_oversized_interaction_trigger(el) -> bool:
    """True when el is too large to be an interaction trigger (mis-bind breaks nav)."""
    if not getattr(el, "name", None):
        return False
    if (el.get("id") or "") in _OVERSIZED_TRIGGER_IDS:
        return True
    if (el.get("data-testid") or "") in _OVERSIZED_TRIGGER_TESTIDS:
        return True
    cls = " ".join(el.get("class") or [])
    if any(frag in cls for frag in _OVERSIZED_TRIGGER_CLASS_FRAGMENTS):
        return True
    if el.name == "main":
        return True
    if el.find(attrs={"data-testid": re.compile(r"^primary-nav-item-link")}):
        return True
    if el.find(attrs={"data-testid": "world-root"}):
        return True
    if el.find(id="primary-nav"):
        return True
    root = el.find(id="dashboardRoot")
    if root is not None and root is not el:
        return True
    # Heuristic: real triggers are small; wrappers match thousands of nodes.
    if len(list(el.descendants)) > 400:
        return True
    return False


def _prepare_stripe_stitched_dom(soup: BeautifulSoup) -> int:
    """Remove click-blocking Stripe portal shells from stitched pages."""
    if not soup.find(id="dashboardRoot"):
        return 0
    body = soup.body
    if not body:
        return 0
    removed = 0
    for layer in list(body.find_all("div", recursive=False)):
        classes = " ".join(layer.get("class") or [])
        if "__sail-layer-containers" not in classes:
            continue
        if not layer.find(True):
            layer.decompose()
            removed += 1
            continue
        style = layer.get("style") or ""
        if "pointer-events" not in style:
            layer["style"] = (style + "; pointer-events: none").strip("; ")
    chrome = soup.find(id="chrome-layout")
    if chrome is not None:
        style = chrome.get("style") or ""
        if "pointer-events" not in style:
            chrome["style"] = (style + "; pointer-events: auto").strip("; ")
    root = soup.find(id="dashboardRoot")
    if root is not None:
        style = root.get("style") or ""
        if "pointer-events" not in style:
            root["style"] = (style + "; pointer-events: auto").strip("; ")
    for backdrop in soup.find_all(id="chrome-layout-backdrop"):
        backdrop["style"] = ((backdrop.get("style") or "") + "; display: none; pointer-events: none").strip("; ")
    return removed


def _cleanup_oversized_ui_triggers(soup: BeautifulSoup) -> int:
    """Strip data-stitch-ui-id from container nodes that should never be triggers."""
    removed = 0
    for el in soup.find_all(attrs={"data-stitch-ui-id": True}):
        if _is_oversized_interaction_trigger(el):
            del el["data-stitch-ui-id"]
            removed += 1
            continue
        # Empty wrapper divs mis-tagged during attribute scoring.
        text = el.get_text(" ", strip=True)
        if len(text) < 2 and not el.find(["a", "button"]) and not el.find(attrs={"role": "button"}):
            del el["data-stitch-ui-id"]
            removed += 1
    return removed


def _find_trigger(soup: BeautifulSoup, trigger: dict, used: set[int]):
    """Locate the trigger element in the snapshot DOM using stable attributes.

    The saved page.html predates the crawler's data-crawl-id tagging and inner
    ids are regenerated per load, so we score on durable attributes (tag, class,
    aria-label, text, name, role, type) and assign each interaction to the best
    not-yet-used element in document order.
    """
    outer = trigger.get("outer_html") or trigger.get("outerHTML") or ""
    testid = _testid_from_trigger_outer(outer)
    if testid:
        el = soup.find(attrs={"data-testid": testid})
        if el is not None and id(el) not in used and not _is_oversized_interaction_trigger(el):
            return el

    for key in ("crawl_selector", "selector", "css_selector"):
        sel = (trigger.get(key) or "").strip()
        if not sel or sel.startswith("/"):
            continue
        try:
            for el in soup.select(sel):
                if id(el) not in used and not _is_oversized_interaction_trigger(el):
                    return el
        except Exception:
            pass

    tid = (trigger.get("id") or "").strip()
    if tid:
        el = soup.find(id=tid)
        if el is not None and id(el) not in used and not _is_oversized_interaction_trigger(el):
            return el

    tag = (trigger.get("tag_name") or "").lower() or True
    tid = trigger.get("id") or ""
    cls = _norm_class(trigger.get("class_name"))
    aria = trigger.get("aria_label") or ""
    text = (trigger.get("text") or "").strip()
    name = trigger.get("name") or ""
    role = trigger.get("role") or ""
    ttype = ""
    m = re.search(r'type=["\']([^"\']+)["\']', trigger.get("outer_html") or "")
    if m:
        ttype = m.group(1)

    best = None
    best_score = 0
    for el in soup.find_all(tag):
        if id(el) in used:
            continue
        score = 0
        if tid and el.get("id") == tid:
            score += 100
        ecls = _norm_class(el.get("class"))
        if cls:
            if ecls == cls:
                score += 40
            elif ecls and set(ecls.split()) == set(cls.split()):
                score += 35
            elif ecls and set(cls.split()) & set(ecls.split()):
                score += 10
        if aria and el.get("aria-label") == aria:
            score += 25
        if text:
            el_text = el.get_text(" ", strip=True)
            if el_text == text:
                score += 20
            else:
                continue
        if name and el.get("name") == name:
            score += 15
        if role and el.get("role") == role:
            score += 10
        if ttype and el.get("type") == ttype:
            score += 8
        if score > best_score:
            if _is_oversized_interaction_trigger(el):
                continue
            best = el
            best_score = score

    return best if best_score > 0 else None


def _find_trigger_in_container(soup: BeautifulSoup, nav: dict, used: set[int]):
    """Match a trigger inside a list card when container_text / product_title is set."""
    container_text = (
        nav.get("product_title") or nav.get("container_text") or ""
    ).strip()
    label = (nav.get("label") or "").strip()
    if not container_text:
        return None
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if heading.get_text(strip=True) != container_text:
            continue
        card = heading
        for _ in range(8):
            parent = card.parent
            if parent is None or not getattr(parent, "name", None):
                break
            card = parent
            if label:
                for btn in card.find_all(["button", "a"]):
                    if id(btn) in used:
                        continue
                    btn_text = btn.get_text(strip=True)
                    if label.lower() in btn_text.lower():
                        return btn
            else:
                if id(card) not in used:
                    return card
    return None


def _navigation_trigger_from_nav(nav: dict) -> dict:
    """Build a trigger dict for _find_trigger from a navigations.json record."""
    trigger = _normalize_trigger(nav.get("trigger") or {})
    fallback = _normalize_trigger(
        {
            "tag_name": nav.get("tag_name"),
            "text": nav.get("label"),
            "css_selector": nav.get("selector"),
            "class_name": nav.get("class_name"),
        }
    )
    for key, val in fallback.items():
        if val and not trigger.get(key):
            trigger[key] = val
    css = (
        trigger.get("css_selector")
        or nav.get("selector")
        or (nav.get("trigger") or {}).get("css_selector")
        or ""
    )
    if css:
        trigger["css_selector"] = css
    return trigger


def _find_navigation_element(soup: BeautifulSoup, nav: dict, used: set[int]):
    """Resolve a navigation trigger — container disambiguation first, then attributes."""
    el = _find_trigger_in_container(soup, nav, used)
    if el is not None:
        return el
    trigger = _navigation_trigger_from_nav(nav)
    return _find_trigger(soup, trigger, used)


def _wire_navigations(
    soup: BeautifulSoup,
    navigations: list[dict],
    valid_slugs: set[str],
    to_root: str,
    used: set[int],
    route_index: dict[str, str] | None = None,
) -> dict[str, str]:
    """Bind non-anchor navigation triggers (div/li/span/role=menuitem/button)
    discovered during the crawl. Each becomes clickable via data-stitch-go →
    the local target page, so navigation works without an anchor tag."""
    page_links: dict[str, str] = {}
    for nav in navigations:
        slug = _resolve_nav_target_slug(nav, valid_slugs, route_index or {})
        if not slug:
            continue
        trigger = nav.get("trigger", {}) or {}
        # Anchors are already rewritten via href; skip to avoid redundancy.
        if (trigger.get("tag_name") or nav.get("tag_name") or "").lower() == "a":
            continue
        el = _find_navigation_element(soup, nav, used)
        if el is None:
            continue
        if el.get("data-stitch-go"):
            continue
        used.add(id(el))
        rel = f"{to_root}{slug}/page.html"
        el["data-stitch-go"] = rel
        el["data-stitch-page"] = slug
        page_links[slug] = rel
    return page_links


def _parent_slug_for_form(slug: str) -> str | None:
    """Map a creation/new form slug back to its list page slug."""
    if slug.endswith("-new"):
        return slug[:-4]
    if slug.endswith("-product-product-creation"):
        return slug.replace("-product-product-creation", "-product-index")
    return None


_ENTITY_DETAIL_MODULES = (
    "contacts",
    "vendors",
    "quotes",
    "invoices",
    "salesorders",
    "purchaseorders",
    "bills",
    "expenses",
    "creditnotes",
    "vendorcredits",
    "paymentsreceived",
    "paymentsmade",
)


def _parent_slug_for_flyout(slug: str, valid_slugs: set[str]) -> str | None:
    """Map a full-page flyout (new form or entity detail) back to its list page."""
    parent = _parent_slug_for_form(slug)
    if parent and parent in valid_slugs:
        return parent

    # Item detail: .../variantslist/{id}?...
    if re.search(r"inventory-product-variantslist-\d+", slug):
        for vs in valid_slugs:
            if vs.endswith("-inventory-product-index"):
                return vs

    # Entity detail: app-{id}-{module}-{entity_id} (no list filters in slug).
    modules = "|".join(_ENTITY_DETAIL_MODULES)
    m = re.match(rf"^(app-\d+-(?:{modules}))-\d+$", slug)
    if m:
        candidate = m.group(1)
        if candidate in valid_slugs:
            return candidate

    return None


def _wire_flyout_close(
    soup: BeautifulSoup,
    slug: str,
    valid_slugs: set[str],
    to_root: str,
    used: set[int],
) -> None:
    """Wire X / Back / Cancel on full-page flyouts to navigate back to the list page."""
    parent = _parent_slug_for_flyout(slug, valid_slugs)
    if not parent:
        return
    rel = f"{to_root}{parent}/page.html"
    for sel in (
        "button.close-details",
        'button[aria-label="Close this side bar"]',
        'button[aria-label="Back"]',
    ):
        for el in soup.select(sel):
            if id(el) in used:
                continue
            used.add(id(el))
            el["data-stitch-go"] = rel
    for el in soup.find_all("button"):
        if id(el) in used:
            continue
        if (el.get_text() or "").strip() != "Cancel":
            continue
        classes = el.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        if "btn-secondary" in classes or "btn-link" in classes:
            used.add(id(el))
            el["data-stitch-go"] = rel


_SALESFORGE_TAB_SLUGS: dict[str, str] = {
    "senders": "abhiman-kingdom-senders",
    "mailboxes": "abhiman-kingdom-senders-mailboxes",
}


def _wire_salesforge_tabs(
    soup: BeautifulSoup,
    slug: str,
    valid_slugs: set[str],
    to_root: str,
    used: set[int],
) -> None:
    """Wire Senders/Mailboxes tab buttons as local page navigation.

    Salesforge uses React <button role=\"tab\"> elements (not <a href>), so
    sidebar-style anchor rewriting never applies. Each tab maps to a separate
    crawled route: /senders and /senders/mailboxes.
    """
    for tab in soup.select('[role="tab"]'):
        if id(tab) in used:
            continue
        label = (tab.get_text() or "").strip().lower()
        target_slug = _SALESFORGE_TAB_SLUGS.get(label)
        if not target_slug or target_slug not in valid_slugs:
            continue
        used.add(id(tab))
        rel = f"{to_root}{target_slug}/page.html"
        tab["data-stitch-go"] = rel
        tab["data-stitch-page"] = target_slug


def _normalize_trigger(trigger: dict) -> dict:
    """Map a reconciliation-style trigger (camelCase) to the snake_case keys
    `_find_trigger` expects. Pass-through for already snake_case triggers."""
    if not trigger:
        return {}
    return {
        "tag_name": trigger.get("tag_name") or trigger.get("tagName") or "",
        "id": trigger.get("id") or "",
        "class_name": trigger.get("class_name") or trigger.get("className") or "",
        "aria_label": trigger.get("aria_label") or trigger.get("ariaLabel") or "",
        "text": trigger.get("text") or trigger.get("label") or "",
        "name": trigger.get("name") or "",
        "role": trigger.get("role") or "",
        "outer_html": trigger.get("outer_html") or trigger.get("outerHTML") or "",
        "css_selector": trigger.get("css_selector") or trigger.get("selector") or "",
    }


def _rewrite_fragment_anchors(html: str, route_index: dict[str, str], to_root: str) -> str:
    """Localize anchors inside an injected UI fragment so links opened from an
    overlay still navigate within the clone."""
    if not html or "<a" not in html.lower():
        return html
    frag = BeautifulSoup(html, "html.parser")
    _rewrite_anchors(frag, route_index, to_root)
    return str(frag)


def _testid_from_trigger_outer(outer: str) -> str | None:
    """Extract data-testid from a saved trigger outerHTML (Stripe/React)."""
    m = re.search(r'data-testid=(["\'])([^"\']+)\1', outer or "")
    return m.group(2) if m else None


def _sanitize_stripe_dropdown_html(html: str) -> str:
    """Clean Stripe popover fragments before injection into the static clone."""
    if not html or ("role=\"menu\"" not in html and "account-switcher" not in html):
        return html
    frag = BeautifulSoup(html, "html.parser")
    for node in frag.find_all(style=True):
        style = node.get("style") or ""
        if not re.search(r"position\s*:\s*fixed|transform\s*:", style, flags=re.I):
            continue
        cleaned = re.sub(r"position\s*:\s*fixed\s*;?", "", style, flags=re.I)
        cleaned = re.sub(r"transform\s*:\s*[^;]+;?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"(top|left|right|bottom)\s*:\s*[^;]+;?", "", cleaned, flags=re.I)
        cleaned = cleaned.strip(" ;")
        if cleaned:
            node["style"] = cleaned
        else:
            del node["style"]
    for flyout in frag.find_all(attrs={"data-testid": "account-switcher-workspace"}):
        flyout.decompose()
    for item in frag.find_all(attrs={"role": "menuitem"}):
        item["style"] = "transform:none;position:static;width:100%;"
        if item.has_attr("title"):
            del item["title"]
    for btn in frag.find_all(attrs={"data-testid": "exit-legacy-testmode-button"}):
        btn["style"] = "transform:none;position:static;display:flex;width:100%;"
        wrap = btn.find_parent("div", class_=lambda c: c and "as-bm" in " ".join(c if isinstance(c, list) else [c]))
        if wrap is not None:
            wrap["style"] = "position:static;display:block;width:100%;transform:none;"
    for menu in frag.find_all(attrs={"role": "menu"}):
        style = menu.get("style") or ""
        if style:
            cleaned = re.sub(r"max-height\s*:\s*[^;]+;?", "", style, flags=re.I).strip(" ;")
            if cleaned:
                menu["style"] = cleaned
            else:
                del menu["style"]
    return str(frag)


def _interaction_config_from_recon(
    recon: dict,
    *,
    route_index: dict[str, str],
    to_root: str,
    fallback: str,
    itype: str = "",
) -> dict:
    loc = recon.get("location", {}) or {}
    ui_html = recon.get("ui_html", "") or ""
    backdrop_html = recon.get("backdrop_html", "") or ""
    ui_css = recon.get("ui_css", "") or ""
    ui_html = _sanitize_stripe_dropdown_html(ui_html)
    return {
        "type": itype or recon.get("interaction_type", "unknown") or "unknown",
        "parentSelector": loc.get("parentSelector", "") or "",
        "parentXPath": loc.get("parentXPath", "") or "",
        "insertMethod": loc.get("insertMethod", "append") or "append",
        "uiHtml": _rewrite_fragment_anchors(ui_html, route_index, to_root),
        "uiCss": ui_css,
        "backdropHtml": _rewrite_fragment_anchors(backdrop_html, route_index, to_root),
        "fallback": fallback,
    }


def _build_interactions_index(interactions: list[dict]) -> dict[str, dict]:
    """Map [data-crawl-id="N"] selector → interactions.json item.

    Both discovered.json and interactions.json use the same selector format,
    so an exact string match is the reliable JOIN key.
    """
    return {item["selector"]: item for item in interactions if item.get("selector")}


def _build_nav_crawl_index(navigations: list[dict]) -> dict[str, dict]:
    """Map [data-crawl-id="N"] selector → navigations.json item.

    navigations.json stores the crawl-id inside trigger.outer_html rather than
    as a top-level selector, so we extract it with a regex.
    """
    index: dict[str, dict] = {}
    for nav in navigations:
        outer = (nav.get("trigger") or {}).get("outer_html", "")
        m = re.search(r'data-crawl-id=["\'](\d+)["\']', outer)
        if m:
            key = f'[data-crawl-id="{m.group(1)}"]'
            index.setdefault(key, nav)
    return index


def _wire_from_discovered(
    soup: BeautifulSoup,
    page_dir: Path,
    discovered: list[dict],
    inter_idx: dict[str, dict],
    nav_idx: dict[str, dict],
    valid_slugs: set[str],
    to_root: str,
    used: set[int],
    route_index: dict[str, str],
) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """Primary wiring pass driven by discovered.json llm_type classifications.

    For each entry in discovered.json:
      - navigation  → data-stitch-go pointing at the target page
      - interaction → data-stitch-ui-id + __STITCH_INTERACTIONS__ config
      - tab_switch  → data-stitch-tab-id + __STITCH_TABS__ config

    Element matching falls back to attribute scoring (_find_trigger) because
    page.html is saved before DISCOVER_JS stamps data-crawl-id on the live DOM.

    Elements claimed here are added to `used`; subsequent fallback wiring
    functions (_wire_navigations, _wire_tabs, _wire_interactions) skip them.
    """
    inter_manifest: list[dict] = []
    configs: dict[str, dict] = {}
    tabs_configs: dict[str, dict] = {}
    inter_counter = 0
    tab_counter = 0

    for entry in discovered:
        llm_type = entry.get("llm_type", "")
        selector = entry.get("selector", "")

        trigger_dict = {
            "tag_name": entry.get("elementType", ""),
            "id": entry.get("id", ""),
            "class_name": entry.get("className", ""),
            "text": entry.get("label", ""),
        }
        match_trigger = trigger_dict
        if llm_type in ("interaction", "tab_switch"):
            item = inter_idx.get(selector)
            if item:
                rel_path = page_dir / item.get(
                    "relationship_file",
                    f"{item.get('interaction_path', '')}/relationship.json",
                )
                if rel_path.exists():
                    try:
                        rel = json.loads(rel_path.read_text(encoding="utf-8"))
                        rel_trigger = _normalize_trigger(rel.get("trigger", {}) or {})
                        if rel_trigger:
                            match_trigger = rel_trigger
                    except Exception:
                        pass
        el = _find_trigger(soup, match_trigger, used)
        if el is None:
            continue

        if llm_type == "navigation":
            nav = nav_idx.get(selector)
            if not nav:
                continue
            slug = _resolve_nav_target_slug(nav, valid_slugs, route_index)
            if not slug:
                continue
            used.add(id(el))
            rel = f"{to_root}{slug}/page.html"
            el["data-stitch-go"] = rel
            el["data-stitch-page"] = slug

        elif llm_type == "interaction":
            item = inter_idx.get(selector)
            if not item:
                continue
            if _is_oversized_interaction_trigger(el):
                continue
            ipath = item.get("interaction_path", "")
            if not ipath:
                continue
            recon: dict = {}
            recon_path = page_dir / ipath / "reconciliation.json"
            if recon_path.exists():
                try:
                    recon = json.loads(recon_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    recon = {}
            itype = recon.get("interaction_type", "unknown") or "unknown"
            ui_html = recon.get("ui_html", "") or ""
            fallback = f"{ipath}/page.html"
            used.add(id(el))
            inter_counter += 1
            ui_id = f"interaction_{inter_counter}"
            el["data-stitch-ui-id"] = ui_id
            configs[ui_id] = _interaction_config_from_recon(
                recon,
                route_index=route_index,
                to_root=to_root,
                fallback=fallback,
                itype=itype,
            )
            inter_manifest.append({
                "label": entry.get("label", ""),
                "type": itype,
                "path": fallback,
                "ui_id": ui_id,
                "has_ui": bool(ui_html),
                "bound": True,
            })

        elif llm_type == "tab_switch":
            item = inter_idx.get(selector)
            if not item:
                continue
            ipath = item.get("interaction_path", "")
            if not ipath:
                continue
            recon = {}
            recon_path = page_dir / ipath / "reconciliation.json"
            if recon_path.exists():
                try:
                    recon = json.loads(recon_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    recon = {}
            content_html = recon.get("tab_content_html", "") or ""
            content_selector = recon.get("tab_content_selector", "") or ""
            if not content_html or not content_selector:
                continue
            used.add(id(el))
            tab_counter += 1
            tab_id = f"tab_{tab_counter}"
            el["data-stitch-tab-id"] = tab_id
            tabs_configs[tab_id] = {
                "contentSelector": content_selector,
                "contentHtml": content_html,
            }

    return inter_manifest, configs, tabs_configs


def _wire_interactions(
    soup: BeautifulSoup,
    page_dir: Path,
    interactions: list[dict],
    used: set[int],
    route_index: dict[str, str],
    to_root: str,
    counter_start: int = 0,
) -> tuple[list[dict], dict[str, dict]]:
    """Match each interaction trigger and tag it with `data-stitch-ui-id`. Build
    a per-page config map (→ window.__STITCH_INTERACTIONS__) carrying the
    reconciled `ui_html` / `backdrop_html`, insertion location, and a snapshot
    `fallback`. Primary behavior is in-page injection; the snapshot is fallback
    only. Returns (manifest, configs)."""
    manifest: list[dict] = []
    configs: dict[str, dict] = {}
    counter = counter_start

    for item in interactions:
        ipath = item.get("interaction_path", "")
        if not ipath:
            continue
        fallback = f"{ipath}/page.html"

        # Reconciliation drives the primary (injection) behavior.
        recon: dict = {}
        recon_abs = page_dir / ipath / "reconciliation.json"
        if recon_abs.exists():
            try:
                recon = json.loads(recon_abs.read_text(encoding="utf-8")) or {}
            except Exception:
                recon = {}

        itype = recon.get("interaction_type", "") or "unknown"
        loc = recon.get("location", {}) or {}
        ui_html = recon.get("ui_html", "") or ""
        backdrop_html = recon.get("backdrop_html", "") or ""

        # Prefer relationship.json for *matching* (richest trigger metadata);
        # fall back to the reconciliation trigger.
        match_trigger: dict = {}
        rel_abs = page_dir / item.get("relationship_file", f"{ipath}/relationship.json")
        if rel_abs.exists():
            try:
                rel = json.loads(rel_abs.read_text(encoding="utf-8"))
                match_trigger = rel.get("trigger", {}) or {}
                if itype == "unknown":
                    itype = rel.get("interaction_type", itype)
            except Exception:
                match_trigger = {}
        if not match_trigger:
            match_trigger = _normalize_trigger(recon.get("trigger", {}) or {})

        el = _find_trigger(soup, match_trigger, used) if match_trigger else None
        bound = False
        ui_id = ""
        if el is not None:
            used.add(id(el))
            counter += 1
            ui_id = f"interaction_{counter}"
            el["data-stitch-ui-id"] = ui_id
            configs[ui_id] = _interaction_config_from_recon(
                recon,
                route_index=route_index,
                to_root=to_root,
                fallback=fallback,
                itype=itype,
            )
            bound = True

        manifest.append(
            {
                "label": item.get("label", ""),
                "type": itype,
                "path": fallback,
                "ui_id": ui_id,
                "has_ui": bool(ui_html),
                "bound": bound,
            }
        )
    return manifest, configs


def _wire_tabs(
    soup: BeautifulSoup,
    page_dir: Path,
    interactions: list[dict],
    used: set[int],
    counter_start: int = 0,
) -> dict[str, dict]:
    """Match tab-switch triggers and tag them with `data-stitch-tab-id`.

    For each interaction whose relationship.json has ``interaction_type ==
    "tab-switch"`` and a ``tab_content`` block, reads ``tab-content.html``
    and builds an entry in the returned ``tabs_configs`` map.  Matched
    elements are added to *used* so ``_wire_interactions`` skips them.
    """
    tabs_configs: dict[str, dict] = {}
    counter = counter_start
    for item in interactions:
        ipath = item.get("interaction_path", "")
        if not ipath:
            continue
        rel_path = page_dir / item.get("relationship_file", f"{ipath}/relationship.json")
        if not rel_path.exists():
            continue
        try:
            rel = json.loads(rel_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rel.get("interaction_type") != "tab-switch":
            continue
        tab_content = rel.get("tab_content") or {}
        content_selector = tab_content.get("selector", "")
        if not content_selector:
            continue
        content_path = page_dir / ipath / tab_content.get("file", "tab-content.html")
        if not content_path.exists():
            continue
        content_html = content_path.read_text(encoding="utf-8")
        match_trigger = rel.get("trigger", {}) or {}
        el = _find_trigger(soup, match_trigger, used) if match_trigger else None
        if el is None:
            continue
        used.add(id(el))
        counter += 1
        tab_id = f"tab_{counter}"
        el["data-stitch-tab-id"] = tab_id
        tabs_configs[tab_id] = {
            "contentSelector": content_selector,
            "contentHtml": content_html,
        }
    return tabs_configs


def _is_likwid_flows_slug(slug: str) -> bool:
    if slug == "flow-ai-customers-list":
        return True
    if slug.startswith("flow-ai-orders-orders-list"):
        return True
    if slug == "flow-ai-orders-sales-order-create":
        return True
    if slug in ("flow-ai-vendors-add-vendor", "flow-ai-vendors-vendor-list"):
        return True
    if slug == "flow-ai-inventory-stock-list":
        return True
    return False


BROWSER_CONTROL_HELPER_URL = (
    "https://api.insurgeai.com/static/browser-control-helper.js"
)


def _inject_browser_control_helper(soup: BeautifulSoup) -> None:
    head = soup.head or soup.body or soup
    for tag in head.find_all("script", src=True):
        if BROWSER_CONTROL_HELPER_URL in (tag.get("src") or ""):
            return
    head.append(soup.new_tag("script", src=BROWSER_CONTROL_HELPER_URL))


def _inject_runtime(
    soup: BeautifulSoup,
    to_root: str,
    configs: dict[str, dict] | None = None,
    tabs_configs: dict[str, dict] | None = None,
    *,
    slug: str = "",
    likwid_flows: dict | None = None,
) -> None:
    body = soup.body or soup
    if configs:
        # Escape `</` so a literal "</script>" inside ui_html can't terminate the
        # inline script tag. ensure_ascii keeps U+2028/U+2029 etc. safe.
        data = json.dumps(configs, ensure_ascii=True).replace("</", "<\\/")
        cfg_tag = soup.new_tag("script")
        cfg_tag.string = f"window.__STITCH_INTERACTIONS__ = {data};"
        body.append(cfg_tag)
    if tabs_configs:
        data = json.dumps(tabs_configs, ensure_ascii=True).replace("</", "<\\/")
        tab_tag = soup.new_tag("script")
        tab_tag.string = f"window.__STITCH_TABS__ = {data};"
        body.append(tab_tag)
    if likwid_flows and _is_likwid_flows_slug(slug):
        data = json.dumps(likwid_flows, ensure_ascii=True).replace("</", "<\\/")
        flow_tag = soup.new_tag("script")
        flow_tag.string = f"window.__LIKWID_FLOWS__ = {data};"
        body.append(flow_tag)
        body.append(soup.new_tag("script", src=f"{to_root}likwid_flows.js"))
    body.append(soup.new_tag("script", src=f"{to_root}replica_forms.js"))
    body.append(soup.new_tag("script", src=f"{to_root}runtime.js"))


def _neutralize_likwid_post_forms(soup: BeautifulSoup) -> int:
    """Prevent POST form submits in the static clone (server returns 501).

    Likwid uses Django POST forms for lead stages, employee toggles, etc.
    Convert stage submit buttons to type=button so click handlers work.
    """
    fixed = 0
    for form in soup.find_all("form"):
        method = (form.get("method") or "get").lower()
        if method != "post":
            continue
        for btn in form.find_all("button"):
            if "ld-stage" in _norm_class(btn.get("class")):
                btn["type"] = "button"
                fixed += 1
    return fixed


def _strip_cross_origin_iframes(soup: BeautifulSoup) -> int:
    """Replace cross-origin iframes with inert placeholder divs.

    Cross-origin iframes (HubSpot nav widget, chat, analytics frames) never
    load in the static clone and cause hanging network requests that slow page
    display. We remove them from the DOM entirely, leaving a display:none
    placeholder so the removed slot is traceable for debugging.
    """
    removed = 0
    for iframe in soup.find_all("iframe"):
        src = (iframe.get("src") or "").strip()
        if src and not src.startswith(("/", "#", "data:")):
            placeholder = soup.new_tag("div")
            placeholder["class"] = "stitch-iframe-removed"
            placeholder["style"] = "display:none"
            placeholder["data-original-src"] = src
            iframe.replace_with(placeholder)
            removed += 1
    return removed


def _strip_baked_onboarding_ui(soup: BeautifulSoup) -> int:
    """Remove coaching popovers and dismissible banners frozen open during crawl.

  HubSpot marks the page background ``data-floating-ui-inert`` while a popover is
  open. Remove the portal *and* clear inert flags so sidebar navigation works.
  Only applied to main page snapshots — interaction captures keep their open UI.
    """
    removed = 0

    for el in soup.find_all(attrs={"data-floating-ui-inert": True}):
        del el["data-floating-ui-inert"]
    for el in soup.find_all(lambda tag: tag.has_attr("data-floating-ui-inert")):
        del el["data-floating-ui-inert"]

    for portal in list(soup.select("[data-floating-ui-portal]")):
        portal.decompose()
        removed += 1

    for popover in list(soup.select("[data-component-name='UIPopover']")):
        popover.decompose()
        removed += 1

    for highlight in list(soup.select(".private-overlay-highlight")):
        highlight.unwrap()
        removed += 1

    for overlay in list(soup.select(".hDDpEi")):
        parent = overlay.parent
        overlay.decompose()
        removed += 1
        if not isinstance(parent, Tag):
            continue
        for child in list(parent.children):
            if not isinstance(child, Tag):
                continue
            if not any("View__StyledView" in c for c in (child.get("class") or [])):
                continue
            classes = list(child.get("class") or [])
            if "stitch-tour-highlight-reset" not in classes:
                child["class"] = [*classes, "stitch-tour-highlight-reset"]

    seen: set[int] = set()
    for btn in list(soup.find_all("button")):
        if id(btn) in seen:
            continue
        if (btn.get_text(" ", strip=True) or "").strip().lower() != "dismiss":
            continue
        card = btn.find_parent(
            lambda tag: isinstance(tag, Tag)
            and any("CardWrapper" in c or "CardSection" in c for c in (tag.get("class") or []))
        )
        if not card:
            continue
        wrapper = card.find_parent(
            lambda tag: isinstance(tag, Tag)
            and any("CardWrapper" in c for c in (tag.get("class") or []))
        ) or card
        wid = id(wrapper)
        if wid in seen:
            continue
        wrapper.decompose()
        seen.add(wid)
        removed += 1

    return removed


def _neutralize_disabled_state(soup: BeautifulSoup) -> tuple[int, int]:
    """Undo temporary disabled/loading state captured during the crawl so the
    offline clone stays interactive. Runs across the whole document:

      * strip `pointer-events:none` / `user-select:none` from inline styles
      * drop `disabled` + `aria-disabled="true"` from interactive controls
      * inject a CSS override keeping nav containers clickable

    Returns (pointer_events_none_removed, disabled_controls_restored).
    """
    pe_removed = 0
    for el in soup.find_all(style=True):
        style = el.get("style") or ""
        hits = len(_POINTER_EVENTS_NONE_RE.findall(style))
        if not hits and not _USER_SELECT_NONE_RE.search(style):
            continue
        pe_removed += hits
        cleaned = _USER_SELECT_NONE_RE.sub("", _POINTER_EVENTS_NONE_RE.sub("", style))
        cleaned = cleaned.strip().strip(";").strip()
        if cleaned:
            el["style"] = cleaned
        else:
            del el["style"]

    controls_restored = 0
    for el in soup.find_all(_INTERACTIVE_TAGS):
        changed = False
        if el.has_attr("disabled"):
            del el["disabled"]
            changed = True
        if (el.get("aria-disabled") or "").lower() == "true":
            del el["aria-disabled"]
            changed = True
        if changed:
            controls_restored += 1

    style_tag = soup.new_tag("style", id="stitch-interaction-fixes")
    style_tag.string = _INTERACTION_FIX_CSS
    (soup.head or soup.body or soup).append(style_tag)

    return pe_removed, controls_restored


def _fix_svg_viewbox_html(html: str) -> str:
    """Restore SVG viewBox casing after BeautifulSoup serialization.

    BeautifulSoup's html.parser lowercases all attribute names on output, turning
    viewBox="0 0 32 32" into viewbox="0 0 32 32". Browsers treat viewbox as an
    unknown attribute and fall back to a default viewport, causing icons to render
    at their raw path-coordinate size (often thousands of pixels). A simple
    string-level substitution restores the correct camelCase form.
    """
    return re.sub(r"\bviewbox=", "viewBox=", html, flags=re.IGNORECASE)


def _process_html(
    html: str,
    *,
    to_root: str,
    route_index: dict[str, str],
    valid_slugs: set[str] | None = None,
    page_dir: Path | None = None,
    interactions: list[dict] | None = None,
    navigations: list[dict] | None = None,
    discovered: list[dict] | None = None,
    expand_sidebars: bool = True,
    likwid_flows: dict | None = None,
    app_name: str = "",
    preserve_query_params: list[str] | None = None,
    label_to_slug: dict[str, str] | None = None,
) -> tuple[str, dict[str, str], list[dict], int, tuple[int, int]]:
    soup = BeautifulSoup(html, "html.parser")
    stripe_panels = _inject_stripe_workload_nav_panels(soup, route_index)
    page_links = _rewrite_anchors(
        soup, route_index, to_root, preserve_query_params=preserve_query_params
    )
    used: set[int] = set()
    # Accordions first: claim sidebar toggles so interaction wiring never
    # rebinds them to a snapshot, and rewritten submenu anchors stay reachable.
    accordions = _wire_accordions(soup, used, expand_sidebars)
    _unwire_stripe_workload_accordions(soup)
    _finalize_stripe_workload_nav(
        soup, page_dir.name if page_dir is not None else None, route_index
    )

    if valid_slugs is not None and page_dir is not None:
        _wire_flyout_close(soup, page_dir.name, valid_slugs, to_root, used)
        if app_name == "salesforge":
            _wire_salesforge_tabs(soup, page_dir.name, valid_slugs, to_root, used)

    inter_manifest: list[dict] = []
    configs: dict[str, dict] = {}
    tabs_configs: dict[str, dict] = {}

    # Primary wiring: discovered.json drives element tagging using llm_type.
    # Elements claimed here are added to `used`; fallback passes skip them.
    if discovered and page_dir is not None and valid_slugs is not None:
        inter_idx = _build_interactions_index(interactions or [])
        nav_idx = _build_nav_crawl_index(navigations or [])
        d_manifest, d_configs, d_tabs = _wire_from_discovered(
            soup, page_dir, discovered, inter_idx, nav_idx,
            valid_slugs, to_root, used, route_index,
        )
        inter_manifest.extend(d_manifest)
        configs.update(d_configs)
        tabs_configs.update(d_tabs)

    # Fallback wiring: handles any elements not already claimed above.
    if navigations and valid_slugs is not None:
        page_links.update(
            _wire_navigations(soup, navigations, valid_slugs, to_root, used, route_index)
        )
    if label_to_slug:
        page_links.update(
            _wire_label_sidebar_lists(soup, label_to_slug, to_root, used)
        )
    if interactions and page_dir is not None:
        # Wire tabs first (fallback): claims remaining tab-switch triggers.
        tabs_configs.update(
            _wire_tabs(soup, page_dir, interactions, used, counter_start=len(tabs_configs))
        )
        fb_manifest, fb_configs = _wire_interactions(
            soup, page_dir, interactions, used, route_index, to_root,
            counter_start=len(configs),
        )
        inter_manifest.extend(fb_manifest)
        configs.update(fb_configs)

    # Remove cross-origin iframes before final neutralization pass.
    _strip_cross_origin_iframes(soup)
    # Main pages only: drop coaching popovers / banners captured in open state.
    if page_dir is not None:
        _strip_baked_onboarding_ui(soup)
    ui_cleaned = _cleanup_oversized_ui_triggers(soup)
    if ui_cleaned:
        print(f"[STITCH] Removed oversized ui-id from {ui_cleaned} element(s) on {page_dir.name if page_dir else '?'}")
    # Final pass: undo any temporary disabled/loading state before writing.
    fixes = _neutralize_disabled_state(soup)
    stripe_layers = _prepare_stripe_stitched_dom(soup)
    if stripe_layers:
        print(f"[STITCH] Removed {stripe_layers} empty sail-layer shell(s) on {page_dir.name if page_dir else '?'}")
    likwid_forms = _neutralize_likwid_post_forms(soup)
    if likwid_forms:
        print(f"[STITCH] Neutralized {likwid_forms} Likwid POST stage button(s) on {page_dir.name if page_dir else '?'}")
    if app_name == "likwid":
        _inject_browser_control_helper(soup)
    if (
        _is_raasta_app(app_name)
        and page_dir is not None
        and page_dir.name in _RAASTA_MAP_PAGES
        and page_has_maplibre(html)
    ):
        slug = page_dir.name
        map_states = _raasta_stitch_map_states(slug, page_dir, html)
        if _inject_raasta_maps(soup, to_root, slug, map_states):
            print(
                f"[STITCH] Rastaa map enabled ({len(map_states)} map(s)) on {slug}"
            )
    if _is_raasta_app(app_name) and page_dir is not None and page_dir.name == "dashboard":
        _unwire_raasta_weather_interaction(soup, configs)
        _inject_raasta_ui(soup, to_root, "dashboard")
        print("[STITCH] Rastaa dashboard UI enabled (Trips flyout + weather filters)")
    if _is_raasta_app(app_name) and page_dir is not None:
        if page_dir.name == "riders":
            _inject_raasta_riders_page(soup, configs, page_dir)
            print("[STITCH] Rastaa riders UI enabled (Add Driver modal + localStorage)")
        elif page_dir.name == "003-add-driver" and page_dir.parent.name == "interactions":
            _tag_raasta_riders_interaction_page(soup)
    _inject_runtime(
        soup,
        to_root,
        configs,
        tabs_configs,
        slug=page_dir.name if page_dir is not None else "",
        likwid_flows=likwid_flows,
    )
    return _fix_svg_viewbox_html(str(soup)), page_links, inter_manifest, accordions, fixes


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _rebuild_interactions_registry(page_dir: Path) -> list[dict]:
    """Rebuild interactions.json from per-interaction relationship.json files.

    Crawl passes can crash after saving captures but before writing the registry;
    stitching still needs the join keys for discovered.json wiring.
    """
    interactions_dir = page_dir / "interactions"
    if not interactions_dir.is_dir():
        return []
    registry: list[dict] = []
    for sub in sorted(interactions_dir.iterdir()):
        if not sub.is_dir() or not (sub / "relationship.json").is_file():
            continue
        try:
            rel = json.loads((sub / "relationship.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        trigger = rel.get("trigger", {}) or {}
        selector = (
            trigger.get("crawl_selector")
            or trigger.get("selector")
            or ""
        ).strip()
        label = (
            rel.get("trigger_label")
            or trigger.get("text")
            or sub.name
        )
        rel_path = f"interactions/{sub.name}"
        registry.append(
            {
                "label": label,
                "selector": selector,
                "interaction_path": rel_path,
                "relationship_file": f"{rel_path}/relationship.json",
            }
        )
    return registry


def _repair_interactions_registry(page_dir: Path) -> None:
    """Persist a merged interactions.json when captures exist but registry is missing."""
    rebuilt = _rebuild_interactions_registry(page_dir)
    if not rebuilt:
        return
    interactions_dir = page_dir / "interactions"
    interactions_dir.mkdir(parents=True, exist_ok=True)
    f = interactions_dir / "interactions.json"
    existing: list[dict] = []
    if f.exists():
        try:
            existing = json.loads(f.read_text(encoding="utf-8")) or []
        except Exception:
            existing = []
    if not existing:
        merged = rebuilt
    else:
        paths = {item.get("interaction_path") for item in existing}
        merged = list(existing)
        for item in rebuilt:
            if item.get("interaction_path") not in paths:
                merged.append(item)
    if len(merged) > len(existing):
        f.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def _load_interactions(page_dir: Path) -> list[dict]:
    _repair_interactions_registry(page_dir)
    f = page_dir / "interactions" / "interactions.json"
    if not f.exists():
        return _rebuild_interactions_registry(page_dir)
    try:
        registry = json.loads(f.read_text(encoding="utf-8")) or []
    except Exception:
        registry = []
    if registry:
        return registry
    return _rebuild_interactions_registry(page_dir)


_FONT_EXTS = {".woff", ".woff2", ".ttf", ".eot", ".otf"}
_FONT_CDN_MARKERS = (
    "static2.hubspot.com",
    "fonts.hubspot.com",
    "fonts.gstatic.com",
    "b.stripecdn.com",
    "stripe.com",
    "salesforge.ai",
)


_CDN_CSS_MARKERS = (
    "static.hsappstatic.net",
    "hubspot.com",
    "b.stripecdn.com",
    "dashboard.stripe.com",
    "likwidai.com",
    "app.salesforge.ai",
    "salesforge.ai",
)

_CDN_IMAGE_MARKERS = (
    "likwidai.com/static/",
    "salesforge.ai/static/",
)

def _maybe_gunzip(data: bytes) -> bytes:
    if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
        return gzip.decompress(data)
    return data


def _write_downloaded_asset(dest: Path, resp) -> None:
    """Save a downloaded asset, decompressing gzip if the CDN returned compressed bytes."""
    raw = resp.read()
    encoding = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in encoding:
        raw = gzip.decompress(raw)
    else:
        raw = _maybe_gunzip(raw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)


def _ensure_plain_asset_file(dest: Path) -> None:
    """Fix assets saved as gzip blobs without Content-Encoding (Likwid CDN does this)."""
    if not dest.is_file():
        return
    data = dest.read_bytes()
    plain = _maybe_gunzip(data)
    if plain is not data:
        dest.write_bytes(plain)


def _urlopen_asset(req: urllib.request.Request, timeout: int = 20):
    """Download CDN assets; fall back to unverified SSL on macOS Python installs."""
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except ssl.SSLError:
        return urllib.request.urlopen(
            req, timeout=timeout, context=ssl._create_unverified_context()
        )


def _fix_escaped_attr_quotes(html: str) -> str:
    r"""Unescape \" inside HTML attribute values produced by JS-serialised link tags.

    HubSpot's JS sometimes injects <link> tags whose attributes are serialised
    with escaped quotes (e.g. href=\"https://...\"). Browsers skip those tags
    entirely. Only rewrite <link> tags — a global replace would corrupt JSON
    embedded in inline <script> blocks (e.g. window.__STITCH_INTERACTIONS__).
    """

    def _fix_link_tag(m: re.Match) -> str:
        return m.group(0).replace('\\"', '"')

    return re.sub(r"<link\b[^>]*>", _fix_link_tag, html, flags=re.IGNORECASE)


def _localize_hubspot_css(
    html: str,
    css_dir: Path,
    to_root: str,
    css_cdn_dirs: dict[str, str] | None = None,
) -> str:
    """Download CDN CSS files and rewrite <link> tags to local paths.

    External CSS from HubSpot / Stripe CDNs can fail from localhost (referrer
    checks, CORP headers, latency). Download once at stitch time and serve locally.
    """
    seen: dict[str, str] = {}

    def _rewrite_link(m: re.Match) -> str:
        tag = m.group(0)
        href_m = re.search(r'\bhref=(["\'])(https?://[^"\']+\.css[^"\']*)\1', tag)
        if not href_m:
            return tag
        url = href_m.group(2)
        if not any(marker in url for marker in _CDN_CSS_MARKERS):
            return tag
        base_url = url.split("?")[0]
        if base_url in seen:
            local_name = seen[base_url]
        else:
            path_part = urlparse(base_url).path
            stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", path_part.lstrip("/"))[:80]
            local_name = stem + ".css"
            dest = css_dir / local_name
            if dest.exists():
                _ensure_plain_asset_file(dest)
            if not dest.exists():
                try:
                    req = urllib.request.Request(
                        base_url,
                        headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"},
                    )
                    with _urlopen_asset(req, timeout=20) as resp:
                        _write_downloaded_asset(dest, resp)
                    print(f"[CSS] Downloaded {local_name}")
                except Exception as exc:
                    print(f"[CSS] Failed {base_url}: {exc}")
                    return tag
            seen[base_url] = local_name
            if css_cdn_dirs is not None:
                css_cdn_dirs[local_name] = base_url.rsplit("/", 1)[0] + "/"

        local_href = f"{to_root}assets/css/{local_name}"
        new_tag = re.sub(r'\bhref=(["\'])[^"\']+\1', f'href="{local_href}"', tag)
        # Remote SRI/crossorigin break once CSS is served locally.
        new_tag = re.sub(r'\s+crossorigin(?:="[^"]*"|=\'[^\']*\'|=\S+)?', "", new_tag)
        new_tag = re.sub(r'\s+integrity="[^"]*"', "", new_tag)
        return new_tag

    # Match any <link> tag that contains a stylesheet rel, regardless of attribute order.
    return re.sub(
        r'<link\b(?=[^>]*\brel=["\']stylesheet["\'])[^>]*(?:/>|>)',
        _rewrite_link,
        html,
        flags=re.IGNORECASE,
    )


def _localize_fonts(html: str, fonts_dir: Path, to_root: str) -> str:
    """Download CDN font files referenced in @font-face rules and rewrite URLs.

    Scans every <style> block for url() calls pointing to remote font files
    (.woff, .woff2, .ttf, .eot, .otf). Each unique font URL is downloaded once
    into `fonts_dir`. The url() reference in the HTML is then replaced with a
    relative path like `{to_root}assets/fonts/<filename>` so the static clone
    serves fonts locally without cross-origin restrictions.
    """
    font_url_re = re.compile(
        r'url\([\'"]?(https?://[^)\'"]+(?:' + "|".join(re.escape(e) for e in _FONT_EXTS) + r')[^)\'"]*)[\'"]?\)',
        re.IGNORECASE,
    )

    seen: dict[str, str] = {}

    def _download_and_remap(m: re.Match) -> str:
        raw_url = m.group(1).split("?")[0]
        if raw_url in seen:
            local_name = seen[raw_url]
        else:
            suffix = Path(urlparse(raw_url).path).suffix.lower() or ".woff2"
            stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(urlparse(raw_url).path).stem)[:48]
            local_name = f"{stem}{suffix}"
            dest = fonts_dir / local_name
            if dest.exists():
                _ensure_plain_asset_file(dest)
            if not dest.exists():
                try:
                    req = urllib.request.Request(
                        raw_url,
                        headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"},
                    )
                    with _urlopen_asset(req, timeout=15) as resp:
                        _write_downloaded_asset(dest, resp)
                    print(f"[FONTS] Downloaded {local_name}")
                except Exception as exc:
                    print(f"[FONTS] Failed {raw_url}: {exc}")
                    return m.group(0)
            seen[raw_url] = local_name

        local_url = f"{to_root}assets/fonts/{local_name}"
        return f"url({local_url})"

    def _fix_style_block(sm: re.Match) -> str:
        block = sm.group(0)
        if not any(marker in block for marker in _FONT_CDN_MARKERS):
            return block
        return font_url_re.sub(_download_and_remap, block)

    return re.sub(
        r"<style\b[^>]*>[\s\S]*?</style>",
        _fix_style_block,
        html,
        flags=re.IGNORECASE,
    )


def _localize_remote_images(html: str, images_dir: Path, to_root: str) -> str:
    """Download remote logo/image URLs and rewrite <img src> to local paths."""
    seen: dict[str, str] = {}

    def _rewrite_img(m: re.Match) -> str:
        tag = m.group(0)
        src_m = re.search(r'\bsrc=(["\'])(https?://[^"\']+)\1', tag, re.IGNORECASE)
        if not src_m:
            return tag
        url = src_m.group(2)
        if not any(marker in url for marker in _CDN_IMAGE_MARKERS):
            return tag
        base_url = url.split("?")[0]
        if base_url in seen:
            local_name = seen[base_url]
        else:
            path_part = urlparse(base_url).path
            stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", path_part.lstrip("/"))[:80]
            suffix = Path(path_part).suffix.lower() or ".png"
            local_name = stem + suffix
            dest = images_dir / local_name
            if dest.exists():
                _ensure_plain_asset_file(dest)
            if not dest.exists():
                try:
                    req = urllib.request.Request(
                        base_url,
                        headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"},
                    )
                    with _urlopen_asset(req, timeout=20) as resp:
                        _write_downloaded_asset(dest, resp)
                    print(f"[IMG] Downloaded {local_name}")
                except Exception as exc:
                    print(f"[IMG] Failed {base_url}: {exc}")
                    return tag
            seen[base_url] = local_name

        local_src = f"{to_root}assets/images/{local_name}"
        return re.sub(r'\bsrc=(["\'])[^"\']+\1', f'src="{local_src}"', tag, count=1)

    return re.sub(r"<img\b[^>]*>", _rewrite_img, html, flags=re.IGNORECASE)


_CSS_REL_FONT_URL = re.compile(
    r'url\((["\']?)(?!data:)(fonts/[^)\'"]+)\1\)',
    re.IGNORECASE,
)


def _localize_css_bundle_fonts(css_dir: Path, css_cdn_dirs: dict[str, str]) -> None:
    """Download icon/web fonts referenced as url(fonts/...) inside localized CSS bundles."""
    for local_name, cdn_dir in css_cdn_dirs.items():
        css_path = css_dir / local_name
        if not css_path.is_file():
            continue
        seen_paths: set[str] = set()
        text = css_path.read_text(encoding="utf-8", errors="ignore")
        for m in _CSS_REL_FONT_URL.finditer(text):
            ref = m.group(2)
            path_only = ref.split("?")[0].split("#")[0]
            if path_only in seen_paths:
                continue
            seen_paths.add(path_only)
            dest = css_dir / path_only
            if dest.exists():
                _ensure_plain_asset_file(dest)
                continue
            remote = cdn_dir + path_only
            try:
                req = urllib.request.Request(
                    remote,
                    headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"},
                )
                with _urlopen_asset(req, timeout=20) as resp:
                    _write_downloaded_asset(dest, resp)
                print(f"[FONTS] Downloaded {path_only}")
            except Exception as exc:
                print(f"[FONTS] Failed {remote}: {exc}")


def stitch_app(app_name: str, expand_sidebars: bool = True) -> dict:
    crawl_dir = get_crawl_dir(app_name)
    if not crawl_dir.is_dir():
        raise FileNotFoundError(f"No crawl output for '{app_name}' at {crawl_dir}")

    sitemap_path = get_sitemap_path(app_name)
    sitemap = json.loads(sitemap_path.read_text(encoding="utf-8")) if sitemap_path.exists() else []
    titles = {e.get("slug", ""): e.get("title", "") for e in sitemap}
    urls = {e.get("slug", ""): e.get("url", "") for e in sitemap}

    page_dirs = [d for d in sorted(crawl_dir.iterdir()) if d.is_dir() and (d / "page.html").exists()]
    valid_slugs = {d.name for d in page_dirs if d.name != "login"}
    stitch_cfg = get_app_config(app_name)
    preserve_query_params = stitch_cfg.get("crawl_preserve_query_params") or []
    route_index = _build_route_index(
        page_dirs, sitemap, valid_slugs, preserve_query_params=preserve_query_params
    )
    label_to_slug = _query_label_slug_index(page_dirs, valid_slugs, preserve_query_params)

    stitched_dir = get_stitched_dir(app_name)
    clean_stitched(app_name)
    stitched_dir.mkdir(parents=True, exist_ok=True)

    (stitched_dir / "runtime.js").write_text(RUNTIME_JS, encoding="utf-8")

    flow_meta = get_metadata_dir(app_name) / "flow_replays.json"
    likwid_flows = None
    if app_name == "likwid" and flow_meta.is_file():
        try:
            likwid_flows = json.loads(flow_meta.read_text(encoding="utf-8"))
        except Exception:
            likwid_flows = None
    flows_js = Path(__file__).resolve().parent / "src" / "runtime" / "likwid_flows.js"
    if likwid_flows and flows_js.is_file():
        (stitched_dir / "likwid_flows.js").write_text(
            flows_js.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print("[STITCH] Likwid flows layer enabled")

    replica_js = Path(__file__).resolve().parent / "src" / "runtime" / "replica_forms.js"
    if replica_js.is_file():
        (stitched_dir / "replica_forms.js").write_text(
            replica_js.read_text(encoding="utf-8"), encoding="utf-8"
        )

    raasta_maps_js = Path(__file__).resolve().parent / "src" / "runtime" / "raasta_maps.js"
    if _is_raasta_app(app_name) and raasta_maps_js.is_file():
        (stitched_dir / "raasta_maps.js").write_text(
            raasta_maps_js.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print("[STITCH] Rastaa MapLibre replay layer enabled")

    raasta_ui_js = Path(__file__).resolve().parent / "src" / "runtime" / "raasta_ui.js"
    if _is_raasta_app(app_name) and raasta_ui_js.is_file():
        (stitched_dir / "raasta_ui.js").write_text(
            raasta_ui_js.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print("[STITCH] Rastaa dashboard UI layer enabled")

    stitched_assets = stitched_dir / "assets"
    app_assets = get_assets_dir(app_name)
    assets_copied = copy_assets_to_stitched(app_assets, stitched_assets)
    if assets_copied:
        print(f"[STITCH] Copied/updated {assets_copied} asset file(s) from crawl")
    stitched_assets.mkdir(parents=True, exist_ok=True)
    if _is_raasta_app(app_name):
        ensure_maplibre_vendor_assets(stitched_assets)
    assets_localized_total = 0

    navigation: dict[str, dict] = {}
    pages_done = 0
    interactions_bound = 0
    interactions_total = 0
    accordions_total = 0
    pointer_events_fixed = 0
    controls_restored = 0

    for page_dir in page_dirs:
        slug = page_dir.name
        out_dir = stitched_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        interactions = _load_interactions(page_dir)
        navigations = _load_json_list(page_dir / "navigations.json")
        discovered = _load_json_list(page_dir / "interactions" / "discovered.json")
        html = _fix_escaped_attr_quotes(
            (page_dir / "page.html").read_text(encoding="utf-8")
        )
        new_html, page_links, inter_manifest, accordions, fixes = _process_html(
            html,
            to_root="../",
            route_index=route_index,
            valid_slugs=valid_slugs,
            page_dir=page_dir,
            interactions=interactions,
            navigations=navigations,
            discovered=discovered,
            expand_sidebars=expand_sidebars,
            likwid_flows=likwid_flows,
            app_name=app_name,
            preserve_query_params=preserve_query_params,
            label_to_slug=label_to_slug,
        )
        new_html = rewire_asset_prefix(new_html, "../assets/")
        new_html, asset_stats = localize_html_assets(
            new_html,
            urls.get(slug, ""),
            stitched_assets,
            "../assets/",
            download_missing=True,
        )
        assets_localized_total += asset_stats.get("rewritten", 0) + asset_stats.get(
            "downloaded", 0
        )
        (out_dir / "page.html").write_text(new_html, encoding="utf-8")
        pages_done += 1
        accordions_total += accordions
        pointer_events_fixed += fixes[0]
        controls_restored += fixes[1]

        # Copy each interaction snapshot whole (do not reconstruct/merge), but
        # still localize its anchors + inject runtime so nothing escapes.
        for item in inter_manifest:
            interactions_total += 1
            if item["bound"]:
                interactions_bound += 1
            src = page_dir / item["path"]
            if not src.exists():
                continue
            dst = out_dir / item["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            ihtml = _fix_escaped_attr_quotes(src.read_text(encoding="utf-8"))
            new_ihtml, _, _, _, ifixes = _process_html(
                ihtml,
                to_root="../../../",
                route_index=route_index,
                valid_slugs=valid_slugs,
                navigations=navigations,
                expand_sidebars=expand_sidebars,
                likwid_flows=likwid_flows,
                app_name=app_name,
                preserve_query_params=preserve_query_params,
                label_to_slug=label_to_slug,
            )
            new_ihtml = rewire_asset_prefix(new_ihtml, "../../../assets/")
            new_ihtml, iasset_stats = localize_html_assets(
                new_ihtml,
                urls.get(slug, ""),
                stitched_assets,
                "../../../assets/",
                download_missing=True,
            )
            assets_localized_total += iasset_stats.get("rewritten", 0) + iasset_stats.get(
                "downloaded", 0
            )
            pointer_events_fixed += ifixes[0]
            controls_restored += ifixes[1]
            dst.write_text(new_ihtml, encoding="utf-8")

        nav_bound = sum(1 for n in navigations if n.get("target_slug") in valid_slugs)
        navigation[slug] = {
            "title": titles.get(slug, ""),
            "url": urls.get(slug, ""),
            "pages": page_links,
            "interactions": [
                {
                    "label": i["label"],
                    "type": i["type"],
                    "ui_id": i.get("ui_id", ""),
                    "has_ui": i.get("has_ui", False),
                    "fallback": i["path"],
                }
                for i in inter_manifest
            ],
        }
        print(
            f"[STITCH] {slug}: {len(page_links)} page links "
            f"({nav_bound} non-anchor), {accordions} accordions, "
            f"{sum(1 for i in inter_manifest if i['bound'])}/{len(inter_manifest)} interactions wired"
        )

    (stitched_dir / "navigation.json").write_text(
        json.dumps(navigation, indent=2), encoding="utf-8"
    )
    (stitched_dir / "404.html").write_text(FALLBACK_404, encoding="utf-8")

    stitch_cfg = get_app_config(app_name)
    entry_override = stitch_cfg.get("stitch_entry_slug")
    entry_slug = (
        entry_override
        if entry_override and entry_override in valid_slugs
        else _resolve_entry(navigation, valid_slugs, stitched_dir=stitched_dir)
    )
    if entry_slug:
        _write_entry_redirect(stitched_dir, entry_slug)
        print(f"[STITCH] Entry page: {entry_slug}")

    finalize_asset_tree(stitched_assets)

    print(
        f"[STITCH] Interaction fixes: {pointer_events_fixed} pointer-events:none removed, "
        f"{controls_restored} disabled controls restored, "
        f"{assets_localized_total} asset URL(s) localized"
    )
    print(f"[STITCH] Output: {stitched_dir.resolve()}")
    return {
        "pages": pages_done,
        "interactions_total": interactions_total,
        "interactions_bound": interactions_bound,
        "accordions": accordions_total,
        "pointer_events_fixed": pointer_events_fixed,
        "controls_restored": controls_restored,
        "entry": entry_slug,
        "output": str(stitched_dir),
    }
