"""Turn crawled Zoho HTML into a stitched offline site with working sidebar nav."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from home_pages import generate_home_subpages, merge_sitemap
from offline_ui import HASH_NEW_ROUTES, HASH_PREFIX_ROUTES, build_interaction_js

OVERLAY_HIDE_STYLE = """<style>
#zcwindows, .zcoverlay, .zsiq_theme1, #zsiq_float, #zsiq_chat_wrap,
iframe, #micsbackdrop, #wmstoolbar, #tooltip-popover-wrapper,
#zgs20_globalsearch, .zgs19_gsOverlay, #zgs20_gsOverlay,
.popover-container { display: none !important; pointer-events: none !important; }
#main-nav-tab, .main-nav-lhs, .main-nav-lhs a, a.nav-link[href$=".html"] {
  pointer-events: auto !important; cursor: pointer !important;
}
.dropdown, button.dropdown, .orglist-topband { position: relative !important; }
.dropdown-menu {
  list-style: none; margin: 0; padding: 4px 0;
  background: #fff; border: 1px solid rgba(0,0,0,.12); border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,.12); min-width: 160px;
  display: none !important;
}
.dropdown-menu .dropdown-item {
  display: block; padding: 8px 16px; color: #212529;
  text-decoration: none; white-space: nowrap; cursor: pointer;
}
.dropdown-menu .dropdown-item:hover { background: #f5f7fa; }
.dropdown.show > .dropdown-menu,
.dropdown-menu.show { display: block !important; z-index: 9990; }
.ac-dropdown .dropdown-menu { position: absolute; top: 100%; left: 0; width: 100%; }
#main-nav-tab .nav-main-module a,
#main-nav-tab .dropdown-item.nav-link { pointer-events: auto !important; }
</style>"""


def _fragment_key(fragment: str) -> str | None:
    if not fragment:
        return None
    clean = fragment.strip("/")
    return f"#/{clean}" if clean else "#/home"


def build_route_map(sitemap: list, pages_dir: Path) -> dict[str, str]:
    route_map: dict[str, str] = {}

    for item in sitemap:
        slug = item["slug"]
        target = f"{slug}.html"
        url = item["url"]
        parsed = urlparse(url)
        route_map[url] = target

        key = _fragment_key(parsed.fragment)
        if key:
            route_map[key] = target
            route_map[key.rstrip("/")] = target
        else:
            route_map["#/home"] = target
            route_map["#/home/dashboard"] = target

    for meta_path in pages_dir.glob("*.meta"):
        slug = meta_path.stem
        target = f"{slug}.html"
        url = meta_path.read_text(encoding="utf-8").strip()
        if not url:
            continue
        parsed = urlparse(url)
        route_map[url] = target
        key = _fragment_key(parsed.fragment)
        if key:
            route_map[key] = target
            route_map[key.rstrip("/")] = target
        elif url.startswith("#/"):
            route_map[url.split("?")[0]] = target
            route_map[url.split("?")[0].rstrip("/")] = target
        else:
            route_map["#/home"] = target

    route_map.setdefault("#/home/gettingstarted", "home-gettingstarted.html")
    route_map.setdefault("#/home/recentupdates", "home-recentupdates.html")

    return route_map


def _hash_route(url: str) -> str | None:
    """Extract #/route from hash links, ignoring query strings."""
    if url.startswith("#/"):
        path = url.split("?")[0].rstrip("/")
        return path or "#/home"
    if "://" in url:
        fragment = urlparse(url).fragment
        if fragment:
            path = fragment.split("?")[0].strip("/")
            return f"#/{path}" if path else "#/home"
    return None


def _lookup_route(url: str, route_map: dict[str, str]) -> str | None:
    if url in route_map:
        return route_map[url]

    key = _hash_route(url)
    if not key:
        return None
    if key in route_map:
        return route_map[key]

    trimmed = key.rstrip("/")
    if trimmed in route_map:
        return route_map[trimmed]

    if not key.startswith("#/"):
        return None

    path = key[2:]
    if path.endswith("/new"):
        base = path[:-4]
        if base in HASH_NEW_ROUTES:
            return HASH_NEW_ROUTES[base]
        for prefix, target in sorted(HASH_NEW_ROUTES.items(), key=lambda x: -len(x[0])):
            if path == prefix + "/new" or path.startswith(prefix + "/"):
                return target

    for prefix, target in sorted(HASH_PREFIX_ROUTES.items(), key=lambda x: -len(x[0])):
        if path == prefix or path.startswith(prefix + "/"):
            return target

    return None


def rewrite_route_links(html: str, route_map: dict[str, str]) -> str:
    def replace_href(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.endswith(".html") or url.startswith(("data:", "javascript:", "mailto:", "tel:", "../")):
            return match.group(0)

        target = _lookup_route(url, route_map)
        if target:
            return f'{attr}={quote}{target}{quote}'

        return match.group(0)

    return re.sub(r'(href)=(["\'])([^"\']+)\2', replace_href, html)


def strip_scripts(html: str) -> str:
    return re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)


def expand_sidebar(html: str) -> str:
    """Uncollapse sidebar sections so nav links are visible without Ember."""
    html = re.sub(
        r'(<ul[^>]*class="[^"]*collapse[^"]*"[^>]*)\s+hidden="true"',
        r"\1",
        html,
    )
    html = html.replace("accordion-button collapsed", "accordion-button")
    html = html.replace("accordion-title collapsed", "accordion-title")
    return html


def cleanup_prior_stitch(html: str) -> str:
    html = re.sub(
        r"<style>\s*\n#zcwindows.*?</style>\s*",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html


def enable_sidebar_clicks(html: str) -> str:
    """Zoho freezes the sidebar with pointer-events:none during SPA transitions."""
    return re.sub(
        r'(<nav[^>]*id="main-nav-tab"[^>]*style="[^"]*)pointer-events:\s*none;?',
        r"\1pointer-events: auto;",
        html,
        flags=re.IGNORECASE,
    )


def inject_static_ui(html: str, route_map: dict[str, str]) -> str:
    if re.search(r"</head>", html, flags=re.IGNORECASE):
        html = re.sub(r"</head>", OVERLAY_HIDE_STYLE + "\n</head>", html, count=1, flags=re.IGNORECASE)
    else:
        html = OVERLAY_HIDE_STYLE + html

    html = re.sub(
        r'<script[^>]*data-offline-ui[^>]*>[\s\S]*?</script>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )

    static_script = build_interaction_js(route_map)

    if re.search(r"</body>", html, flags=re.IGNORECASE):
        return re.sub(r"</body>", static_script + "\n</body>", html, count=1, flags=re.IGNORECASE)
    return html + static_script


def build_index_html(sitemap: list) -> str:
    seen: set[str] = set()
    rows = []
    for item in sitemap:
        slug = item["slug"]
        if slug in seen:
            continue
        seen.add(slug)
        url = item.get("url", slug)
        rows.append(f'    <li><a href="{slug}.html">{slug}</a> <small>{url}</small></li>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Zoho Books — Offline</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }}
    a {{ color: #408dfb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    small {{ color: #666; margin-left: 0.5rem; }}
  </style>
</head>
<body>
  <h1>Zoho Books — Offline</h1>
  <p>Open the app at <a href="home.html"><strong>home.html</strong></a></p>
  <ul>
{chr(10).join(rows)}
  </ul>
</body>
</html>"""


def finalize_html(html: str, route_map: dict[str, str]) -> str:
    html = cleanup_prior_stitch(html)
    html = strip_scripts(html)
    html = expand_sidebar(html)
    html = enable_sidebar_clicks(html)
    html = rewrite_route_links(html, route_map)
    return inject_static_ui(html, route_map)


def stitch_pages(pages_dir: str = "pages") -> int:
    pages_path = Path(pages_dir)
    sitemap_path = pages_path / "sitemap.json"
    if not sitemap_path.exists():
        raise FileNotFoundError(f"Missing {sitemap_path} — run the crawler first.")

    sitemap = json.loads(sitemap_path.read_text(encoding="utf-8"))
    app_base = ""
    for item in sitemap:
        url = item.get("url", "")
        if "/app/" in url:
            app_base = url.split("#")[0]
            break

    home_entries = generate_home_subpages(pages_path, app_base)
    merge_sitemap(pages_path, home_entries)
    sitemap = json.loads(sitemap_path.read_text(encoding="utf-8"))

    route_map = build_route_map(sitemap, pages_path)
    count = 0

    for html_file in sorted(pages_path.glob("*.html")):
        if html_file.name == "index.html":
            continue
        html = html_file.read_text(encoding="utf-8")
        html_file.write_text(finalize_html(html, route_map), encoding="utf-8")
        count += 1
        print(f"  stitched {html_file.name}")

    index_path = pages_path / "index.html"
    index_path.write_text(build_index_html(sitemap), encoding="utf-8")
    print(f"  wrote {index_path}")
    return count


if __name__ == "__main__":
    print("[*] Stitching offline pages...")
    total = stitch_pages()
    print(f"\n✅ Done — {total} pages stitched.")
    print("   Serve with: python3 -m http.server 8080")
    print("   Then open:  http://localhost:8080/pages/home.html")
