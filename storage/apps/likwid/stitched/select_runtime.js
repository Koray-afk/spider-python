(function () {
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
})();