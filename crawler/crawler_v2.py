# pyrefly: ignore [missing-import]
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

# ── 1. RUNTIME CONFIG (injected by crawl_application) ───────────
_storage: dict | None = None

CHROME_MAC_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_dev_profile"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
"""
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
CSS_EXTS = {".css"}
FONT_EXTS = {".woff", ".woff2", ".ttf", ".eot"}
ASSET_EXTS = IMAGE_EXTS | CSS_EXTS | FONT_EXTS

# ── 2. STORAGE PATHS ───────────────────────────────────────────
def configure_storage(app_name, raw_html_dir, screenshots_dir, metadata_dir, logs_dir):
    global _storage
    for d in (raw_html_dir, screenshots_dir, metadata_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)
    _storage = {
        "app_name": app_name,
        "raw_html_dir": raw_html_dir,
        "screenshots_dir": screenshots_dir,
        "metadata_dir": metadata_dir,
        "logs_dir": logs_dir,
    }


def _paths():
    if not _storage:
        raise RuntimeError("configure_storage() must be called before crawling")
    return _storage


def save_sitemap(sitemap):
    path = _paths()["metadata_dir"] / "sitemap.json"
    path.write_text(json.dumps(sitemap, indent=2), encoding="utf-8")

# ── 3. UTILITIES ───────────────────────────────────────────────
def abs_url(url, base):
    if not url or url.startswith(("data:", "javascript:", "blob:", "mailto:", "tel:")):
        return None
    if url.startswith("#"):
        return base.split("#")[0] + url
    return url if url.startswith("http") else urljoin(base, url)

def normalize_spa_url(url):
    """Canonical key for SPA pages: path + #fragment (no query)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}#{parsed.fragment}" if parsed.fragment else f"{parsed.scheme}://{parsed.netloc}{path}"

def get_slug(url):
    parsed = urlparse(url)
    raw_path = f"{parsed.path}-{parsed.fragment}" if parsed.fragment else parsed.path
    clean_path = re.sub(r"[^a-zA-Z0-9]", "-", raw_path)
    clean_path = re.sub(r"-+", "-", clean_path).strip("-")
    return clean_path or "home"

def resolve_auth_file(app_name: str):
    from storage.storage_manager import get_auth_file, get_session_file

    auth_path = get_auth_file(app_name)
    session_path = get_session_file(app_name)
    print(f"AUTH FILE PATH: {auth_path}")
    print(f"SESSION FILE PATH: {session_path}")

    for path in (auth_path, session_path):
        if path.exists():
            print(f"Found auth file: {path}")
            return str(path)
    return None


def _release_cdp_browser(browser):
    """Experiments used browser.disconnect(); Playwright 1.60+ exposes close() instead."""
    if hasattr(browser, "disconnect"):
        browser.disconnect()
    else:
        browser.close()

def make_assets_absolute(html, page_url, include_js=False):
    """Absolutize CDN asset URLs so CSS/images/fonts load from file:// pages."""

    def replace(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith(("http", "data:", "javascript:", "blob:", "#", "mailto:", "tel:")):
            return match.group(0)

        ext = os.path.splitext(urlparse(url.split("?")[0]).path)[1].lower()
        if ext in {".js", ".mjs"} and not include_js:
            return match.group(0)

        if ext in ASSET_EXTS or ext in {".js", ".mjs"} or attr == "src":
            absolute_url = urljoin(page_url, url)
            return f"{attr}={quote}{absolute_url}{quote}"
        return match.group(0)

    return re.sub(r'(src|href)=(["\'])([^"\']+)\2', replace, html)

def remove_base_tag(html):
    return re.sub(r"<base\b[^>]*>", "", html, flags=re.IGNORECASE)

def strip_scripts(html):
    """Remove all JS so Ember/API code cannot run or hijack navigation."""
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*\bas="script"[^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*rel=["\']modulepreload["\'][^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+=([\"']).*?\1", "", html, flags=re.IGNORECASE)
    return html

def hash_route_from_href(href):
    if not href.startswith("#/"):
        return None
    route = href[2:].split("?")[0].strip("/")
    return f"#/{route}" if route else "#/home"

def build_href_index(url_slug_map):
    """Map every href variant (hash, path+hash, full URL) → local slug folder."""
    index = {}
    for original_url, slug in url_slug_map.items():
        parsed = urlparse(original_url)
        fragment = parsed.fragment.split("?")[0] if parsed.fragment else ""
        path = parsed.path.rstrip("/") or "/"
        full = normalize_spa_url(original_url)

        index[full] = slug
        index[original_url] = slug
        if fragment:
            index[f"#/{fragment}"] = slug
            index[f"#{fragment}"] = slug
            index[fragment] = slug
            index[f"{path}#/{fragment}"] = slug
            index[f"{path}#{fragment}"] = slug
    return index

def rewrite_links(html, url_slug_map):
    href_index = build_href_index(url_slug_map)

    def local_path(slug):
        return f"../{slug}/index.html"

    def resolve_slug(href):
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "data:")):
            return None
        candidates = [href.strip()]
        route = hash_route_from_href(href)
        if route:
            candidates.extend([route, route.rstrip("/")])
            parts = route[2:].split("/")
            for i in range(len(parts), 0, -1):
                candidates.append("#/" + "/".join(parts[:i]))
        if href.startswith("#"):
            candidates.append(href.split("?")[0])
        else:
            abs_h = abs_url(href, "")
            if abs_h:
                candidates.append(abs_h)
                candidates.append(normalize_spa_url(abs_h))
                frag = urlparse(abs_h).fragment.split("?")[0]
                if frag:
                    candidates.extend([f"#/{frag}", f"#{frag}"])
        for key in candidates:
            if key in href_index:
                return href_index[key]
        return None

    def replace_href(match):
        attr, quote, href = match.group(1), match.group(2), match.group(3)
        slug = resolve_slug(href)
        if slug:
            return f'{attr}={quote}{local_path(slug)}{quote}'
        return match.group(0)

    html = re.sub(r'(href)=(["\'])([^"\']+)\2', replace_href, html)
    return html

