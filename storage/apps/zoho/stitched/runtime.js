// Stitcher runtime — page navigation, sidebar accordions, and reconciliation
// UI injection. Interaction clicks inject the reconciled UI into the CURRENT
// page (no reload); the captured snapshot page is used only as a fallback.
(function () {
  "use strict";

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
    container.style.position = "static";
    container.style.pointerEvents = "none";
    container.style.background = "transparent";
    container.style.border = "0";
    container.style.padding = "0";
    container.style.margin = "0";

    function apply() {
      var panels = container.querySelectorAll(
        ".dropdown-menu, .modal-dialog, .popover, .popover-container, .popper[role='tooltip'], .tooltip, .popper.tooltip"
      );
      Array.prototype.forEach.call(panels, function (panel) {
        if (/backdrop|modal-backdrop|arrow/i.test(panel.className || "")) return;
        panel.style.pointerEvents = "auto";
        if (panel.classList.contains("dropdown-menu") || panel.classList.contains("show")) {
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
        return true;
      }
      if (href && href !== "#" && href.indexOf("javascript:") !== 0) {
        if (/^https?:\/\//i.test(href) && href.indexOf(location.origin) !== 0) {
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
    if (menuItem && (menuItem.tagName === "BUTTON" || menuItem.getAttribute("role") === "button" || menuItem.tagName === "LI")) {
      e.preventDefault();
      e.stopPropagation();
      var scope = menuItem.closest(".dropdown-menu") || menuItem.parentElement;
      if (scope) {
        Array.prototype.forEach.call(
          scope.querySelectorAll(".dropdown-item.selected-option, .dropdown-item.active"),
          function (sib) { sib.classList.remove("selected-option", "active"); }
        );
      }
      menuItem.classList.add("selected-option");
      console.log("[STITCH] Dropdown item (demo selection)", (menuItem.textContent || "").trim().slice(0, 48));
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
      if (fallback) window.location.href = fallback;
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
