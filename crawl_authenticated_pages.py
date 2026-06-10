# pyrefly: ignore [missing-import]
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from page_stitch import stitch_pages

# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

# ── config ─────────────────────────────────────────────────────
START_URL = "https://books.zoho.in"
MAX_PAGES = 10
AUTH_FILE = "auth.json"
SESSION_FILE = "session.json"
LOGIN_URL = (
    "https://accounts.zoho.com/signin?servicename=ZohoBooks"
    "&signupurl=https://www.zoho.com%2fin%2fbooks%2fsignup%2f"
)
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
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
CSS_EXTS = {".css"}
SKIP_IMAGE_URL_PARTS = (
    "books_logo", "sprite", "cssicons", "svgicons", "favicon"
)
CONTENT_IMAGE_PARTS = ("onboarding/", "/images/", "photo", "avatar", "attachment", "upload")
# ───────────────────────────────────────────────────────────────

os.makedirs("pages", exist_ok=True)
os.makedirs("assets/images", exist_ok=True)
os.makedirs("assets/css", exist_ok=True)
os.makedirs("assets/js", exist_ok=True)

def abs_url(url, base):
    if not url or url.startswith(("data:", "javascript:", "blob:")):
        return None
    return url if url.startswith("http") else urljoin(base, url)

def get_slug(url):
    parsed = urlparse(url)
    fragment = parsed.fragment.strip("/")
    if fragment:
        clean = re.sub(r"[^a-zA-Z0-9]", "-", fragment)
        clean = re.sub(r"-+", "-", clean).strip("-")
        return clean or "home"
    if "/app/" in parsed.path:
        return "home"
    raw_path = parsed.path.strip("/")
    clean = re.sub(r"[^a-zA-Z0-9]", "-", raw_path)
    clean = re.sub(r"-+", "-", clean).strip("-")
    return clean or "home"

def resolve_auth_file():
    for name in (AUTH_FILE, SESSION_FILE):
        if Path(name).exists():
            return name
    return None

def launch_real_chrome():
    print("[*] Launching Google Chrome for secure manual login...")
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

def ensure_authenticated(p, auth_file=AUTH_FILE):
    if Path(auth_file).exists():
        print(f"[*] Using saved auth from {auth_file}")
        return auth_file

    print(f"[*] No {auth_file} found — starting manual login...")
    chrome = launch_real_chrome()
    time.sleep(3)

    browser = p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()

    print(f"[*] Navigating to {LOGIN_URL}")
    page.goto(LOGIN_URL)
    input(
        "\n[!] Log in manually in Chrome, then wait for the Books dashboard to load.\n"
        "[!] Press Enter here when you are fully logged in..."
    )

    context.storage_state(path=auth_file)
    print(f"[*] Auth saved to {auth_file}")
    browser.disconnect()
    chrome.terminate()
    return auth_file

def get_workspace_context(auth_file):
    """Books workspace is resolved from the live app URL after login redirect."""
    ctx = {"books_origin": START_URL.rstrip("/"), "workspace_id": None, "app_base": None, "start_url": START_URL}
    if not auth_file or not Path(auth_file).exists():
        return ctx

    with open(auth_file, encoding="utf-8") as f:
        json_data = json.load(f)

    for origin in json_data.get("origins", []):
        if "books.zoho" in origin.get("origin", ""):
            ctx["books_origin"] = origin.get("origin", "").rstrip("/")
            break

    return ctx


def resolve_app_base_from_browser(pg, ctx):
    match = re.search(r"/app/(\d+)", pg.url)
    if not match:
        return ctx

    workspace_id = match.group(1)
    ctx["workspace_id"] = workspace_id
    ctx["app_base"] = f"{ctx['books_origin']}/app/{workspace_id}"
    ctx["start_url"] = f"{ctx['app_base']}#/home/dashboard"
    print(f"[*] Resolved app base from browser: {ctx['app_base']}")
    return ctx


