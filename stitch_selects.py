"""Wire native <select> and Select2 widgets for the static clone runtime.

Stitch-time: tag controls in every page.html (main + interaction snapshots).
Serve-time: select_runtime.js toggles option menus built from <option> elements.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

SELECT_FIX_CSS = """
/* Select2 + native selects — keep clickable in the static clone */
[data-stitch-select-ui],
[data-stitch-select-ui] .select2-selection,
[data-stitch-native-select],
select[data-stitch-native-select] {
    pointer-events: auto !important;
    cursor: pointer !important;
}
[data-stitch-select-ui] {
    position: relative !important;
}
.stitch-select2-dropdown {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 3000;
    max-height: 260px;
    overflow-y: auto;
    margin-top: 2px;
    background: #fff;
    border: 1px solid #e4e6ef;
    border-radius: 0.475rem;
    box-shadow: 0 0 50px 0 rgba(82, 63, 105, 0.15);
}
.stitch-select2-dropdown.show {
    display: block !important;
}
.stitch-select2-dropdown .dropdown-item {
    pointer-events: auto !important;
    cursor: pointer !important;
    white-space: normal;
}
.stitch-select2-dropdown .dropdown-item.active,
.stitch-select2-dropdown .dropdown-item:hover {
    background-color: #f1faff;
}
select[data-stitch-native-select] {
    appearance: auto !important;
    -webkit-appearance: menulist !important;
}
"""

SELECT_RUNTIME_JS = r"""(function () {
  "use strict";

  function closeAll() {
    document.querySelectorAll(".stitch-select2-dropdown.show").forEach(function (m) {
      m.classList.remove("show");
      m.style.display = "none";
    });
    document.querySelectorAll(
      '[data-stitch-select-ui] .select2-selection[aria-expanded="true"]'
    ).forEach(function (s) {
      s.setAttribute("aria-expanded", "false");
    });
  }

  function findSelect(container) {
    var sid = container.getAttribute("data-stitch-select-ui");
    if (!sid) return null;
    return document.querySelector('[data-stitch-select="' + sid + '"]');
  }

  function isMultiple(select) {
    return select.hasAttribute("multiple");
  }

  function updateSingleDisplay(container, text) {
    var rendered = container.querySelector(".select2-selection__rendered");
    if (!rendered) return;
    rendered.textContent = text || "";
    rendered.removeAttribute("title");
    var ph = container.querySelector(".select2-selection__placeholder");
    if (ph) ph.remove();
  }

  function updateMultipleDisplay(container, select) {
    var ul = container.querySelector(".select2-selection__rendered");
    if (!ul) return;
    ul.innerHTML = "";
    var opts = Array.prototype.filter.call(select.options, function (o) {
      return o.selected && o.value;
    });
    if (!opts.length) {
      var ph = document.createElement("li");
      ph.className = "select2-selection__placeholder";
      ph.textContent =
        select.getAttribute("data-placeholder") ||
        select.getAttribute("placeholder") ||
        "Select…";
      ul.appendChild(ph);
      return;
    }
    opts.forEach(function (opt) {
      var li = document.createElement("li");
      li.className = "select2-selection__choice";
      li.title = opt.textContent.trim();
      li.textContent = opt.textContent.trim();
      ul.appendChild(li);
    });
  }

  function syncDisplay(container, select) {
    if (isMultiple(select)) {
      updateMultipleDisplay(container, select);
      return;
    }
    var opt = select.options[select.selectedIndex];
    updateSingleDisplay(container, opt ? opt.textContent.trim() : "");
  }

  function buildMenu(container, select) {
    var existing = container.querySelector(".stitch-select2-dropdown");
    if (existing) return existing;
    var menu = document.createElement("div");
    menu.className = "stitch-select2-dropdown dropdown-menu";
    menu.setAttribute("role", "listbox");

    Array.prototype.forEach.call(select.options, function (opt) {
      var label = (opt.textContent || "").trim();
      if (!label && !opt.value) return;
      var item = document.createElement("button");
      item.type = "button";
      item.className = "dropdown-item";
      item.textContent = label || opt.value;
      item.setAttribute("data-value", opt.value);
      if (opt.selected) item.classList.add("active");
      item.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (isMultiple(select)) {
          opt.selected = !opt.selected;
          item.classList.toggle("active", opt.selected);
          syncDisplay(container, select);
        } else {
          select.value = opt.value;
          Array.prototype.forEach.call(menu.querySelectorAll(".dropdown-item"), function (el) {
            el.classList.remove("active");
          });
          item.classList.add("active");
          syncDisplay(container, select);
          closeAll();
        }
      });
      menu.appendChild(item);
    });

    container.appendChild(menu);
    return menu;
  }

  function toggle(container) {
    var select = findSelect(container);
    if (!select) return;
    var menu = buildMenu(container, select);
    var selection = container.querySelector(".select2-selection");
    var open = menu.classList.contains("show");
    closeAll();
    if (open) return;
    menu.classList.add("show");
    menu.style.display = "block";
    if (selection) selection.setAttribute("aria-expanded", "true");
  }

  function bindContainer(container) {
    if (container.__stitchSelectBound) return;
    container.__stitchSelectBound = true;
    var selection = container.querySelector(".select2-selection");
    if (!selection) return;
    selection.style.cursor = "pointer";
    selection.setAttribute("tabindex", "0");
    selection.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();
      toggle(container);
    });
  }

  function init() {
    document.querySelectorAll("[data-stitch-select-ui]").forEach(bindContainer);
    document.querySelectorAll("select[data-stitch-native-select]").forEach(function (sel) {
      sel.style.pointerEvents = "auto";
      sel.removeAttribute("disabled");
    });
  }

  document.addEventListener(
    "click",
    function (e) {
      var ui = e.target.closest && e.target.closest("[data-stitch-select-ui]");
      if (ui) return;
      if (e.target.closest && e.target.closest(".stitch-select2-dropdown")) return;
      closeAll();
    },
    true
  );

  document.addEventListener(
    "click",
    function (e) {
      if (
        e.target.closest &&
        (e.target.closest("[data-stitch-ui-id]") ||
          e.target.closest("[data-bs-toggle='modal']") ||
          e.target.closest(".modal"))
      ) {
        setTimeout(init, 80);
      }
    },
    true
  );

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.__stitchInitSelects = init;
})();"""


def _class_tokens(el: Tag) -> set[str]:
    c = el.get("class")
    if not c:
        return set()
    return set(c if isinstance(c, list) else str(c).split())


def _is_select2_container(el: Tag) -> bool:
    return "select2-container" in _class_tokens(el)


def _next_select2_container(select_el: Tag) -> Tag | None:
    sib = select_el.next_sibling
    while sib is not None:
        if isinstance(sib, Tag):
            if _is_select2_container(sib):
                return sib
            if sib.name not in ("span", "div"):
                break
        sib = sib.next_sibling
    return None


def wire_select_dropdowns(soup: BeautifulSoup) -> int:
    """Tag select / Select2 pairs so select_runtime.js can drive them."""
    wired = 0
    counter = 0

    for select_el in soup.find_all("select"):
        counter += 1
        sid = f"stitch-select-{counter}"
        select_el["data-stitch-select"] = sid

        ui = _next_select2_container(select_el)
        if ui is not None:
            ui["data-stitch-select-ui"] = sid
            for part in ui.select(".select2-selection"):
                part["tabindex"] = "0"
                if not part.get("role"):
                    part["role"] = "combobox"
                part["aria-expanded"] = "false"
            wired += 1
            continue

        hidden = (select_el.get("aria-hidden") or "").lower() == "true"
        classes = _class_tokens(select_el)
        if hidden or "select2-hidden-accessible" in classes:
            continue

        select_el["data-stitch-native-select"] = "1"
        if select_el.get("tabindex") == "-1":
            del select_el["tabindex"]
        if select_el.has_attr("disabled"):
            del select_el["disabled"]
        wired += 1

    return wired


def inject_select_fix_css(soup: BeautifulSoup) -> None:
    """Append select dropdown CSS to the page (idempotent)."""
    if soup.find("style", id="stitch-select-fixes"):
        return
    style = soup.new_tag("style", id="stitch-select-fixes")
    style.string = SELECT_FIX_CSS
    (soup.head or soup.body or soup).append(style)
