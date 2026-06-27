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

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from storage.storage_manager import (
    clean_stitched,
    get_crawl_dir,
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

  function configFor(id) {
    var all = window.__STITCH_INTERACTIONS__ || {};
    return all[id] || null;
  }

  function showDemoHint(msg) {
    if (document.getElementById("stitch-demo-hint")) return;
    var el = document.createElement("div");
    el.id = "stitch-demo-hint";
    el.textContent = msg || "Demo mode \u2014 this action is outside the recorded path";
    el.style.cssText = [
      "position:fixed", "bottom:24px", "right:24px", "z-index:99999",
      "background:rgba(30,30,30,0.88)", "color:#fff",
      "padding:10px 18px", "border-radius:8px",
      "font:13px/1.5 system-ui,sans-serif",
      "pointer-events:none", "opacity:0",
      "transition:opacity 0.2s",
    ].join(";");
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.style.opacity = "1"; });
    setTimeout(function () {
      el.style.opacity = "0";
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 250);
    }, 3000);
  }

  function findPanel(toggle) {
    var id = toggle.getAttribute("data-stitch-accordion");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) {
      var ac = toggle.getAttribute("aria-controls");
      if (ac) panel = document.getElementById(ac);
    }
    if (!panel) panel = toggle.nextElementSibling;
    return panel;
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
      window.location.href = goTrigger.getAttribute("data-stitch-go");
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
        if (/^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0) {
          e.preventDefault();
          e.stopPropagation();
          return true;
        }
        e.preventDefault();
        e.stopPropagation();
        window.location.href = href;
        return true;
      }
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
      var t = e.target;
      if (!t || !t.closest) return;

      // Clicks inside an open injected overlay: navigate local links / demo-select items.
      if (handleInjectedUIClick(e, t)) return;

      // 1. Sidebar accordion toggle — purely in-page, never loads a snapshot.
      var acc = t.closest("[data-stitch-accordion]");
      if (acc) {
        e.preventDefault();
        e.stopPropagation();
        var expanded = acc.getAttribute("aria-expanded") === "true";
        acc.setAttribute("aria-expanded", expanded ? "false" : "true");
        if (expanded) acc.classList.add("collapsed");
        else acc.classList.remove("collapsed");
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

      // 2. Interaction → inject reconciled UI into the current page (no reload).
      var uiTrigger = t.closest("[data-stitch-ui-id]");
      if (uiTrigger && !uiTrigger.classList.contains("stitch-injected-ui")) {
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
        window.location.href = goTrigger.getAttribute("data-stitch-go");
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
        !btn.hasAttribute("data-stitch-go") &&
        !btn.hasAttribute("data-stitch-tab-id") &&
        !btn.hasAttribute("data-stitch-accordion")
      ) {
        showDemoHint();
      }
    },
    true
  );
})();
"""

_INERT_PREFIXES = ("javascript:", "mailto:", "tel:", "data:", "blob:")

_ENTRY_TITLE_HINTS = ("dashboard",)
_ENTRY_SLUG_HINTS = (
    "contacts-list-view-all",  # HubSpot — contacts list is the best landing page
    "global-home",             # HubSpot — home overview
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
        f'<script>location.replace("{target}");</script>'
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


def _build_route_index(
    page_dirs: list[Path], sitemap: list[dict], valid_slugs: set[str]
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
        for alias in _hubspot_extra_route_keys(url, slug):
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


def _resolve_anchor(href: str, route_index: dict[str, str]) -> str | None:
    """Return the target slug for an anchor href, or None if not a crawled page."""
    if not href:
        return None
    full = _norm_route(href)
    if full in route_index:
        return route_index[full]
    base = _norm_route(href.split("?")[0])
    return route_index.get(base)


def _rewrite_anchors(soup: BeautifulSoup, route_index: dict[str, str], to_root: str) -> dict[str, str]:
    """Rewrite every <a href> to a local page or neutralize it. Returns the
    slug→relative-path map of resolved page links for the navigation manifest."""
    page_links: dict[str, str] = {}
    for a in soup.find_all("a"):
        if not a.has_attr("href"):
            continue
        href = (a.get("href") or "").strip()
        low = href.lower()
        if low in ("", "#") or low.startswith(_INERT_PREFIXES):
            continue

        slug = _resolve_anchor(href, route_index)
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

    Priority: `aria-controls` → element with that id (must exist in this page
    and not be a descendant of the toggle). For class-based accordions without
    a resolvable aria-controls, fall back to the next element sibling.

    Returns None when the controlled content does not exist in the page — that
    is the signal it's a dynamic interaction trigger (dropdown/modal/popover),
    not a sidebar accordion.
    """
    ac = toggle.get("aria-controls")
    if ac:
        target = soup.find(id=ac)
        if target is not None and not _is_descendant(target, toggle):
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
        classes = set(_norm_class(el.get("class")).split())
        is_class_toggle = bool(classes & _ACCORDION_CLASS_TOKENS)
        has_aria = el.has_attr("aria-controls") or el.has_attr("aria-expanded")
        if not (is_class_toggle or has_aria):
            continue

        panel = _resolve_panel(soup, el, is_class_toggle)
        if panel is None:
            continue  # dynamic interaction trigger or nothing to toggle
        if id(panel) in wired_panels:
            continue  # already covered by an outer toggle for this panel

        wired_panels.add(id(panel))
        el["data-stitch-accordion"] = panel.get("id") or ""
        used.add(id(el))
        count += 1

        if "collapsed" in classes:
            el["class"] = [c for c in (el.get("class") or []) if c != "collapsed"]
        if expand_default:
            el["aria-expanded"] = "true"
            _show_panel(panel)
        elif el.has_attr("aria-expanded"):
            el["aria-expanded"] = "false"
    return count