def bootstrap_books_app(pg, ctx):
    pg.goto(ctx["books_origin"], wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4000)
    resolve_app_base_from_browser(pg, ctx)

    if not ctx.get("app_base"):
        pg.goto(f"{ctx['books_origin']}/home", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(4000)
        resolve_app_base_from_browser(pg, ctx)

    if not ctx.get("app_base"):
        raise RuntimeError(
            "Could not resolve Books workspace URL. Delete auth.json and log in again."
        )

    if "/app/" not in pg.url:
        pg.goto(ctx["app_base"], wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3000)

    pg.wait_for_selector("a.nav-link", timeout=60000)
    pg.wait_for_timeout(1500)
    return ctx


def resolve_start_url(auth_file):
    return get_workspace_context(auth_file)["start_url"]


def normalize_crawl_url(url, ctx):
    parsed = urlparse(url)
    if parsed.netloc and ctx["books_origin"] not in parsed.netloc:
        return url

    fragment = parsed.fragment.strip("/")
    if ctx.get("app_base"):
        if fragment:
            return f"{ctx['app_base']}#/{fragment}"
        if "/app/" in parsed.path:
            return url
        return ctx["start_url"]

    if fragment:
        return f"{ctx['books_origin']}#/{fragment}"
    return url


def expand_sidebar_sections(pg):
    for btn in pg.locator(".accordion-button.collapsed").all():
        try:
            btn.click(timeout=2000)
            pg.wait_for_timeout(200)
        except Exception:
            pass


def click_sidebar_link(pg, fragment):
    href = f"#/{fragment.strip('/')}"
    expand_sidebar_sections(pg)
    link = pg.locator(f'a.nav-link[href="{href}"], a[href="{href}"]').first
    try:
        if link.count() and link.is_visible():
            link.click(timeout=5000)
            pg.wait_for_timeout(3000)
            return True
    except Exception:
        pass
    return False


def navigate_to_route(pg, url, ctx):
    target = normalize_crawl_url(url, ctx)
    parsed = urlparse(target)
    fragment = parsed.fragment.strip("/")

    if not ctx.get("app_base"):
        pg.goto(ctx["books_origin"], wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3000)
        resolve_app_base_from_browser(pg, ctx)

    if not ctx.get("app_base"):
        raise RuntimeError("Books app URL not resolved — run bootstrap or re-login.")

    if "/app/" not in pg.url:
        pg.goto(ctx["app_base"], wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_selector("a.nav-link", timeout=30000)
        pg.wait_for_timeout(2000)

    if not fragment or fragment in ("home", "home/dashboard"):
        pg.goto(f"{ctx['app_base']}#/home/dashboard", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(2500)
        return

    pg.evaluate("(hash) => { window.location.hash = hash; }", f"#/{fragment}")
    pg.wait_for_timeout(1500)

    try:
        pg.wait_for_function(
            """(frag) => {
                const current = window.location.hash.replace(/^#\\/?/, '').split('/')[0];
                const want = frag.split('/')[0];
                return current === want;
            }""",
            fragment,
            timeout=15000,
        )
    except Exception:
        pass

    try:
        pg.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    pg.wait_for_timeout(2500)

    body = pg.locator("body").inner_text()[:1000]
    route_root = fragment.split("/")[0]
    if route_root not in ("home", "") and "Hello, gauri" in body and "Dashboard" in body:
        print(f"  ↻ hash nav stuck on dashboard — clicking sidebar for #/{fragment}")
        click_sidebar_link(pg, fragment)

def is_login_page(pg):
    parsed = urlparse(pg.url)
    if parsed.netloc.lower().startswith("accounts.zoho"):
        return True
    return any(part in parsed.path.lower() for part in ("/signin", "/login", "/sign-in"))

def prepare_context(context):
    context.add_init_script(STEALTH_SCRIPT)
    context.route("**/*", lambda route: route.abort() if "pagesense.io" in route.request.url else route.continue_())

def save_asset(url, folder, extensions, request):
    try:
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in extensions:
            return None
        filepath = os.path.join(folder, hashlib.md5(url.encode()).hexdigest()[:10] + ext)
        if not os.path.exists(filepath):
            response = request.get(url, timeout=15000)
            if response.ok:
                with open(filepath, "wb") as f:
                    f.write(response.body())
        return filepath
    except Exception:
        return None

def localize_assets(html, page_url, request):
    def replace(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        full = abs_url(url, page_url)
        if not full:
            return match.group(0)
        ext = os.path.splitext(urlparse(full).path)[1].lower()
        if ext in CSS_EXTS:
            local = save_asset(full, "assets/css", CSS_EXTS, request)
        else:
            return match.group(0)
        return f'{attr}={quote}../{local}{quote}' if local else match.group(0)
    return re.sub(r'(src|href)=(["\'])([^"\']+)\2', replace, html)

def rewrite_links(html, url_slug_map):
    def replace(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        for original_url, slug in url_slug_map.items():
            if url in original_url:
                return f'{attr}={quote}{slug}.html{quote}'
        return match.group(0)
    return re.sub(r'(href|src)=(["\'])([^"\']+)\2', replace, html)

def collect_links(pg, page_url):
    links = []
    pg.wait_for_timeout(2000)
    for anchor in pg.locator("a").all():
        full = abs_url(anchor.get_attribute("href"), page_url)
        if full:
            links.append(full)
    return links

def is_content_image_url(url):
    lower = url.lower()
    if any(part in lower for part in SKIP_IMAGE_URL_PARTS):
        return False
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext not in IMAGE_EXTS:
        return False
    if ext in {".svg", ".gif"}:
        return any(part in lower for part in CONTENT_IMAGE_PARTS)
    return ext in {".png", ".jpg", ".jpeg", ".webp"}

def attach_asset_capture(page, request):
    captured_images = set()
    def on_response(response):
        try:
            url = response.url
            content_type = response.headers.get("content-type", "").lower()
            is_image = (
                response.request.resource_type in ("image", "media")
                or content_type.startswith("image/")
            )
            if is_image and is_content_image_url(url):
                captured_images.add(url)
            is_js = (
                response.request.resource_type == "script"
                or "javascript" in content_type
                or url.endswith(".js")
            )
            if is_js and ("zoho" in url or "zohostatic" in url):
                save_asset(url, "assets/js", {".js", ".mjs"}, request)
        except Exception:
            pass
    page.on("response", on_response)
    return captured_images

def collect_content_images(pg, page_url, request, network_urls):
    urls = set(network_urls)
    for img in pg.locator("img").all():
        src = abs_url(img.get_attribute("src") or img.get_attribute("data-src"), page_url)
        if src and is_content_image_url(src):
            urls.add(src)
    images = []
    for url in sorted(urls):
        local = save_asset(url, "assets/images", IMAGE_EXTS, request)
        if local:
            images.append({"src": url, "local_path": f"../{local}"})
    return images


def save_page(pg, request, url, slug):
    pg.screenshot(path=f"pages/{slug}.png", full_page=True)
    html = localize_assets(pg.content(), url, request)
    Path(f"pages/{slug}.html").write_text(html, encoding="utf-8")
    Path(f"pages/{slug}.txt").write_text(pg.locator("body").inner_text(), encoding="utf-8")
    Path(f"pages/{slug}.meta").write_text(url, encoding="utf-8")


def crawl():
    visited, url_slug_map, sitemap, saved_slugs = set(), {}, [], set()

    with sync_playwright() as p:
        auth_file = resolve_auth_file() or ensure_authenticated(p)
        ctx = get_workspace_context(auth_file)
        base_domain = urlparse(ctx["books_origin"]).netloc

        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            storage_state=auth_file,
        )
        prepare_context(context)
        request = context.request
        print(f"[*] Loaded session from {auth_file} — crawling as authenticated user")

        pg = context.new_page()
        captured = attach_asset_capture(pg, request)
        bootstrap_books_app(pg, ctx)
        start_url = ctx["start_url"]
        queue = [start_url]

        while queue and len(sitemap) < MAX_PAGES:
            raw_url = queue.pop(0)
            url = normalize_crawl_url(raw_url, ctx)
            if url in visited or urlparse(url).netloc != base_domain:
                continue

            visited.add(url)
            slug = get_slug(url)
            if slug in saved_slugs:
                continue

            url_slug_map[url] = slug
            url_slug_map[raw_url] = slug
            print(f"[{len(sitemap) + 1}] {url}")

            try:
                navigate_to_route(pg, url, ctx)

                if is_login_page(pg):
                    print(f"  ✗ hit login page at {pg.url}")
                    print(f"    Delete {AUTH_FILE} and run again to log in to Zoho Books.")
                    break

                for link in collect_links(pg, pg.url):
                    norm = normalize_crawl_url(link, ctx)
                    if not norm or "/app/" not in norm:
                        continue
                    if norm not in visited and norm not in queue and urlparse(norm).netloc == base_domain:
                        queue.append(norm)

                image_index = collect_content_images(pg, pg.url, request, captured)
                Path(f"pages/{slug}.images.json").write_text(json.dumps(image_index, indent=2), encoding="utf-8")

                save_page(pg, request, url, slug)
                saved_slugs.add(slug)
                sitemap.append({"slug": slug, "url": url, "title": pg.title()})

            except Exception as e:
                print(f"  ✗ {e}")

        pg.close()
        context.close()
        browser.close()

    print("\n[*] Rewriting internal links...")
    for item in sitemap:
        path = Path(f"pages/{item['slug']}.html")
        path.write_text(rewrite_links(path.read_text(encoding="utf-8"), url_slug_map), encoding="utf-8")

    Path("pages/sitemap.json").write_text(json.dumps(sitemap, indent=2), encoding="utf-8")

    print("\n[*] Stitching pages for offline navigation...")
    stitch_pages()

    print(f"\n✅ Done — {len(sitemap)} pages saved successfully!")
    print("   Serve with: python3 -m http.server 8080")
    print("   Then open:  http://localhost:8080/pages/home.html")


if __name__ == "__main__":
    crawl()