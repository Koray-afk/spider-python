"""Wire crawled Zoho pages together — sidebar clicks load local HTML, no master index."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

# Minimal JS: accordion toggles + force local page navigation
NAV_SCRIPT_TEMPLATE = """<script id="static-replica-ui">
(function() {
  var ROUTES = __ROUTES_JSON__;
  var CURRENT = __CURRENT_SLUG__;

  function navigateLocal(href) {
    if (!href) return;
    window.location.assign(href);
  }

  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.accordion-button, .accordion-title');
    if (btn && !e.target.closest('a[data-local-nav]')) {
      e.preventDefault();
      e.stopPropagation();
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      btn.classList.toggle('collapsed', expanded);
      var panelId = btn.getAttribute('aria-controls');
      if (panelId) {
        var panel = document.getElementById(panelId);
        if (panel) {
          panel.hidden = expanded;
          panel.classList.toggle('show', !expanded);
        }
      }
      return;
    }

    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href) return;

    if (a.getAttribute('data-local-nav') === '1' || href.indexOf('index.html') >= 0) {
      e.preventDefault();
      e.stopImmediatePropagation();
      navigateLocal(href);
      return;
    }

    if (href.indexOf('#/') === 0) {
      var route = '#/' + href.slice(2).split('?')[0].replace(/^\\/+|\\/+$/g, '');
      var target = ROUTES[route];
      if (!target) {
        var parts = route.slice(2).split('/');
        for (var i = parts.length; i > 0; i--) {
          var candidate = '#/' + parts.slice(0, i).join('/');
          if (ROUTES[candidate]) { target = ROUTES[candidate]; break; }
        }
      }
      if (target) {
        e.preventDefault();
        e.stopImmediatePropagation();
        navigateLocal(target);
      }
    }
  }, true);

  document.querySelectorAll('a[data-local-nav]').forEach(function(a) {
    var href = a.getAttribute('href') || '';
    if (href.indexOf(CURRENT) >= 0) a.classList.add('active');
  });
})();
</script>"""

SIDEBAR_FIX_STYLE = """<style id="static-replica-sidebar">
  /* Zoho <base href> removed — ensure sidebar links are visible and clickable */
  .main-nav-lhs .collapse,
  .main-nav-lhs ul.collapse,
  .main-nav-lhs .accordion-collapse {
    display: block !important;
    height: auto !important;
    visibility: visible !important;
    overflow: visible !important;
  }
  .main-nav-lhs ul[hidden],
  .main-nav-lhs [hidden].collapse {
    display: block !important;
  }
  .main-nav-lhs a[data-local-nav],
  .main-nav-lhs a[href*="index.html"] {
    pointer-events: auto !important;
    cursor: pointer !important;
  }
</style>"""


def _fragment_key(fragment: str) -> str | None:
    if not fragment:
        return None
    clean = fragment.split("?")[0].strip("/")
    return f"#/{clean}" if clean else "#/home"


def hash_route_from_href(href: str) -> str | None:
    """#/quotes?filter_by=All → #/quotes"""
    if not href.startswith("#/"):
        return None
    route = href[2:].split("?")[0].strip("/")
    return f"#/{route}" if route else "#/home"


def normalize_spa_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    frag = parsed.fragment.split("?")[0] if parsed.fragment else ""
    if frag:
        return f"{parsed.scheme}://{parsed.netloc}{path}#{frag}"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def detect_layout(pages_dir: Path) -> str:
    if any(pages_dir.glob("*/index.html")):
        return "folder"
    if any(pages_dir.glob("*.html")):
        return "flat"
    return "folder"


def discover_html_files(pages_dir: Path) -> list[Path]:
    folder_pages = sorted(pages_dir.glob("*/index.html"))
    if folder_pages:
        return folder_pages
    return sorted(p for p in pages_dir.glob("*.html") if p.name != "index.html")


def discover_meta_files(pages_dir: Path) -> list[Path]:
    folder_meta = list(pages_dir.glob("*/index.meta"))
    if folder_meta:
        return folder_meta
    return list(pages_dir.glob("*.meta"))


def slug_from_html_path(html_path: Path, layout: str) -> str:
    if layout == "folder":
        return html_path.parent.name
    return html_path.stem


def local_href(from_slug: str, to_slug: str, layout: str) -> str:
    if layout == "flat":
        return f"{to_slug}.html"
    if from_slug == to_slug:
        return "index.html"
    return f"../{to_slug}/index.html"