def _find_trigger(soup: BeautifulSoup, trigger: dict, used: set[int]):
    """Locate the trigger element in the snapshot DOM using stable attributes.

    The saved page.html predates the crawler's data-crawl-id tagging and inner
    ids are regenerated per load, so we score on durable attributes (tag, class,
    aria-label, text, name, role, type) and assign each interaction to the best
    not-yet-used element in document order.
    """
    for key in ("crawl_selector", "selector", "css_selector"):
        sel = (trigger.get(key) or "").strip()
        if not sel or sel.startswith("/"):
            continue
        try:
            for el in soup.select(sel):
                if id(el) not in used:
                    return el
        except Exception:
            pass

    tid = (trigger.get("id") or "").strip()
    if tid:
        el = soup.find(id=tid)
        if el is not None and id(el) not in used:
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
        if text and el.get_text(" ", strip=True) == text:
            score += 20
        if name and el.get("name") == name:
            score += 15
        if role and el.get("role") == role:
            score += 10
        if ttype and el.get("type") == ttype:
            score += 8
        if score > best_score:
            best = el
            best_score = score

    return best if best_score > 0 else None


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
        el = _find_trigger(soup, trigger, used) if trigger else None
        if el is None:
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
    }


def _rewrite_fragment_anchors(html: str, route_index: dict[str, str], to_root: str) -> str:
    """Localize anchors inside an injected UI fragment so links opened from an
    overlay still navigate within the clone."""
    if not html or "<a" not in html.lower():
        return html
    frag = BeautifulSoup(html, "html.parser")
    _rewrite_anchors(frag, route_index, to_root)
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
        el = _find_trigger(soup, trigger_dict, used)
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


def _inject_runtime(
    soup: BeautifulSoup,
    to_root: str,
    configs: dict[str, dict] | None = None,
    tabs_configs: dict[str, dict] | None = None,
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
    body.append(soup.new_tag("script", src=f"{to_root}runtime.js"))


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
) -> tuple[str, dict[str, str], list[dict], int, tuple[int, int]]:
    soup = BeautifulSoup(html, "html.parser")
    page_links = _rewrite_anchors(soup, route_index, to_root)
    used: set[int] = set()
    # Accordions first: claim sidebar toggles so interaction wiring never
    # rebinds them to a snapshot, and rewritten submenu anchors stay reachable.
    accordions = _wire_accordions(soup, used, expand_sidebars)

    if valid_slugs is not None and page_dir is not None:
        _wire_flyout_close(soup, page_dir.name, valid_slugs, to_root, used)

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
    # Final pass: undo any temporary disabled/loading state before writing.
    fixes = _neutralize_disabled_state(soup)
    _inject_runtime(soup, to_root, configs, tabs_configs)
    return _fix_svg_viewbox_html(str(soup)), page_links, inter_manifest, accordions, fixes


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_interactions(page_dir: Path) -> list[dict]:
    f = page_dir / "interactions" / "interactions.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


