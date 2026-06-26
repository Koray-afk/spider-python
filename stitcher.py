import json
import re
from pathlib import Path

from config import ROOT_DIR, STORAGE_DIR, get_app_config
from urls import normalize_crawl_url, resolve_href

SITE_DIR = ROOT_DIR / "site"

A_HREF_RE = re.compile(
    r"(<a\b[^>]*?\bhref=)([\"'])(.*?)\2",
    re.IGNORECASE | re.DOTALL,
)

STITCH_JS = """\
(function () {
  var routes = window.__STITCHED_ROUTES__ || {};

  function normalizeCrawlUrl(url) {
    try {
      var parsed = new URL(url);
      var path = parsed.pathname || "/";
      if (path.length > 1 && path.charAt(path.length - 1) === "/") {
        path = path.slice(0, -1);
      }

      var query = parsed.search ? parsed.search.slice(1) : "";
      if (parsed.hash && parsed.hash.length > 1) {
        var hash = parsed.hash.slice(1);
        var qIndex = hash.indexOf("?");
        if (qIndex >= 0) {
          query = query ? query + "&" + hash.slice(qIndex + 1) : hash.slice(qIndex + 1);
          hash = hash.slice(0, qIndex);
        }
        var route = hash.replace(/^\\/+/, "");
        if (route) {
          path = path + "/" + route;
        }
      }

      if (query) {
        query = query.split("&").sort().join("&");
      }

      return parsed.protocol + "//" + parsed.host + path + (query ? "?" + query : "");
    } catch (err) {
      return url;
    }
  }

  document.addEventListener("click", function (e) {
    var link = e.target.closest("a[href]");
    if (!link || e.defaultPrevented) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (link.target && link.target.toLowerCase() === "_blank") return;

    var href = link.getAttribute("href");
    if (!href || href.indexOf("javascript:") === 0) return;

    var absolute;
    try {
      absolute = new URL(href, window.location.href).href;
    } catch (err) {
      return;
    }

    var normalized = normalizeCrawlUrl(absolute);
    var local = routes[href] || routes[absolute] || routes[normalized];
    if (!local) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    if (window.__offlineNavigateTo && window.__offlineNavigateTo(href || absolute || local)) return;
    try {
      var resolved = new URL(local, window.location.href);
      window.location.replace(resolved.pathname + resolved.search + resolved.hash);
    } catch (err) {
      window.location.replace(local);
    }
  }, true);
})();
"""


def scan_pages(crawl_dir: Path) -> list[dict]:
    pages = []

    for html_path in sorted(crawl_dir.glob("**/page.html")):
        page_dir = html_path.parent
        metadata_path = page_dir / "metadata.json"

        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            url = metadata.get("url", "")
            normalized_url = metadata.get("normalized_url") or normalize_crawl_url(url)
            slug = metadata.get("slug", page_dir.name)
            title = metadata.get("title", "")
        else:
            slug = page_dir.name
            url = ""
            normalized_url = ""
            title = ""

        pages.append({
            "url": url,
            "normalized_url": normalized_url,
            "slug": slug,
            "title": title,
            "html_path": html_path,
            "page_dir": page_dir,
        })

    return pages


def build_url_map(pages: list[dict]) -> dict[str, str]:
    url_map: dict[str, str] = {}

    for page in pages:
        normalized = page["normalized_url"]
        if not normalized:
            continue
        url_map[normalized] = page["slug"]

    for index, (url, slug) in enumerate(url_map.items()):
        if index >= 20:
            break
        print(f"[STITCH] URL:\n{url}\n")
        print(f"[STITCH] SLUG:\n{slug}\n")

    return url_map


def lookup_slug(href: str, page_url: str, url_map: dict[str, str]) -> str | None:
    absolute = resolve_href(page_url, href)
    if not absolute:
        return None

    normalized = normalize_crawl_url(absolute)
    return url_map.get(normalized)


def relative_page_path(from_slug: str, to_slug: str) -> str:
    if from_slug == to_slug:
        return "index.html"
    return f"../{to_slug}/index.html"


