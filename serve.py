import argparse
import json
import mimetypes
import re
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from config import ROOT_DIR, STORAGE_DIR, get_app_config
from mock_api import (
    global_mock_dir,
    load_or_build_registry,
    resolve_mock_file,
)
from urls import normalize_crawl_url

SITE_DIR = ROOT_DIR / "site"

MOCK_BRIDGE_JS = """\
(function () {
  "use strict";

  var origins = window.__MOCK_API_ORIGINS__ || [];
  var pageMocks = window.__PAGE_MOCKS__ || {};
  var routeMap = window.__ROUTE_MAP__ || {};
  var slugRouteMap = window.__SLUG_ROUTE_MAP__ || {};
  var availableSlugs = window.__AVAILABLE_SLUGS__ || [];
  var currentSlug = window.__CURRENT_SLUG__ || "";
  var intendedRoute = window.__INTENDED_ROUTE__ || "";
  var navigating = false;
  var lastHumanClick = 0;
  var HUMAN_MS = 1500;
  var BOOT_LOCK_MS = 15000;
  var bootLockUntil = Date.now() + BOOT_LOCK_MS;

  try {
    var pending = sessionStorage.getItem("offline_pending_slug");
    var pendingAt = parseInt(sessionStorage.getItem("offline_pending_at") || "0", 10);
    if (pending === currentSlug && Date.now() - pendingAt < BOOT_LOCK_MS) {
      bootLockUntil = pendingAt + BOOT_LOCK_MS;
      sessionStorage.removeItem("offline_pending_slug");
      sessionStorage.removeItem("offline_pending_at");
      console.log("[OFFLINE] Boot lock active");
    }
  } catch (err) {}

  function markHuman() {
    lastHumanClick = Date.now();
  }

  function isHuman() {
    return Date.now() - lastHumanClick < HUMAN_MS;
  }

  function isBootLocked() {
    return Date.now() < bootLockUntil;
  }

  function normalizeRoute(value) {
    return String(value || "")
      .replace(/^#\\/?/, "")
      .split("?")[0]
      .replace(/^\\/+|\\/+$/g, "")
      .toLowerCase();
  }

  function ensureRouteHash() {
    if (!intendedRoute) return;
    var desired = "#/" + intendedRoute;
    if (normalizeRoute(location.hash) === normalizeRoute(desired)) return;
    try {
      history.replaceState(null, "", location.pathname + location.search + desired);
    } catch (err) {
      location.replace(location.pathname + location.search + desired);
    }
  }

  ensureRouteHash();
  console.log("[OFFLINE] Slug:", currentSlug, "Route:", intendedRoute);

  document.addEventListener("click", markHuman, true);
  document.addEventListener("mousedown", markHuman, true);

  function rewriteUrl(url) {
    if (!url) return url;
    for (var i = 0; i < origins.length; i++) {
      if (url.indexOf(origins[i]) === 0) return url.slice(origins[i].length);
    }
    return url;
  }

  function lookupLocalPath(method, url) {
    var rewritten = rewriteUrl(url);
    var parsed;
    try {
      parsed = new URL(rewritten, window.location.origin);
    } catch (err) {
      return null;
    }
    var query = parsed.search ? parsed.search.slice(1) : "";
    if (query) query = query.split("&").sort().join("&");
    var exactKey = method.toUpperCase() + " " + parsed.pathname + (query ? "?" + query : "");
    if (pageMocks[exactKey]) return pageMocks[exactKey];
    var pathKey = method.toUpperCase() + " " + parsed.pathname;
    for (var key in pageMocks) {
      if (Object.prototype.hasOwnProperty.call(pageMocks, key) && key.indexOf(pathKey) === 0) {
        return pageMocks[key];
      }
    }
    return null;
  }

  var originalFetch = window.fetch;
  window.fetch = function (input, init) {
    var method = (init && init.method) || "GET";
    var url = typeof input === "string" ? input : (input && input.url) || "";
    var localPath = lookupLocalPath(method, url);
    if (localPath) return originalFetch(localPath, init);
    var rewritten = rewriteUrl(url);
    if (rewritten !== url) return originalFetch(rewritten, init);
    return originalFetch(input, init);
  };

  var originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    var localPath = lookupLocalPath(method, url);
    if (localPath) {
      return originalOpen.apply(this, [method, localPath].concat(Array.prototype.slice.call(arguments, 2)));
    }
    return originalOpen.apply(this, [method, rewriteUrl(url)].concat(Array.prototype.slice.call(arguments, 2)));
  };

  function extractRouteFromUrl(url) {
    if (!url) return "";
    var str = String(url);
    var hashIndex = str.indexOf("#");
    if (hashIndex >= 0) return normalizeRoute(str.slice(hashIndex));
    try {
      var parsed = new URL(str, window.location.href);
      var path = parsed.pathname || "";
      var appMatch = path.match(/\\/app\\/[^/]+\\/?(.*)$/i);
      if (appMatch && appMatch[1]) return normalizeRoute(appMatch[1]);
      return normalizeRoute(path);
    } catch (err) {
      return normalizeRoute(str);
    }
  }

  function lookupSlug(route) {
    if (!route) return null;
    if (routeMap[route]) return routeMap[route];
    var bestKey = null;
    var bestLen = 0;
    for (var key in routeMap) {
      if (!Object.prototype.hasOwnProperty.call(routeMap, key)) continue;
      if (route === key) return routeMap[key];
      if (route.indexOf(key + "/") === 0 || key.indexOf(route + "/") === 0) {
        if (key.length > bestLen) { bestLen = key.length; bestKey = key; }
      }
    }
    return bestKey ? routeMap[bestKey] : null;
  }

  function resolveTarget(href) {
    if (!href) return null;
    var route = extractRouteFromUrl(href);
    var slug = lookupSlug(route);
    if (slug) return { slug: slug, route: route || slugRouteMap[slug] || "" };

    var absMatch = href.match(/\\/pages\\/([^/]+)\\/index\\.html/i);
    if (absMatch && availableSlugs.indexOf(absMatch[1]) >= 0) {
      slug = absMatch[1];
      return { slug: slug, route: slugRouteMap[slug] || route };
    }

    var relMatch = href.match(/(?:\\.\\.\\/|\\/)?([a-z0-9][a-z0-9-]+)\\/index\\.html/i);
    if (relMatch && availableSlugs.indexOf(relMatch[1]) >= 0) {
      slug = relMatch[1];
      return { slug: slug, route: slugRouteMap[slug] || route };
    }
    return null;
  }

  function pageUrl(slug, route) {
    var hash = route ? "#/" + route : "";
    return "/pages/" + slug + "/index.html" + hash;
  }

  function hardNavigate(slug, route) {
    if (!slug || navigating) return false;
    navigating = true;
    var url = pageUrl(slug, route);
    console.log("[ROUTER] Full page nav:", currentSlug, "->", slug, url);
    try {
      sessionStorage.setItem("offline_pending_slug", slug);
      sessionStorage.setItem("offline_pending_at", String(Date.now()));
    } catch (err) {}
    try { window.stop(); } catch (err) {}
    window.location.replace(url);
    return true;
  }

  function navigateTo(href) {
    var target = resolveTarget(href);
    if (!target || target.slug === currentSlug) return false;
    markHuman();
    return hardNavigate(target.slug, target.route);
  }

  function isDashboardReset(url) {
    var route = extractRouteFromUrl(url);
    return route === "home/dashboard" || route === "home";
  }

  function shouldBlockDashboardReset(url) {
    if (!url || isHuman() || !isBootLocked()) return false;
    if (!intendedRoute || intendedRoute === "home/dashboard" || intendedRoute === "home") return false;
    return isDashboardReset(url);
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a[href]");
    if (!link) return;
    var href = link.getAttribute("href");
    if (!href || href.indexOf("javascript:") === 0) return;
    if (!resolveTarget(href)) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    navigateTo(href);
  }, true);

  var originalPushState = history.pushState;
  var originalReplaceState = history.replaceState;

  history.pushState = function (state, title, url) {
    if (url != null && isHuman() && navigateTo(String(url))) return;
    if (shouldBlockDashboardReset(url)) {
      console.log("[ROUTER] Blocked dashboard reset:", url);
      ensureRouteHash();
      return;
    }
    return originalPushState.apply(this, arguments);
  };

  history.replaceState = function (state, title, url) {
    if (url != null && isHuman() && navigateTo(String(url))) return;
    if (shouldBlockDashboardReset(url)) {
      console.log("[ROUTER] Blocked dashboard reset:", url);
      ensureRouteHash();
      return;
    }
    return originalReplaceState.apply(this, arguments);
  };

  window.addEventListener("hashchange", function () {
    if (isHuman() && navigateTo(window.location.href)) return;
    if (shouldBlockDashboardReset(window.location.href)) ensureRouteHash();
  });

  window.__offlineNavigateTo = navigateTo;
})();
"""