def resolve_route_slug(href: str, slug_route_map: dict[str, str]) -> str | None:
    """Resolve a sidebar href to a crawled page slug."""
    if href in slug_route_map:
        return slug_route_map[href]

    route = hash_route_from_href(href)
    if route and route in slug_route_map:
        return slug_route_map[route]

    if route:
        trimmed = route.rstrip("/")
        if trimmed in slug_route_map:
            return slug_route_map[trimmed]
        parts = route[2:].split("/")
        for i in range(len(parts), 0, -1):
            candidate = "#/" + "/".join(parts[:i])
            if candidate in slug_route_map:
                return slug_route_map[candidate]

    if "://" in href:
        parsed = urlparse(href)
        norm = normalize_spa_url(href)
        if norm in slug_route_map:
            return slug_route_map[norm]
        key = _fragment_key(parsed.fragment)
        if key and key in slug_route_map:
            return slug_route_map[key]

    return None


def build_slug_route_map(sitemap: list, pages_dir: Path) -> dict[str, str]:
    route_map: dict[str, str] = {}

    def register(url: str, slug: str) -> None:
        parsed = urlparse(url)
        route_map[url] = slug
        route_map[normalize_spa_url(url)] = slug
        key = _fragment_key(parsed.fragment)
        if key:
            route_map[key] = slug
            route_map[key.rstrip("/")] = slug
        elif "books.zoho" in url:
            route_map["#/home"] = slug
            route_map["#/home/dashboard"] = slug

    # Only wire post-auth Zoho Books app routes — ignore marketing pages
    books_items = [i for i in sitemap if "books.zoho" in i.get("url", "")]
    for item in books_items:
        register(item["url"], item["slug"])

    for meta_path in discover_meta_files(pages_dir):
        slug = meta_path.parent.name if meta_path.name == "index.meta" else meta_path.stem
        url = meta_path.read_text(encoding="utf-8").strip()
        if url and "books.zoho" in url:
            register(url, slug)

    return route_map


def build_page_routes(from_slug: str, slug_route_map: dict[str, str], layout: str) -> dict[str, str]:
    """#/route → relative local path from this page."""
    routes: dict[str, str] = {}
    for key, slug in slug_route_map.items():
        if key.startswith("#/"):
            target = local_href(from_slug, slug, layout)
            routes[key] = target
            routes[key.rstrip("/")] = target
    return routes