_FONT_EXTS = {".woff", ".woff2", ".ttf", ".eot", ".otf"}
_FONT_CDN_MARKERS = ("static2.hubspot.com", "fonts.hubspot.com", "fonts.gstatic.com")


_HS_CSS_CDN_MARKERS = ("static.hsappstatic.net", "hubspot.com")


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


def _localize_hubspot_css(html: str, css_dir: Path, to_root: str) -> str:
    """Download HubSpot CDN CSS files and rewrite <link> tags to local paths.

    External CSS files from static.hsappstatic.net load fine in a real browser
    but can silently fail from localhost (referrer checks, CORP headers, or plain
    network latency). Downloading them once at stitch time and serving locally
    ensures the clone renders identically regardless of CDN availability.

    Only stylesheet <link> tags pointing to HubSpot CDNs are rewritten; other
    external links are left unchanged.
    """
    seen: dict[str, str] = {}

    def _rewrite_link(m: re.Match) -> str:
        tag = m.group(0)
        href_m = re.search(r'\bhref=(["\'])(https?://[^"\']+\.css[^"\']*)\1', tag)
        if not href_m:
            return tag
        url = href_m.group(2)
        if not any(marker in url for marker in _HS_CSS_CDN_MARKERS):
            return tag
        base_url = url.split("?")[0]
        if base_url in seen:
            local_name = seen[base_url]
        else:
            path_part = urlparse(base_url).path
            stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", path_part.lstrip("/"))[:80]
            local_name = stem + ".css"
            dest = css_dir / local_name
            if not dest.exists():
                try:
                    req = urllib.request.Request(
                        base_url,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        dest.write_bytes(resp.read())
                    print(f"[CSS] Downloaded {local_name}")
                except Exception as exc:
                    print(f"[CSS] Failed {base_url}: {exc}")
                    return tag
            seen[base_url] = local_name

        local_href = f"{to_root}assets/css/{local_name}"
        new_tag = re.sub(r'\bhref=(["\'])[^"\']+\1', f'href="{local_href}"', tag)
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
            if not dest.exists():
                try:
                    req = urllib.request.Request(
                        raw_url,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        dest.write_bytes(resp.read())
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
    route_index = _build_route_index(page_dirs, sitemap, valid_slugs)

    stitched_dir = get_stitched_dir(app_name)
    clean_stitched(app_name)
    stitched_dir.mkdir(parents=True, exist_ok=True)

    (stitched_dir / "runtime.js").write_text(RUNTIME_JS, encoding="utf-8")

    fonts_dir = stitched_dir / "assets" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    css_dir = stitched_dir / "assets" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)

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
        )
        new_html = _localize_hubspot_css(new_html, css_dir, to_root="../")
        new_html = _localize_fonts(new_html, fonts_dir, to_root="../")
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
            )
            new_ihtml = _localize_hubspot_css(new_ihtml, css_dir, to_root="../../../")
            new_ihtml = _localize_fonts(new_ihtml, fonts_dir, to_root="../../../")
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

    entry_slug = _resolve_entry(navigation, valid_slugs, stitched_dir=stitched_dir)
    if entry_slug:
        _write_entry_redirect(stitched_dir, entry_slug)
        print(f"[STITCH] Entry page: {entry_slug}")

    print(
        f"[STITCH] Interaction fixes: {pointer_events_fixed} pointer-events:none removed, "
        f"{controls_restored} disabled controls restored"
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