STATIC_NAV_STYLE = """
<style id="static-replica-nav">
  /* Keep sidebar/menus usable without Ember JS (hover dropdowns) */
  a[href$="index.html"] { cursor: pointer; }
  a[href$="index.html"]:focus { outline: 2px solid #268ddd; outline-offset: 2px; }
</style>
"""

def collect_links(pg, page_url, base_domain):
    """Collect same-origin links including Ember hash routes (#/home/dashboard)."""
    links = []
    seen = set()
    base_no_hash = page_url.split("#")[0]

    pg.wait_for_timeout(1500)
    for anchor in pg.locator("a[href]").all():
        href = (anchor.get_attribute("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue

        full = abs_url(href, page_url)
        if not full:
            continue

        parsed = urlparse(full)
        if parsed.netloc and parsed.netloc != base_domain:
            continue

        key = normalize_spa_url(full)
        if key not in seen:
            seen.add(key)
            links.append(full if "#" in full else key)

    return links

def is_login_page(pg):
    parsed = urlparse(pg.url)
    if parsed.netloc.lower().startswith("accounts.zoho"):
        return True
    return any(part in parsed.path.lower() for part in ("/signin", "/login", "/sign-in"))

# ── 4. PAGE SAVE ───────────────────────────────────────────────
def save_page(pg, url, slug, is_authenticated=False):
    paths = _paths()
    html_dir = paths["raw_html_dir"] / slug
    shot_dir = paths["screenshots_dir"] / slug
    html_dir.mkdir(parents=True, exist_ok=True)
    shot_dir.mkdir(parents=True, exist_ok=True)

    pg.screenshot(path=str(shot_dir / "index.png"), full_page=True)
    html = pg.content()

    if is_authenticated:
        # Post-auth: view-only static replica — CSS/images from CDN, zero JS
        html = make_assets_absolute(html, url, include_js=False)
        html = remove_base_tag(html)
        html = strip_scripts(html)
        html = re.sub(r"(<head[^>]*>)", rf"\1\n{STATIC_NAV_STYLE}", html, count=1, flags=re.IGNORECASE)
    else:
        # Pre-auth marketing: keep live CDN assets including JS for animations
        html = make_assets_absolute(html, url, include_js=True)

    Path(html_dir / "index.html").write_text(html, encoding="utf-8")
    Path(html_dir / "index.txt").write_text(pg.locator("body").inner_text(), encoding="utf-8")
    Path(html_dir / "index.meta").write_text(url, encoding="utf-8")

# ── 5. AUTHENTICATION ──────────────────────────────────────────
def launch_real_chrome():
    return subprocess.Popen(
        [
            CHROME_MAC_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def ensure_authenticated(p, login_url: str, app_name: str):
    from storage.storage_manager import get_auth_file

    existing = resolve_auth_file(app_name)
    if existing:
        print(f"[*] Found active credentials cache at: '{existing}'")
        print(f"Using auth file: {existing}")
        return existing

    auth_path = get_auth_file(app_name)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    print("\n[*] No auth cache — opening Chrome for manual login...")
    chrome = launch_real_chrome()
    time.sleep(3)
    browser = p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(login_url)

    input(
        "\n[!] Log in inside Chrome until the Books dashboard loads, then press Enter..."
    )
    print(f"Writing auth file: {auth_path}")
    context.storage_state(path=str(auth_path))
    if not auth_path.exists():
        raise RuntimeError(f"Auth file was not created at {auth_path}")
    print(f"Auth file exists after save: True")
    print(f"AUTH FILE CREATED: {auth_path}")
    _release_cdp_browser(browser)
    chrome.terminate()
    return str(auth_path)

def get_post_auth_home(auth_file, post_auth_home: str):
    with open(auth_file, encoding="utf-8") as f:
        data = json.load(f)

    for origin in data.get("origins", []):
        if "books.zoho" in origin.get("origin", ""):
            books_origin = origin["origin"].rstrip("/")
            for item in origin.get("localStorage", []):
                if item.get("name") == "workspaceconf":
                    try:
                        keys = list(json.loads(item["value"]).keys())
                        if keys:
                            return f"{books_origin}/app/{keys[0]}#/home/dashboard"
                    except json.JSONDecodeError:
                        continue
            return f"{books_origin}/app/home"
    return f"{post_auth_home.rstrip('/')}/app/home"

# ── 6. CRAWL ENGINE ────────────────────────────────────────────
def run_spider(context, start_url, base_domain, max_pages, sitemap, url_slug_map, is_authenticated=False):
    queue = [start_url]
    visited = set()

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        norm = normalize_spa_url(url)
        if norm in visited:
            continue
        if urlparse(url).netloc and urlparse(url).netloc != base_domain:
            continue

        visited.add(norm)
        slug = get_slug(url)
        url_slug_map[norm] = slug
        url_slug_map[url] = slug
        print(f"  [{len(visited)}/{max_pages}] Capturing: {url}")

        pg = None
        try:
            pg = context.new_page()
            pg.goto(url, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(2500)

            if is_authenticated and is_login_page(pg):
                app = _paths()["app_name"]
                print(
                    "    ✗ Session expired — landed on login page. "
                    f"Delete storage/apps/{app}/metadata/auth.json and re-run."
                )
                break

            for link in collect_links(pg, pg.url, base_domain):
                link_norm = normalize_spa_url(link)
                if link_norm not in visited and link_norm not in {normalize_spa_url(q) for q in queue}:
                    queue.append(link)

            save_page(pg, url, slug, is_authenticated=is_authenticated)
            sitemap.append({"slug": slug, "url": url, "title": pg.title()})
            save_sitemap(sitemap)
        except Exception as e:
            print(f"    ✗ Capture failed: {e}")
        finally:
            if pg:
                pg.close()

def prepare_context(context):
    context.add_init_script(STEALTH_SCRIPT)
    context.route(
        "**/*",
        lambda route: route.abort()
        if "pagesense.io" in route.request.url
        else route.continue_(),
    )

def crawl_application(
    app_name: str,
    pre_auth_home: str,
    login_url: str,
    post_auth_home: str,
    max_pages_pre_auth: int,
    max_pages_post_auth: int,
) -> dict:
    """Public crawl entrypoint — logic unchanged, paths from storage_manager."""
    from storage.storage_manager import (
        create_app_storage,
        get_logs_dir,
        get_metadata_dir,
        get_raw_html_dir,
        get_screenshots_dir,
    )

    create_app_storage(app_name)
    configure_storage(
        app_name,
        get_raw_html_dir(app_name),
        get_screenshots_dir(app_name),
        get_metadata_dir(app_name),
        get_logs_dir(app_name),
    )

    sitemap = []
    url_slug_map = {}
    raw_html = _paths()["raw_html_dir"]

    with sync_playwright() as p:
        print("  pre-auth marketing pages...")
        browser = p.chromium.launch(headless=True, channel="chrome")
        public_context = browser.new_context(viewport={"width": 1920, "height": 1080})
        run_spider(
            public_context,
            pre_auth_home,
            urlparse(pre_auth_home).netloc,
            max_pages_pre_auth,
            sitemap,
            url_slug_map,
            is_authenticated=False,
        )
        public_context.close()
        browser.close()

        print("  post-auth dashboard...")
        auth_file = ensure_authenticated(p, login_url, app_name)
        post_auth_start = get_post_auth_home(auth_file, post_auth_home)
        base_domain = urlparse(post_auth_start).netloc
        print(f"  starting at: {post_auth_start}")

        browser = p.chromium.launch(headless=False, channel="chrome")
        auth_context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            storage_state=auth_file,
        )
        prepare_context(auth_context)
        run_spider(
            auth_context,
            post_auth_start,
            base_domain,
            max_pages_post_auth,
            sitemap,
            url_slug_map,
            is_authenticated=True,
        )
        auth_context.close()
        browser.close()

    rewritten = 0
    for item in sitemap:
        path = raw_html / item["slug"] / "index.html"
        if not path.exists():
            continue
        html_content = path.read_text(encoding="utf-8")
        new_html = rewrite_links(html_content, url_slug_map)
        if new_html != html_content:
            rewritten += 1
        path.write_text(new_html, encoding="utf-8")

    save_sitemap(sitemap)
    return {"pages_crawled": len(sitemap), "links_rewritten": rewritten}