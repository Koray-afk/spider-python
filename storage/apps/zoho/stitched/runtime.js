// Stitcher runtime — page navigation, sidebar accordions, and reconciliation
// UI injection. Interaction clicks inject the reconciled UI into the CURRENT
// page (no reload); the captured snapshot page is used only as a fallback.
(function () {
  "use strict";

  var CLOSE_SELECTOR =
    ".close, .sidebar-close, .modal-close, [data-dismiss], [data-bs-dismiss]," +
    " [aria-label*='close' i], [class*='backdrop'], [class*='overlay-mask']";

  function configFor(id) {
    var all = window.__STITCH_INTERACTIONS__ || {};
    return all[id] || null;
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

  function removeUI(container) {
    if (!container) return;
    if (container.__stitchOutside)
      document.removeEventListener("click", container.__stitchOutside, true);
    if (container.__stitchKey)
      document.removeEventListener("keydown", container.__stitchKey, true);
    if (container.parentNode) container.parentNode.removeChild(container);
  }

  function bindClose(container, trigger) {
    // Explicit close affordances inside the injected UI.
    container.querySelectorAll(CLOSE_SELECTOR).forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        removeUI(container);
      });
    });
    // Click anywhere outside the injected UI (and not on the trigger) closes it.
    function outside(ev) {
      if (
        !container.contains(ev.target) &&
        ev.target !== trigger &&
        !(trigger && trigger.contains && trigger.contains(ev.target))
      ) {
        removeUI(container);
      }
    }
    container.__stitchOutside = outside;
    // Defer so the click that opened the UI doesn't immediately close it.
    setTimeout(function () {
      document.addEventListener("click", outside, true);
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
      if (!parent) throw new Error("parentSelector not found: " + cfg.parentSelector);

      var container = document.createElement("div");
      container.className = "stitch-injected-ui";
      container.setAttribute("data-stitch-ui-id", id);
      container.setAttribute("data-stitch-type", cfg.type || "");
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
      console.log("[STITCH] Inject UI", id, "type=" + (cfg.type || "?"), "→", cfg.parentSelector);
    } catch (err) {
      console.warn("[STITCH] UI injection failed → snapshot fallback", id, err);
      if (fallback) window.location.href = fallback;
    }
  }

  document.addEventListener(
    "click",
    function (e) {
      var t = e.target;
      if (!t || !t.closest) return;

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
      if (uiTrigger) {
        e.preventDefault();
        e.stopPropagation();
        injectInteraction(uiTrigger);
        return;
      }

      // 3. Non-anchor page navigation discovered during crawl.
      var goTrigger = t.closest("[data-stitch-go]");
      if (goTrigger) {
        e.preventDefault();
        e.stopPropagation();
        window.location.href = goTrigger.getAttribute("data-stitch-go");
        return;
      }

      // 4. Page navigation: local rewritten anchors work natively. Block any
      //    leftover production/external link so nothing escapes the clone.
      var a = t.closest("a[href]");
      if (a) {
        var href = a.getAttribute("href") || "";
        if (a.hasAttribute("data-stitch-unresolved")) {
          console.log("[STITCH] Sidebar Link (unresolved route)", a.getAttribute("data-stitch-route") || "#");
        } else if (a.hasAttribute("data-stitch-page")) {
          console.log("[STITCH] Sidebar Link", href);
        }
        if (/^https?:\/\//i.test(href) && href.indexOf(location.origin) !== 0) {
          e.preventDefault();
        }
      }
    },
    true
  );
})();