def api_origin_for(post_auth_home: str) -> str:
    parsed = urlparse(post_auth_home)
    return f"{parsed.scheme}://{parsed.netloc}"


def build_route_map(app_name: str) -> dict[str, str]:
    crawl_dir = STORAGE_DIR / app_name / "crawl"
    route_map: dict[str, str] = {}

    for metadata_path in crawl_dir.glob("**/metadata.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        slug = metadata.get("slug", metadata_path.parent.name)
        url = metadata.get("url", "")
        normalized = metadata.get("normalized_url") or normalize_crawl_url(url)

        routes: set[str] = set()

        if url and "#" in url:
            hash_route = url.split("#", 1)[1].split("?")[0].strip("/").lower()
            if hash_route:
                routes.add(hash_route)

        parsed = urlparse(normalized)
        path = parsed.path or ""
        app_match = re.search(r"/app/[^/]+/?(.*)$", path, re.IGNORECASE)
        if app_match and app_match.group(1):
            routes.add(app_match.group(1).strip("/").lower())
        elif path.strip("/"):
            routes.add(path.strip("/").lower())

        for route in routes:
            route_map[route] = slug

    return route_map


def build_slug_route_map(route_map: dict[str, str]) -> dict[str, str]:
    slug_routes: dict[str, str] = {}
    for route, slug in route_map.items():
        existing = slug_routes.get(slug)
        if not existing or len(route) > len(existing):
            slug_routes[slug] = route
    return slug_routes


def build_page_mock_map(page_slug: str, registry: dict) -> dict[str, str]:
    page_mocks: dict[str, str] = {}
    for key, entry in registry.items():
        pages = entry.get("pages", [])
        if pages and page_slug not in pages:
            continue
        local = f"/__mocks__/{entry['mock_file']}"
        page_mocks[key] = local
        path_key = entry.get("path_key")
        if path_key and path_key not in page_mocks:
            page_mocks[path_key] = local
    return page_mocks


def inject_head_scripts(html: str, injection: str) -> str:
    lower = html.lower()
    head_match = re.search(r"<head[^>]*>", lower)
    if head_match:
        insert_at = head_match.end()
        return html[:insert_at] + injection + html[insert_at:]
    if "</head>" in lower:
        pos = lower.index("</head>")
        return html[:pos] + injection + html[pos:]
    return injection + html


def copy_mocks_to_site(app_name: str, site_dir: Path) -> int:
    source = global_mock_dir(app_name)
    target = site_dir / "_mocks"
    if target.exists():
        shutil.rmtree(target)
    if not source.exists():
        return 0
    shutil.copytree(source, target)
    return len(list(target.glob("*.json")))


def resolve_home_slug(
    app_name: str, route_map: dict[str, str], available_slugs: list[str]
) -> str:
    post_auth_home = get_app_config(app_name).get("post_auth_home", "")
    if post_auth_home and "#" in post_auth_home:
        home_route = post_auth_home.split("#", 1)[1].split("?")[0].strip("/").lower()
        slug = route_map.get(home_route)
        if slug and slug in available_slugs:
            return slug

    for candidate in available_slugs:
        if "home-dashboard" in candidate and "__interaction" not in candidate:
            return candidate

    return available_slugs[0] if available_slugs else ""


def prepare_site(app_name: str) -> Path:
    from stitcher import stitch_app

    site_dir = stitch_app(app_name)
    registry = load_or_build_registry(app_name)
    route_map = build_route_map(app_name)
    slug_route_map = build_slug_route_map(route_map)
    mock_count = copy_mocks_to_site(app_name, site_dir)

    api_origin = api_origin_for(get_app_config(app_name)["post_auth_home"])
    pages_dir = site_dir / "pages"
    assets_dir = site_dir / "_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "mock-bridge.js").write_text(MOCK_BRIDGE_JS, encoding="utf-8")

    available_slugs = sorted(set(route_map.values()))

    home_slug = resolve_home_slug(app_name, route_map, available_slugs)
    home_route = slug_route_map.get(home_slug, "home/dashboard")

    route_payload = json.dumps(route_map, separators=(",", ":"))
    slug_route_payload = json.dumps(slug_route_map, separators=(",", ":"))
    slugs_payload = json.dumps(available_slugs, separators=(",", ":"))
    origins_payload = json.dumps([api_origin], separators=(",", ":"))

    print(f"[SERVE-PREP] Route map entries: {len(route_map)}")
    print(f"[SERVE-PREP] Canonical pages: {len(available_slugs)}")
    print(f"[SERVE-PREP] Home page: {home_slug}")

    home_hash = f"#/{home_route}" if home_route else ""
    root_index = (
        "<!DOCTYPE html><html><head>"
        f'<meta http-equiv="refresh" content="0;url=pages/{home_slug}/index.html{home_hash}">'
        f'<script>window.location.replace("pages/{home_slug}/index.html{home_hash}");</script>'
        "</head><body></body></html>"
    )
    (site_dir / "index.html").write_text(root_index, encoding="utf-8")
    shell_path = site_dir / "shell.html"
    if shell_path.exists():
        shell_path.unlink()

    for page_dir in pages_dir.iterdir():
        if not page_dir.is_dir():
            continue

        slug = page_dir.name
        index_path = page_dir / "index.html"
        if not index_path.exists():
            continue

        page_mocks = build_page_mock_map(slug, registry)
        mocks_payload = json.dumps(page_mocks, separators=(",", ":"))
        current_slug_payload = json.dumps(slug)
        intended_route = slug_route_map.get(slug, "")
        intended_route_payload = json.dumps(intended_route)

        injection = (
            f'<script>'
            f'window.__ROUTE_MAP__={route_payload};'
            f'window.__SLUG_ROUTE_MAP__={slug_route_payload};'
            f'window.__AVAILABLE_SLUGS__={slugs_payload};'
            f'window.__CURRENT_SLUG__={current_slug_payload};'
            f'window.__INTENDED_ROUTE__={intended_route_payload};'
            f'window.__MOCK_API_ORIGINS__={origins_payload};'
            f'window.__PAGE_MOCKS__={mocks_payload};'
            f'</script>'
            f'<script src="../../_assets/mock-bridge.js"></script>'
        )

        html = index_path.read_text(encoding="utf-8")
        index_path.write_text(inject_head_scripts(html, injection), encoding="utf-8")

    (site_dir / "mock_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    (site_dir / "route_map.json").write_text(json.dumps(route_map, indent=2), encoding="utf-8")

    print(f"[SERVE-PREP] Copied {mock_count} mock payloads into {site_dir / '_mocks'}")
    print(f"[SERVE-PREP] Registry entries: {len(registry)}")
    return site_dir


class OfflineAppHandler(BaseHTTPRequestHandler):
    app_name: str = ""
    site_dir: Path = Path()
    registry: dict = {}

    def log_message(self, format: str, *args) -> None:
        print(f"[HTTP] {self.address_string()} {format % args}")

    def _send_json_mock(self, mock_path: Path) -> bool:
        body = mock_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json;charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
        return True

    def _try_mock(self, method: str) -> bool:
        parsed = urlparse(self.path)
        mock_path = resolve_mock_file(
            self.app_name,
            self.registry,
            method,
            parsed.path,
            parsed.query,
        )
        if mock_path:
            print(f"[MOCK] {method} {self.path} -> {mock_path.name}")
            return self._send_json_mock(mock_path)
        return False

    def _serve_static(self) -> None:
        parsed = urlparse(self.path)
        rel_path = parsed.path.lstrip("/")
        if not rel_path:
            rel_path = "index.html"

        file_path = (self.site_dir / rel_path).resolve()
        if not str(file_path).startswith(str(self.site_dir.resolve())):
            self.send_error(403)
            return

        if file_path.is_dir():
            file_path = file_path / "index.html"

        if not file_path.exists():
            self.send_error(404, f"Not found: {rel_path}")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        body = file_path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/__mocks__/"):
            mock_name = self.path.split("/__mocks__/")[-1]
            mock_path = self.site_dir / "_mocks" / mock_name
            if mock_path.exists():
                self._send_json_mock(mock_path)
                return
        if self._try_mock("GET"):
            return
        self._serve_static()

    def do_POST(self) -> None:
        if self._try_mock("POST"):
            return
        self.send_error(404)

    def do_PUT(self) -> None:
        if self._try_mock("PUT"):
            return
        self.send_error(404)

    def do_PATCH(self) -> None:
        if self._try_mock("PATCH"):
            return
        self.send_error(404)

    def do_DELETE(self) -> None:
        if self._try_mock("DELETE"):
            return
        self.send_error(404)


def serve_app(app_name: str, port: int = 8765, prepare: bool = True) -> None:
    site_dir = SITE_DIR / app_name
    if prepare or not site_dir.exists():
        site_dir = prepare_site(app_name)

    registry = load_or_build_registry(app_name)

    handler = OfflineAppHandler
    handler.app_name = app_name
    handler.site_dir = site_dir
    handler.registry = registry

    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"[SERVE] App: {app_name}")
    print(f"[SERVE] Site root: {site_dir}")
    print(f"[SERVE] Mock endpoints: {len(registry)}")
    print(f"[SERVE] Open: http://127.0.0.1:{port}/")
    server.serve_forever()


def parse_args():
    parser = argparse.ArgumentParser(description="Serve offline app with API mocks")
    parser.add_argument("--app-name", required=True, help="App key from config.APPS")
    parser.add_argument("--port", type=int, default=8765, help="Local port (default: 8765)")
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Skip stitch/mock preparation and serve existing site output",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    serve_app(args.app_name, port=args.port, prepare=not args.no_prepare)


if __name__ == "__main__":
    main()
