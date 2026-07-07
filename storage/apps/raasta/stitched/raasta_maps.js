// Rastaa stitched clone — fast MapLibre bootstrap (inline style, no style.json fetch).
(function () {
  "use strict";

  function markMapPanels() {
    document.querySelectorAll(".maplibregl-map").forEach(function (mapEl) {
      var panel = mapEl.closest(".absolute.inset-0");
      if (panel) panel.classList.add("raasta-map-panel");
    });
  }

  function resetContainer(container) {
    container.innerHTML = "";
    container.classList.remove("maplibregl-loaded");
    container.style.position = container.style.position || "relative";
    container.style.width = "100%";
    container.style.height = "100%";
    container.style.minHeight = "320px";
    return container;
  }

  function addGeoJson(map, items) {
    if (!items || !items.length) return;
    items.forEach(function (item) {
      if (!item || !item.sourceId || !item.data) return;
      try {
        if (map.getSource(item.sourceId)) return;
        map.addSource(item.sourceId, { type: "geojson", data: item.data });
        map.addLayer({
          id: item.sourceId + "-circle",
          type: "circle",
          source: item.sourceId,
          paint: {
            "circle-radius": 14,
            "circle-color": "#3b82f6",
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
          },
        });
        map.addLayer({
          id: item.sourceId + "-label",
          type: "symbol",
          source: item.sourceId,
          layout: {
            "text-field": ["to-string", ["get", "id"]],
            "text-size": 11,
            "text-anchor": "center",
          },
          paint: { "text-color": "#ffffff" },
        });
      } catch (e) {}
    });
  }

  function initMap(container, config) {
    var style = config.style;
    if (!style || !style.version) return null;

    var map = new maplibregl.Map({
      container: container,
      style: style,
      center: config.center || [73.8567, 18.5204],
      zoom: typeof config.zoom === "number" ? config.zoom : 11,
      bearing: config.bearing || 0,
      pitch: config.pitch || 0,
      attributionControl: false,
      fadeDuration: 0,
      refreshExpiredTiles: false,
    });

    map.once("load", function () {
      addGeoJson(map, config.geojsonSources);
      try {
        map.resize();
      } catch (e) {}
      container.classList.add("maplibregl-loaded");
    });

    return map;
  }

  function boot() {
    if (typeof maplibregl === "undefined") return;
    var configs = window.__RASTAA_MAPS__;
    if (!configs || !configs.length) return;

    markMapPanels();
    var containers = document.querySelectorAll(".maplibregl-map");
    containers.forEach(function (container, index) {
      var config = configs[index] || configs[0];
      if (!config) return;
      try {
        resetContainer(container);
        initMap(container, config);
      } catch (err) {
        console.warn("[RASTAA MAP] init failed", err);
      }
    });
  }

  if (typeof maplibregl !== "undefined") {
    boot();
  } else {
    document.addEventListener("DOMContentLoaded", boot);
  }
})();
