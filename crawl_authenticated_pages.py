# pyrefly: ignore [missing-import]
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

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
    # Removed "#" from the ignore list so SPA routes are captured
    if not url or url.startswith(("data:", "javascript:", "blob:")):
        return None
    return url if url.startswith("http") else urljoin(base, url)

def get_slug(url):
    parsed = urlparse(url)
    # Combine the main path and the SPA fragment
    raw_path = f"{parsed.path}-{parsed.fragment}"
    
    # Replace slashes and special characters with dashes for a clean filename
    clean_path = re.sub(r'[^a-zA-Z0-9]', '-', raw_path)
    clean_path = re.sub(r'-+', '-', clean_path).strip('-')
    
    return clean_path or "home"

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

def resolve_start_url(auth_file):
    if not auth_file or not Path(auth_file).exists():
        return START_URL

    with open(auth_file, 'r', encoding="utf-8") as f:
        json_data = json.load(f)

    workspace_id = None
    books_origin = None

    for origin in json_data.get("origins", []):
        if "books.zoho" in origin.get("origin", ""):
            books_origin = origin.get("origin").rstrip("/")
            
            for item in origin.get("localStorage", []):
                if item.get("name") == 'workspaceconf':
                    try:
                        workspaceconf = json.loads(item['value'])
                        keys = list(workspaceconf.keys())
                        workspace_id = keys[0] if keys else None
                    except json.JSONDecodeError:
                        continue
                    break
            break

    if books_origin and workspace_id:
        target = f"{books_origin}/app/{workspace_id}#/home/dashboard"
        print(f"[*] Successfully extracted Workspace ID. Target: {target}")
        return target
    
    return books_origin or START_URL

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
        slug = url_slug_map.get(url)
        return f'{attr}={quote}/{slug}{quote}' if slug else match.group(0)

    return re.sub(r'(href)=(["\'])([^"\'#?]+)\2', replace, html)

def collect_links(pg, page_url):
    links = []
    # Force the crawler to wait 2 seconds so the SPA sidebar can fully render
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
            
            # 1. Capture Images (Your existing logic)
            is_image = (
                response.request.resource_type in ("image", "media")
                or content_type.startswith("image/")
            )
            if is_image and is_content_image_url(url):
                captured_images.add(url)
                
            # 2. NEW: Capture JavaScript
            is_js = (
                response.request.resource_type == "script" 
                or "javascript" in content_type 
                or url.endswith(".js")
            )
            # Only download scripts from Zoho, ignore third-party tracking junk
            if is_js and ("zoho" in url or "zohostatic" in url):
                # We pass .mjs just in case they use modern ES modules
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
    
    # 1. Localize assets (but DO NOT strip the <script> tags this time)
    html = localize_assets(pg.content(), url, request)
    
    # 2. THE VACCINE: A script to hijack and mute all API calls
    mute_network_script = """
    <script>
        // 1. Hijack the modern Fetch API
        window.originalFetch = window.fetch;
        window.fetch = async (...args) => {
            console.log("Blocked Fetch API call to:", args[0]);
            // Return a fake, empty success response
            return new Response(JSON.stringify({}), { 
                status: 200, 
                headers: { "Content-Type": "application/json" } 
            });
        };

        // 2. Hijack the older XMLHttpRequest (AJAX)
        window.originalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new window.originalXHR();
            xhr.send = function() {
                console.log("Blocked AJAX call");
                // Force the browser to think the request succeeded instantly
                Object.defineProperty(this, 'readyState', {get: () => 4});
                Object.defineProperty(this, 'status', {get: () => 200});
                Object.defineProperty(this, 'responseText', {get: () => "{}"});
                
                // Trigger the success callbacks
                if (this.onload) this.onload();
                if (this.onreadystatechange) this.onreadystatechange();
            };
            return xhr;
        };
        
        // 3. Hijack WebSockets (used for live notifications)
        window.WebSocket = function() {
            this.send = () => {};
            this.close = () => {};
        };
    </script>
    """
    
    # 3. Inject the mute script right at the top of the HTML document
    html = html.replace("<head>", f"<head>\n{mute_network_script}", 1)
    
    # 4. Save the files
    Path(f"pages/{slug}.html").write_text(html, encoding="utf-8")
    Path(f"pages/{slug}.txt").write_text(pg.locator("body").inner_text(), encoding="utf-8")
    Path(f"pages/{slug}.meta").write_text(url, encoding="utf-8")

def crawl():
    visited, url_slug_map, sitemap = set(), {}, []

    with sync_playwright() as p:
        auth_file = resolve_auth_file() or ensure_authenticated(p)
        start_url = resolve_start_url(auth_file)
        base_domain = urlparse(start_url).netloc
        queue = [start_url]

        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            storage_state=auth_file,
        )
        prepare_context(context)
        request = context.request
        print(f"[*] Loaded session from {auth_file} — crawling as authenticated user")

        while queue and len(sitemap) < MAX_PAGES:
            url = queue.pop(0)
            if url in visited or urlparse(url).netloc != base_domain:
                continue

            visited.add(url)
            slug = get_slug(url)
            url_slug_map[url] = slug
            print(f"[{len(sitemap) + 1}] {url}")

            pg = None
            try:
                pg = context.new_page()
                captured = attach_asset_capture(pg, request)
                pg.goto(url, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(2000)

                if is_login_page(pg):
                    print(f"  ✗ hit login page at {pg.url}")
                    print(f"    Delete {AUTH_FILE} and run again to log in to Zoho Books.")
                    break

                for link in collect_links(pg, url):
                    if link not in visited and link not in queue and urlparse(link).netloc == base_domain:
                        queue.append(link)

                image_index = collect_content_images(pg, url, request, captured)
                Path(f"pages/{slug}.images.json").write_text(json.dumps(image_index, indent=2), encoding="utf-8")
                
                save_page(pg, request, url, slug)
                sitemap.append({"slug": slug, "url": url, "title": pg.title()})

            except Exception as e:
                print(f"  ✗ {e}")
            finally:
                if pg:
                    pg.close()

        context.close()
        browser.close()

    print("\n[*] Rewriting internal links...")
    for item in sitemap:
        path = Path(f"pages/{item['slug']}.html")
        path.write_text(rewrite_links(path.read_text(encoding="utf-8"), url_slug_map), encoding="utf-8")

    Path("pages/sitemap.json").write_text(json.dumps(sitemap, indent=2), encoding="utf-8")
    print(f"\n✅ Done — {len(sitemap)} pages saved successfully!")

if __name__ == "__main__":
    crawl()