def rewrite_route_links(
    html: str,
    slug_route_map: dict[str, str],
    from_slug: str,
    layout: str,
) -> str:
    def replace_href(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith(("data:", "javascript:", "mailto:", "tel:")):
            return match.group(0)
        if layout == "flat" and url.endswith(".html"):
            return match.group(0)
        if layout == "folder" and ("../" in url or url.endswith("/index.html") or url == "index.html"):
            return match.group(0)

        slug = resolve_route_slug(url, slug_route_map)
        if slug:
            target = local_href(from_slug, slug, layout)
            return f'{attr}={quote}{target}{quote} data-local-nav="1"'
        return match.group(0)

    return re.sub(r'(href)=(["\'])([^"\']+)\2', replace_href, html)


def remove_base_tag(html: str) -> str:
    """Zoho sets <base href=https://books.zoho.in/...> which breaks local ../ links."""
    return re.sub(r"<base\b[^>]*>", "", html, flags=re.IGNORECASE)


def strip_scripts(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+=([\"']).*?\1", "", html, flags=re.IGNORECASE)
    return html


def expand_sidebar(html: str) -> str:
    html = re.sub(
        r'(<ul[^>]*class="[^"]*collapse[^"]*"[^>]*)\s+hidden(?:="[^"]*")?',
        r'\1',
        html,
    )
    html = re.sub(
        r'(<div[^>]*class="[^"]*accordion-collapse[^"]*"[^>]*)\s+hidden(?:="[^"]*")?',
        r'\1',
        html,
    )
    html = html.replace("accordion-button collapsed", "accordion-button")
    html = html.replace("accordion-title collapsed", "accordion-title")
    html = re.sub(
        r'class="([^"]*\bcollapse\b[^"]*)"',
        lambda m: f'class="{m.group(1)} show"' if "show" not in m.group(1) else m.group(0),
        html,
    )
    html = re.sub(r'aria-expanded="false"', 'aria-expanded="true"', html)
    return html


def inject_sidebar_fix(html: str) -> str:
    if 'id="static-replica-sidebar"' in html:
        return html
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        return re.sub(r"(<head[^>]*>)", rf"\1\n{SIDEBAR_FIX_STYLE}", html, count=1, flags=re.IGNORECASE)
    return SIDEBAR_FIX_STYLE + html


def build_nav_script(from_slug: str, slug_route_map: dict[str, str], layout: str) -> str:
    routes = build_page_routes(from_slug, slug_route_map, layout)
    return (
        NAV_SCRIPT_TEMPLATE.replace("__ROUTES_JSON__", json.dumps(routes))
        .replace("__CURRENT_SLUG__", json.dumps(from_slug))
    )


def inject_nav_script(html: str, from_slug: str, slug_route_map: dict[str, str], layout: str) -> str:
    script = build_nav_script(from_slug, slug_route_map, layout)
    if re.search(r"</body>", html, flags=re.IGNORECASE):
        return re.sub(r"</body>", script + "\n</body>", html, count=1, flags=re.IGNORECASE)
    return html + script


def finalize_html(html: str, slug_route_map: dict[str, str], from_slug: str, layout: str) -> str:
    html = strip_scripts(html)
    html = remove_base_tag(html)
    html = expand_sidebar(html)
    html = inject_sidebar_fix(html)
    html = rewrite_route_links(html, slug_route_map, from_slug, layout)
    return inject_nav_script(html, from_slug, slug_route_map, layout)


def rebuild_sitemap_from_disk(pages_dir: Path) -> list:
    sitemap = []
    for meta in sorted(pages_dir.glob("*/index.meta")):
        slug = meta.parent.name
        url = meta.read_text(encoding="utf-8").strip()
        if (meta.parent / "index.html").exists() and url:
            sitemap.append({"slug": slug, "url": url, "title": slug})
    return sitemap


def remove_stale_master_index(pages_dir: Path) -> None:
    """Remove old pages/index.html directory listing if present."""
    master = pages_dir / "index.html"
    if not master.is_file():
        return
    try:
        text = master.read_text(encoding="utf-8")
    except OSError:
        return
    if "Zoho Books — Offline" in text and "<ul>" in text:
        master.unlink()
        print("  removed stale pages/index.html master listing")


def pick_entry_slug(sitemap: list) -> str | None:
    for item in sitemap:
        url = item.get("url", "")
        if "books.zoho" in url and ("dashboard" in url or "dashboard" in item["slug"]):
            return item["slug"]
    for item in sitemap:
        if "books.zoho" in item.get("url", ""):
            return item["slug"]
    return sitemap[0]["slug"] if sitemap else None


def stitch_pages(pages_dir: str, output_dir: str | None = None) -> int:
    pages_path = Path(pages_dir)
    out_path = Path(output_dir) if output_dir else pages_path
    sitemap_path = pages_path / "sitemap.json"
    if not sitemap_path.exists():
        meta_sitemap = pages_path.parent / "metadata" / "sitemap.json"
        if meta_sitemap.exists():
            sitemap_path = meta_sitemap

    if sitemap_path.exists():
        sitemap = json.loads(sitemap_path.read_text(encoding="utf-8"))
    else:
        sitemap = []

    if not sitemap:
        sitemap = rebuild_sitemap_from_disk(pages_path)
        if sitemap:
            dest = out_path / "sitemap.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(sitemap, indent=2), encoding="utf-8")
            print(f"  rebuilt sitemap from {len(sitemap)} index.meta files")

    if not sitemap:
        raise FileNotFoundError(
            f"Missing {sitemap_path} and no pages/*/index.meta found — run the crawler first."
        )

    if not output_dir:
        remove_stale_master_index(pages_path)
    else:
        out_path.mkdir(parents=True, exist_ok=True)

    layout = detect_layout(pages_path)
    html_files = discover_html_files(pages_path)
    if not html_files:
        raise FileNotFoundError(
            f"No page HTML found under {pages_path}. "
            f"Expected pages/<slug>/index.html."
        )

    slug_route_map = build_slug_route_map(sitemap, pages_path)
    count = 0

    for html_file in html_files:
        from_slug = slug_from_html_path(html_file, layout)
        html = html_file.read_text(encoding="utf-8")
        stitched = finalize_html(html, slug_route_map, from_slug, layout)
        dest_dir = out_path / from_slug if layout == "folder" else out_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "index.html" if layout == "folder" else dest_dir / f"{from_slug}.html"
        dest.write_text(stitched, encoding="utf-8")
        meta = html_file.parent / "index.meta"
        if layout == "folder" and meta.exists():
            (dest_dir / "index.meta").write_text(meta.read_text(encoding="utf-8"), encoding="utf-8")
        count += 1
        print(f"  stitched {from_slug}")

    if output_dir:
        (out_path / "sitemap.json").write_text(json.dumps(sitemap, indent=2), encoding="utf-8")

    print(f"  {count} pages → {out_path}")
    return count


def stitch_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_raw_html_dir,
        get_stitched_html_dir,
    )

    create_app_storage(app_name)
    raw_dir = get_raw_html_dir(app_name)
    stitched_dir = get_stitched_html_dir(app_name)

    if not raw_dir.is_dir():
        raise FileNotFoundError(f"No raw HTML at {raw_dir}")

    count = stitch_pages(str(raw_dir), str(stitched_dir))
    return {"pages_stitched": count, "stitched_dir": str(stitched_dir)}
