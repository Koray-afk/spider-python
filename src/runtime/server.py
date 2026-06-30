"""Local clone runtime — serve a stitched app as a navigable static website.

    python main.py serve <app> [--port 8000] [--watch] [--no-open]

Routing:
  * `/`            → entry page (redirect to <entry-slug>/page.html)
  * `/<path>`      → static file under storage/apps/<app>/stitched
  * missing file   → 404.html (status 404), never a raw browser error

`--watch` injects a tiny live-reload poller into served HTML and exposes
`/__stitch_version`; when any stitched file changes the open tab reloads.
"""

import functools
import http.server
import json
import socketserver
import threading
import webbrowser
from pathlib import Path

from storage.storage_manager import get_stitched_dir

DEFAULT_PORT = 8000

_LIVERELOAD_SNIPPET = """
<script>
(function () {
  var current = null;
  function poll() {
    fetch("/__stitch_version", { cache: "no-store" })
      .then(function (r) { return r.text(); })
      .then(function (v) {
        if (current === null) { current = v; }
        else if (v !== current) { location.reload(); }
      })
      .catch(function () {});
  }
  setInterval(poll, 1000);
  poll();
})();
</script>
"""


# Slug substrings checked in order when picking the entry page.
# HubSpot-specific hints come first so contacts-list / global-home
# are preferred over the empty reports-dashboard shell.
_ENTRY_SLUG_HINTS = (
    "contacts-list-view-all",  # HubSpot contacts list
    "global-home",             # HubSpot home overview
    "home-dashboard",          # Zoho dashboard
    "dashboard",
    "home",
)


_LOGIN_PAGE_MARKERS = (
    "<title>HubSpot Login",
    'data-application-name="LoginUI"',
    "Your authentication has expired",
    "Sign in to HubSpot",
    "data-error-type=\"SESSION_TIMED_OUT\"",
)


def _is_login_page_html(path: Path) -> bool:
    """Return True if the page.html at *path* is a login/auth redirect."""
    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:3000]
        return any(m in snippet for m in _LOGIN_PAGE_MARKERS)
    except Exception:
        return False


def _resolve_entry_path(stitched_dir: Path) -> str:
    """Return the root-relative URL of the entry page.

    Prefers well-known home/dashboard slugs (HubSpot contacts-list, global-home,
    Zoho home-dashboard) over generic "dashboard"-titled pages, and explicitly
    skips HubSpot's reports-dashboard (empty JS shell) and any page whose saved
    HTML is actually a HubSpot login/auth-expired redirect.
    """
    def _is_good(slug: str) -> bool:
        p = stitched_dir / slug / "page.html"
        if not p.exists():
            return False
        if slug.startswith("reports-dashboard"):
            return False
        if _is_login_page_html(p):
            return False
        return True

    nav = stitched_dir / "navigation.json"
    if nav.exists():
        try:
            data = json.loads(nav.read_text(encoding="utf-8"))
            # 1. Check slug hints in priority order.
            for hint in _ENTRY_SLUG_HINTS:
                for slug in data:
                    if hint in slug.lower() and _is_good(slug):
                        return f"/{slug}/page.html"
            # 2. Fall back to any page whose title contains "dashboard".
            for slug, info in data.items():
                if "dashboard" in (info.get("title", "") or "").lower() and _is_good(slug):
                    return f"/{slug}/page.html"
            # 3. First entry in navigation that has a valid page.html on disk.
            for slug in data:
                if _is_good(slug):
                    return f"/{slug}/page.html"
        except Exception:
            pass
    # 4. Any directory with a valid page.html.
    for d in sorted(stitched_dir.iterdir()):
        if d.is_dir() and _is_good(d.name):
            return f"/{d.name}/page.html"
    if (stitched_dir / "index.html").exists():
        return "/index.html"
    return "/404.html"


def _max_mtime(root: Path) -> float:
    latest = 0.0
    for f in root.rglob("*"):
        if f.is_file():
            try:
                latest = max(latest, f.stat().st_mtime)
            except OSError:
                pass
    return latest


def _make_handler(stitched_dir: Path, entry_path: str, watch: bool):
    directory = str(stitched_dir.resolve())

    class CloneHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, fmt, *args):  # quieter, prefixed logging
            print(f"[SERVER] {self.address_string()} {fmt % args}")

        def end_headers(self):
            # Dev server: never cache, so edits/--watch always show through.
            self.send_header("Cache-Control", "no-store, must-revalidate")
            super().end_headers()

        def _send_bytes(self, body: bytes, status: int, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0].split("#", 1)[0]

            if watch and path == "/__stitch_version":
                self._send_bytes(
                    str(_max_mtime(stitched_dir)).encode(), 200, "text/plain; charset=utf-8"
                )
                return

            if path in ("/", "/index.html"):
                self.send_response(302)
                self.send_header("Location", entry_path)
                self.end_headers()
                return

            local = Path(self.translate_path(self.path))
            if local.is_file() and local.suffix.lower() in (".html", ".htm"):
                self._serve_html(local)
                return

            super().do_GET()

        def _serve_html(self, file_path: Path):
            try:
                html = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self.send_error(404)
                return
            if watch and "</body>" in html:
                html = html.replace("</body>", _LIVERELOAD_SNIPPET + "</body>", 1)
            self._send_bytes(html.encode("utf-8"), 200, "text/html; charset=utf-8")

        def send_error(self, code, message=None, explain=None):
            if code == 404:
                fallback = stitched_dir / "404.html"
                if fallback.exists():
                    self._send_bytes(fallback.read_bytes(), 404, "text/html; charset=utf-8")
                    return
            super().send_error(code, message, explain)

    return CloneHandler


class _ReusableServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve_app(
    app_name: str,
    port: int = DEFAULT_PORT,
    *,
    watch: bool = False,
    open_browser: bool = True,
) -> None:
    stitched_dir = get_stitched_dir(app_name)
    if not stitched_dir.is_dir() or not any(stitched_dir.glob("*/page.html")):
        raise FileNotFoundError(
            f"No stitched output for '{app_name}' at {stitched_dir}. "
            f"Run: python main.py stitch {app_name}"
        )

    entry_path = _resolve_entry_path(stitched_dir)
    handler = _make_handler(stitched_dir, entry_path, watch)

    try:
        httpd = _ReusableServer(("127.0.0.1", port), handler)
    except OSError as exc:
        raise OSError(f"Could not bind to port {port}: {exc}. Try --port <other>.") from exc

    url = f"http://localhost:{port}{entry_path}"
    print("[SERVER]")
    print(f"Serving:\n{stitched_dir.resolve()}")
    print("[SERVER]")
    print(f"URL:\n{url}")
    print(f"[SERVER] Root redirect: / → {entry_path}")
    if watch:
        print("[SERVER] Watch mode: open tabs auto-reload on file changes")
    print("[SERVER] Press Ctrl+C to stop")

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Stopping…")
    finally:
        httpd.shutdown()
        httpd.server_close()
