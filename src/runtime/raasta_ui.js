// Rastaa dashboard UI runtime (stitched pages — loaded before runtime.js).
(function () {
  "use strict";

  if (document.body.getAttribute("data-raasta-page") !== "dashboard") return;

  function findTripsPanel() {
    var nodes = document.querySelectorAll("div.absolute.top-4.bottom-4");
    for (var i = 0; i < nodes.length; i++) {
      var cls = nodes[i].className || "";
      if (cls.indexOf("w-[380px]") !== -1) return nodes[i];
    }
    return null;
  }

  var panel = findTripsPanel();
  var closeBtn = document.querySelector('button[aria-label="Close trips panel"]');
  var refreshBtn = document.querySelector('button[aria-label="Refresh trips"]');
  var section = panel && panel.closest("section");

  if (!panel || !closeBtn) return;

  var style = document.createElement("style");
  style.id = "raasta-trips-ui";
  style.textContent = [
    "section.raasta-trips-root { overflow: visible !important; }",
    "body.raasta-trips-open .raasta-trips-panel { right: 1rem !important; }",
    "body.raasta-trips-open .raasta-trips-close { right: 380px !important; z-index: 30 !important; }",
    "body.raasta-trips-closed .raasta-trips-panel { right: -400px !important; }",
    "body.raasta-trips-closed .raasta-trips-close { right: 0.5rem !important; z-index: 30 !important; }",
    "body.raasta-trips-closed .raasta-trips-close svg { transform: rotate(180deg); }",
  ].join("\n");
  document.head.appendChild(style);

  if (section) section.classList.add("raasta-trips-root");
  panel.classList.add("raasta-trips-panel");
  closeBtn.classList.add("raasta-trips-close");

  var open = true;

  function setOpen(next) {
    open = next;
    document.body.classList.toggle("raasta-trips-open", open);
    document.body.classList.toggle("raasta-trips-closed", !open);
    closeBtn.setAttribute("aria-label", open ? "Close trips panel" : "Open trips panel");
  }

  closeBtn.addEventListener(
    "click",
    function (e) {
      e.preventDefault();
      e.stopPropagation();
      setOpen(!open);
    },
    true
  );

  if (refreshBtn) {
    refreshBtn.addEventListener(
      "click",
      function (e) {
        e.preventDefault();
        e.stopPropagation();
        refreshBtn.classList.add("opacity-50");
        setTimeout(function () {
          refreshBtn.classList.remove("opacity-50");
        }, 400);
      },
      true
    );
  }

  setOpen(true);
})();
