// Stitcher runtime — page navigation, sidebar accordions, and reconciliation
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
      ].join("\n");
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
      ].join("\n");
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

  function configFor(id) {
    var all = window.__STITCH_INTERACTIONS__ || {};
    return all[id] || null;
  }

  function isExternalHref(href) {
    return /^https?:\/\//i.test(href) && href.indexOf(location.origin) !== 0;
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

  function showDemoHint(msg) {}

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
      showDemoHint("Demo mode — create flows are outside the recorded path");
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
    if (/\b(close|btn-close|sidebar-close|modal-close|popover-close-button|close-details)\b/i.test(cls)) {
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
        if (/^https?:\/\//i.test(href) && href.indexOf(location.origin) !== 0) {
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