def rewrite_anchors(html: str, page_url: str, url_map: dict[str, str], from_slug: str) -> str:
    def replace_href(match: re.Match) -> str:
        prefix, quote, href = match.group(1), match.group(2), match.group(3)

        if not href or href.startswith(("javascript:", "mailto:", "tel:", "data:")):
            return match.group(0)

        target_slug = lookup_slug(href, page_url, url_map)
        if not target_slug:
            return match.group(0)

        local_href = relative_page_path(from_slug, target_slug)
        return f'{prefix}{quote}{local_href}{quote} data-stitched-local="true"'

    return A_HREF_RE.sub(replace_href, html)


def build_page_routes(from_slug: str, pages: list[dict]) -> dict[str, str]:
    routes: dict[str, str] = {}
    for page in pages:
        to_slug = page["slug"]
        local = relative_page_path(from_slug, to_slug)
        if page["normalized_url"]:
            routes[page["normalized_url"]] = local
        if page["url"]:
            routes[page["url"]] = local
    return routes


def inject_client_scripts(html: str, routes: dict[str, str], asset_href: str) -> str:
    payload = json.dumps(routes, separators=(",", ":"))
    injection = (
        f'<script>window.__STITCHED_ROUTES__={payload}</script>'
        f'<script src="{asset_href}"></script>'
    )

    body_match = re.search(r"</body>", html, re.IGNORECASE)
    if body_match:
        pos = body_match.start()
        return html[:pos] + injection + html[pos:]
    return html + injection


def resolve_home_slug(pages: list[dict], url_map: dict[str, str], app_name: str) -> str:
    app_config = get_app_config(app_name)
    post_auth_home = app_config.get("post_auth_home", "")

    if post_auth_home:
        home_normalized = normalize_crawl_url(post_auth_home)
        home_slug = url_map.get(home_normalized)
        if home_slug:
            print(f"[STITCH] Home page: {home_slug}")
            return home_slug

        for page in pages:
            if page["normalized_url"] == home_normalized:
                print(f"[STITCH] Home page: {page['slug']}")
                return page["slug"]

    print("[STITCH] Home page not found, using first page fallback")
    return pages[0]["slug"]


def stitch_app(app_name: str) -> Path:
    crawl_dir = STORAGE_DIR / app_name / "crawl"
    if not crawl_dir.exists():
        raise FileNotFoundError(f"Crawl directory not found: {crawl_dir}")

    pages = scan_pages(crawl_dir)
    if not pages:
        raise ValueError(f"No HTML pages found in {crawl_dir}")

    print(f"[STITCH] Scanning {len(pages)} pages")

    url_map = build_url_map(pages)
    print(f"[STITCH] Pages scanned: {len(pages)}")
    print(f"[STITCH] Route map entries: {len(url_map)}")

    output_dir = SITE_DIR / app_name
    pages_dir = output_dir / "pages"
    assets_dir = output_dir / "_assets"
    pages_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    (assets_dir / "stitch.js").write_text(STITCH_JS, encoding="utf-8")

    rewritten = 0

    for page in pages:
        slug = page["slug"]
        page_url = page["url"]
        html = page["html_path"].read_text(encoding="utf-8")

        before = html
        html = rewrite_anchors(html, page_url, url_map, slug)
        if html != before:
            rewritten += 1

        page_routes = build_page_routes(slug, pages)
        html = inject_client_scripts(html, page_routes, "../../_assets/stitch.js")

        out_dir = pages_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

    home_slug = resolve_home_slug(pages, url_map, app_name)
    root_index = (
        f'<!DOCTYPE html><html><head>'
        f'<meta http-equiv="refresh" content="0;url=pages/{home_slug}/index.html">'
        f'<script>window.location.href="pages/{home_slug}/index.html"</script>'
        f'</head><body></body></html>'
    )
    (output_dir / "index.html").write_text(root_index, encoding="utf-8")

    print(f"[STITCH] Rewrote links in {rewritten} pages")
    print(f"[STITCH] Output: {output_dir}")
    return output_dir
