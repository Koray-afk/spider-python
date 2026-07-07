"""MapLibre GL capture (crawl) and replay (stitch) for static clones."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

_MAP_STATE_NAME = "map_state.json"
_MAPLIBRE_VERSION = "4.7.1"
_MAPLIBRE_JS_URL = (
    f"https://cdn.jsdelivr.net/npm/maplibre-gl@{_MAPLIBRE_VERSION}/dist/maplibre-gl.js"
)
_MAPLIBRE_CSS_URL = (
    f"https://cdn.jsdelivr.net/npm/maplibre-gl@{_MAPLIBRE_VERSION}/dist/maplibre-gl.css"
)
_DEFAULT_STYLE = "https://demotiles.maplibre.org/style.json"
_PUNE_CENTER = [73.8567, 18.5204]
WAIT_FOR_MAPLIBRE_JS = """
() => new Promise((resolve) => {
  const deadline = Date.now() + 25000;
  function ready() {
    const maps = document.querySelectorAll('.maplibregl-map');
    if (!maps.length) return false;
    for (const mapEl of maps) {
      const canvas = mapEl.querySelector('canvas.maplibregl-canvas');
      if (canvas && canvas.width >= 200 && canvas.height >= 200) return true;
      if (mapEl.classList.contains('maplibregl-loaded')) return true;
    }
    return false;
  }
  function tick() {
    if (ready()) {
      resolve(true);
      return;
    }
    if (Date.now() > deadline) {
      resolve(false);
      return;
    }
    setTimeout(tick, 400);
  }
  tick();
})
"""

EXTRACT_MAPLIBRE_JS = """
() => {
  function findMapForContainer(container) {
    if (!container) return null;
    const nodes = [container, container.querySelector('.maplibregl-canvas-container')];
    for (const node of nodes) {
      if (!node) continue;
      for (const key of Object.keys(node)) {
        const value = node[key];
        if (value && typeof value.getCenter === 'function' && typeof value.getZoom === 'function') {
          return value;
        }
      }
    }
    return null;
  }

  function cloneJson(value) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (e) {
      return null;
    }
  }

  function collectGeoJson(style) {
    const out = [];
    if (!style || !style.sources) return out;
    for (const [sourceId, source] of Object.entries(style.sources)) {
      if (!source || source.type !== 'geojson' || !source.data) continue;
      const data = cloneJson(source.data);
      if (data) out.push({ sourceId, data });
    }
    return out;
  }

  function serializeMap(map) {
    if (!map) return null;
    const center = map.getCenter();
    const style = typeof map.getStyle === 'function' ? map.getStyle() : null;
    const styleClone = cloneJson(style);
    let styleUrl = 'https://demotiles.maplibre.org/style.json';
    try {
      if (map._originalStyleUrl) styleUrl = map._originalStyleUrl;
    } catch (e) {}

    return {
      center: [center.lng, center.lat],
      zoom: map.getZoom(),
      bearing: typeof map.getBearing === 'function' ? map.getBearing() : 0,
      pitch: typeof map.getPitch === 'function' ? map.getPitch() : 0,
      styleUrl,
      style: styleClone,
      geojsonSources: collectGeoJson(styleClone),
    };
  }

  const containers = Array.from(document.querySelectorAll('.maplibregl-map'));
  if (!containers.length) return [];

  const serialized = [];
  for (const container of containers) {
    const map = findMapForContainer(container);
    const item = serializeMap(map);
    if (item) serialized.push(item);
  }

  if (!serialized.length && containers.length) {
    return containers.map(() => ({
      center: [73.8567, 18.5204],
      zoom: 11,
      bearing: 0,
      pitch: 0,
      styleUrl: 'https://demotiles.maplibre.org/style.json',
      style: null,
      geojsonSources: [],
    }));
  }
  return serialized;
}
"""


def uses_maplibre_capture(page_url: str) -> bool:
    return "rastaa.ai" in (page_url or "").lower()


def wait_for_maplibre(page) -> bool:
    try:
        return bool(page.evaluate(WAIT_FOR_MAPLIBRE_JS))
    except Exception as exc:
        print(f"[MAP] Wait skipped: {exc}")
        return False


def capture_maplibre_states(page) -> list[dict]:
    try:
        raw = page.evaluate(EXTRACT_MAPLIBRE_JS) or []
        return raw if isinstance(raw, list) else []
    except Exception as exc:
        print(f"[MAP] Capture failed: {exc}")
        return []


def save_map_state(page_dir: Path, states: list[dict]) -> None:
    if not states:
        return
    (page_dir / _MAP_STATE_NAME).write_text(json.dumps(states, indent=2), encoding="utf-8")


def load_map_state(page_dir: Path | None) -> list[dict]:
    if page_dir is None:
        return []
    path = page_dir / _MAP_STATE_NAME
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def page_has_maplibre(html: str) -> bool:
    return "maplibregl-map" in (html or "")


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def ensure_maplibre_vendor_assets(assets_dir: Path) -> tuple[str, str]:
    """Download MapLibre GL JS/CSS into assets/vendor/maplibre. Returns url prefixes."""
    vendor = assets_dir / "vendor" / "maplibre"
    js_path = vendor / "maplibre-gl.js"
    css_path = vendor / "maplibre-gl.css"
    if not js_path.is_file():
        print("[MAP] Downloading maplibre-gl.js")
        _download_file(_MAPLIBRE_JS_URL, js_path)
    if not css_path.is_file():
        print("[MAP] Downloading maplibre-gl.css")
        _download_file(_MAPLIBRE_CSS_URL, css_path)
    return "vendor/maplibre/maplibre-gl.js", "vendor/maplibre/maplibre-gl.css"
