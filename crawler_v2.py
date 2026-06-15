"""Playwright crawler — capture pages, screenshots, metadata, and interactions only."""

import json
import os
import re
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from storage.storage_manager import (
    ensure_app_dirs,
    get_auth_file,
    get_crawl_dir,
    get_sitemap_path,
)

_SCRIPTS = json.loads(Path(__file__).with_name("crawler_scripts.json").read_text(encoding="utf-8"))
DISCOVER_JS = _SCRIPTS["discover"]
CLASSIFY_JS = _SCRIPTS["classify"]
DOM_FINGERPRINT_JS = _SCRIPTS["fingerprint"]
EXTRACT_ELEMENT_JS = _SCRIPTS["extract_element"]

CHROME_MAC_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_dev_profile"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STEALTH_SCRIPT = (
    "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    "window.chrome = { runtime: {} };"
)
DEFAULT_MAX_INTERACTIONS = 10
WAIT_AFTER_LOAD_MS = 2000
WAIT_AFTER_CLICK_MS = 800

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
CSS_EXTS = {".css"}
FONT_EXTS = {".woff", ".woff2", ".ttf", ".eot"}
ASSET_EXTS = IMAGE_EXTS | CSS_EXTS | FONT_EXTS


def make_assets_absolute(html: str, page_url: str, include_js: bool = False) -> str:
    """Absolutize CDN asset URLs so CSS/images/fonts load from the saved page."""

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


def remove_base_tag(html: str) -> str:
    return re.sub(r"<base\b[^>]*>", "", html, flags=re.IGNORECASE)


def strip_scripts(html: str) -> str:
    """Remove all JS so app frameworks/API code cannot run or hijack the page."""
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*\bas="script"[^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*rel=["\']modulepreload["\'][^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+=([\"']).*?\1", "", html, flags=re.IGNORECASE)
    return html


def static_snapshot_html(html: str, page_url: str) -> str:
    """Produce a static UI snapshot: absolutized assets, no base tag, no JS."""
    html = make_assets_absolute(html, page_url, include_js=False)
    html = remove_base_tag(html)
    html = strip_scripts(html)
    return html


def abs_url(url: str, base: str) -> str | None:
    if not url or url.startswith(("data:", "javascript:", "blob:", "mailto:", "tel:")):
        return None
    if url.startswith("#"):
        return base.split("#")[0] + url
    return url if url.startswith("http") else urljoin(base, url)


def normalize_url(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    if p.fragment:
        return f"{p.scheme}://{p.netloc}{path}#{p.fragment.split('?')[0]}"
    return f"{p.scheme}://{p.netloc}{path}"


def page_slug(url: str) -> str:
    p = urlparse(url)
    raw = f"{p.path}-{p.fragment}" if p.fragment else p.path
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-")
    return re.sub(r"-+", "-", slug) or "home"


def slugify_label(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "interaction").lower()).strip("-")
    return (s[:48] or "interaction")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _release_browser(browser) -> None:
    (browser.disconnect if hasattr(browser, "disconnect") else browser.close)()


def launch_chrome():
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


def ensure_auth(playwright, login_url: str, app_name: str) -> str:
    auth_path = get_auth_file(app_name)
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[AUTH] Path: {auth_path.resolve()}")
    print(f"[AUTH] Exists: {'yes' if auth_path.exists() else 'no'}")

    if auth_path.exists():
        print("[AUTH] Using existing session")
        return str(auth_path)

    print("[AUTH] No session found — opening Chrome for manual login")
    chrome = launch_chrome()
    time.sleep(3)
    browser = playwright.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(login_url)
    input("\n  Log in, then press Enter...")
    context.storage_state(path=str(auth_path))
    _release_browser(browser)
    chrome.terminate()
    print(f"[AUTH] Session saved to {auth_path}")
    return str(auth_path)


def post_auth_start_url(auth_file: str, fallback: str) -> str:
    data = json.loads(Path(auth_file).read_text(encoding="utf-8"))
    for origin in data.get("origins", []):
        o = origin.get("origin", "")
        if not o:
            continue
        for item in origin.get("localStorage", []):
            if item.get("name") == "workspaceconf":
                try:
                    keys = list(json.loads(item["value"]).keys())
                    if keys:
                        return f"{o.rstrip('/')}/app/{keys[0]}#/home/dashboard"
                except json.JSONDecodeError:
                    pass
        if "books." in o:
            return f"{o.rstrip('/')}/app/home"
    return fallback.rstrip("/")


def is_login_page(page) -> bool:
    p = urlparse(page.url)
    if p.netloc.lower().startswith("accounts."):
        return True
    return any(x in p.path.lower() for x in ("/signin", "/login", "/sign-in"))


def prepare_context(context) -> None:
    context.add_init_script(STEALTH_SCRIPT)


def save_page_capture(page_dir: Path, page, url: str, title: str, page_type: str) -> None:
    page_dir.mkdir(parents=True, exist_ok=True)

    print("[PAGE] Saving HTML")
    html = static_snapshot_html(page.content(), page.url)
    (page_dir / "page.html").write_text(html, encoding="utf-8")

    print("[PAGE] Saving Screenshot")
    page.screenshot(path=str(page_dir / "screenshot.png"), full_page=True)

    print("[PAGE] Saving Metadata")
    (page_dir / "metadata.json").write_text(
        json.dumps(
            {"url": url, "title": title, "captured_at": _now(), "page_type": page_type},
            indent=2,
        ),
        encoding="utf-8",
    )


def save_interaction_capture(
    folder: Path,
    page,
    *,
    source_slug: str,
    source_url: str,
    before_url: str,
    before_title: str,
    item: dict,
    selector: str,
    itype: str,
    crawl_root: Path,
    element: dict | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    element = element or {}

    after_url = page.url
    after_title = page.title()
    rel_folder = str(folder.relative_to(crawl_root))

    print("[PAGE] Saving HTML")
    html = static_snapshot_html(page.content(), page.url)
    (folder / "page.html").write_text(html, encoding="utf-8")

    print("[PAGE] Saving Screenshot")
    page.screenshot(path=str(folder / "screenshot.png"), full_page=True)

    print("[PAGE] Saving Metadata")
    (folder / "metadata.json").write_text(
        json.dumps(
            {
                "triggerLabel": item.get("label", ""),
                "triggerId": item.get("id", ""),
                "triggerClass": item.get("className", ""),
                "selector": selector,
                "interactionType": itype,
                "sourcePage": source_slug,
                "sourceUrl": source_url,
                "beforeUrl": before_url,
                "beforeTitle": before_title,
                "url": after_url,
                "title": after_title,
                "resultPagePath": rel_folder,
                "captured_at": _now(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[PAGE] Saving Relationship")
    outer_html = element.get("outer_html", "")
    trigger = {
        "tag_name": element.get("tag_name", item.get("elementType", "")),
        "text": element.get("text", item.get("label", "")),
        "id": element.get("id", item.get("id", "")),
        "class_name": element.get("class_name", item.get("className", "")),
        "name": element.get("name", ""),
        "role": element.get("role", ""),
        "href": element.get("href", ""),
        "src": element.get("src", ""),
        "data_testid": element.get("data_testid", ""),
        "aria_label": element.get("aria_label", ""),
        # css_selector is reusable on a freshly reopened page (the crawl-time
        # data-crawl-id selector is not), so it is the primary Playwright handle.
        "selector": element.get("css_selector", ""),
        "crawl_selector": selector,
        "xpath": element.get("xpath", ""),
        "outer_html": outer_html,
    }
    relationship = {
        "source_page": source_slug,
        "source_url": source_url,
        "source_title": before_title,
        "trigger": trigger,
        "target": {
            "url": after_url,
            "slug": page_slug(after_url),
            "title": after_title,
        },
        "interaction_type": itype,
        # mandatory: exact DOM element that triggered the action
        "original_element_html": outer_html,
        # backward-compatible flat fields (do not remove)
        "trigger_label": item.get("label", ""),
        "trigger_id": item.get("id", ""),
        "trigger_class": item.get("className", ""),
        "target_url": after_url,
        "target_slug": page_slug(after_url),
        "target_title": after_title,
    }
    (folder / "relationship.json").write_text(
        json.dumps(relationship, indent=2), encoding="utf-8"
    )


def collect_links(page, page_url: str, base_domain: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    page.wait_for_timeout(1000)
    for anchor in page.locator("a[href]").all():
        href = (anchor.get_attribute("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        full = abs_url(href, page_url)
        if not full:
            continue
        p = urlparse(full)
        if p.netloc and p.netloc != base_domain:
            continue
        key = normalize_url(full)
        if key not in seen:
            seen.add(key)
            links.append(full)
    return links


def dom_changed(before: dict, after: dict) -> bool:
    if after.get("overlays", 0) > before.get("overlays", 0):
        return True
    b, a = before.get("len", 0), after.get("len", 0)
    if b == 0:
        return a > 300
    return abs(a - b) >= 300 or (b and abs(a - b) / b >= 0.02)


def crawl_interactions(
    context,
    page_url: str,
    source_slug: str,
    page_dir: Path,
    crawl_root: Path,
    candidates: list[dict],
    max_interactions: int = DEFAULT_MAX_INTERACTIONS,
) -> dict:
    """Replay each discovered trigger in a brand-new tab.

    A fresh tab per interaction guarantees a clean DOM — no overlays, modals, or
    routes accumulated from prior interactions can leak into a capture.
    """
    interactions_dir = page_dir / "interactions"
    interactions_dir.mkdir(parents=True, exist_ok=True)
    (interactions_dir / "discovered.json").write_text(
        json.dumps(candidates, indent=2), encoding="utf-8"
    )

    found = len(candidates)
    saved = 0
    registry: list[dict] = []
    navigations: list[dict] = []
    nav_targets: list[str] = []

    for idx, item in enumerate(candidates[:max_interactions], start=1):
        selector = item.get("selector", "")
        if not selector:
            continue
        # Anchors are navigation — BFS owns them. Never click/capture here.
        if (item.get("elementType") or "").lower() == "a":
            continue

        ipage = None
        try:
            ipage = context.new_page()
            ipage.goto(page_url, wait_until="domcontentloaded", timeout=60000)
            try:
                ipage.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            ipage.wait_for_timeout(WAIT_AFTER_LOAD_MS)
            ipage.evaluate(DISCOVER_JS)

            locator = ipage.locator(selector).first
            if locator.count() == 0 or not locator.is_visible():
                ipage.close()
                continue

            before_url = ipage.url
            before_title = ipage.title()
            before_fp = ipage.evaluate(DOM_FINGERPRINT_JS)

            # Capture the complete trigger element BEFORE clicking — after a
            # navigation/DOM mutation the element may detach and outerHTML is lost.
            try:
                element_meta = locator.evaluate(EXTRACT_ELEMENT_JS)
            except Exception:
                element_meta = {}

            locator.click(timeout=5000)
            ipage.wait_for_timeout(WAIT_AFTER_CLICK_MS)
            try:
                ipage.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            after_fp = ipage.evaluate(DOM_FINGERPRINT_JS)
            # The click changed the URL. This is a NAVIGATION, not a UI state —
            # record the edge (so non-anchor triggers like div/li/role=menuitem
            # become clickable in the clone) and feed the target back to BFS so
            # the destination page itself gets crawled. No interaction capture.
            if normalize_url(ipage.url) != normalize_url(before_url):
                target_url = ipage.url
                target_slug = page_slug(target_url)
                navigations.append(
                    {
                        "label": item.get("label", ""),
                        "tag_name": (element_meta.get("tag_name") or item.get("elementType") or ""),
                        "selector": element_meta.get("css_selector", "") or selector,
                        "target_url": target_url,
                        "target_slug": target_slug,
                        "target_page": f"../{target_slug}/page.html",
                        "trigger": element_meta,
                    }
                )
                nav_targets.append(target_url)
                print(f"    -> navigation: {item.get('label') or selector} → {target_slug}")
                continue
            # No DOM change means no UI state appeared — nothing to capture.
            if not dom_changed(before_fp, after_fp):
                continue
            itype = ipage.evaluate(CLASSIFY_JS)

            folder_name = f"{idx:03d}-{slugify_label(item.get('label', ''))}"
            folder = interactions_dir / folder_name

            save_interaction_capture(
                folder,
                ipage,
                source_slug=source_slug,
                source_url=page_url,
                before_url=before_url,
                before_title=before_title,
                item=item,
                selector=selector,
                itype=itype,
                crawl_root=crawl_root,
                element=element_meta,
            )

            rel_path = f"interactions/{folder_name}"
            registry.append(
                {
                    "label": item.get("label", ""),
                    "selector": selector,
                    "interaction_path": rel_path,
                    "relationship_file": f"{rel_path}/relationship.json",
                }
            )
            saved += 1
            print(f"    + interaction {saved}: {item.get('label') or selector} ({itype})")
        except Exception as exc:
            print(f"[BFS] Interaction save failed ({selector}): {exc}")
            traceback.print_exc()
        finally:
            if ipage:
                try:
                    ipage.close()
                except Exception:
                    pass

    (interactions_dir / "interactions.json").write_text(
        json.dumps(registry, indent=2), encoding="utf-8"
    )
    (page_dir / "navigations.json").write_text(
        json.dumps(navigations, indent=2), encoding="utf-8"
    )
    return {"found": found, "saved": saved, "navigations": navigations, "nav_targets": nav_targets}


def bfs_crawl(
    context,
    start_url: str,
    base_domain: str,
    max_pages: int,
    page_type: str,
    crawl_root: Path,
    app_name: str,
    *,
    max_interactions: int = DEFAULT_MAX_INTERACTIONS,
    check_login: bool = False,
) -> dict:
    queue = [start_url]
    visited: set[str] = set()
    pages = 0
    interactions_found = 0
    interactions_saved = 0
    sitemap: list[dict] = []

    while queue and pages < max_pages:
        url = queue.pop(0)
        norm = normalize_url(url)
        if norm in visited:
            continue
        p = urlparse(url)
        if p.netloc and p.netloc != base_domain:
            continue

        visited.add(norm)
        slug = page_slug(url)

        print(f"[BFS] Queue Size: {len(queue)}")
        print(f"[BFS] Current URL: {url}")
        print(f"[BFS] Pages Visited: {pages}")

        page = None
        candidates: list[dict] = []
        page_title = ""
        try:
            # 1. Open the page on its own fresh tab and let it stabilize.
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(WAIT_AFTER_LOAD_MS)

            if check_login and is_login_page(page):
                print("[AUTH] Session expired — delete metadata/auth.json and re-run")
                page.close()
                break

            # 2. Capture the pristine page BEFORE any interaction touches the DOM.
            page_dir = crawl_root / slug
            page_title = page.title()
            save_page_capture(page_dir, page, url, page_title, page_type)
            pages += 1

            # 3. Discover triggers and links from the untouched page, then close it.
            try:
                candidates = page.evaluate(DISCOVER_JS)
            except Exception as exc:
                print(f"[BFS] Interaction discovery failed: {exc}")
                candidates = []

            links = collect_links(page, page.url, base_domain)
            print(f"[BFS] Links Found: {len(links)}")
            for link in links:
                link_norm = normalize_url(link)
                if link_norm not in visited and link_norm not in {normalize_url(q) for q in queue}:
                    queue.append(link)

            page.close()
            page = None

            # 4. Run each interaction in its own isolated tab.
            ix = crawl_interactions(
                context, url, slug, page_dir, crawl_root, candidates, max_interactions
            )
            interactions_found += ix["found"]
            interactions_saved += ix["saved"]
            print(f"[BFS] Interactions Found: {ix['found']}")
            print(f"[BFS] Interactions Saved: {ix['saved']}")

            # Non-anchor navigations discovered via clicks feed back into BFS so
            # their destination pages get crawled too.
            nav_targets = ix.get("nav_targets", [])
            if nav_targets:
                print(f"[BFS] Navigations Found: {len(nav_targets)}")
            for link in nav_targets:
                link_norm = normalize_url(link)
                if link_norm not in visited and link_norm not in {normalize_url(q) for q in queue}:
                    queue.append(link)

            sitemap.append({"slug": slug, "url": url, "title": page_title, "page_type": page_type})
            get_sitemap_path(app_name).write_text(json.dumps(sitemap, indent=2), encoding="utf-8")

        except Exception as exc:
            print(f"[BFS] Page capture failed: {exc}")
            traceback.print_exc()
            raise
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    if not queue:
        print("[BFS] Queue Exhausted")
    elif pages >= max_pages:
        print("[BFS] Page Limit Reached")

    return {
        "pages": pages,
        "interactions_found": interactions_found,
        "interactions_saved": interactions_saved,
    }


def _run_browser(app_name: str, cfg: dict, *, post_auth: bool) -> dict:
    crawl_root = ensure_app_dirs(app_name)
    max_interactions = cfg.get("max_interactions_per_page", DEFAULT_MAX_INTERACTIONS)
    with sync_playwright() as p:
        auth_file = None
        if post_auth:
            auth_file = ensure_auth(p, cfg["login_url"], app_name)
            start = post_auth_start_url(auth_file, cfg["post_auth_home"])
            max_pages = cfg["max_pages_post_auth"]
            page_type = "post_auth"
            headless = False
            print(f"[BFS] Start URL: {start}")
        else:
            start = cfg["pre_auth_home"]
            max_pages = cfg["max_pages_pre_auth"]
            page_type = "pre_auth"
            headless = True
            print(f"[BFS] Start URL: {start}")

        browser = p.chromium.launch(headless=headless, channel="chrome")
        ctx_kwargs = {"viewport": {"width": 1920, "height": 1080}}
        if auth_file:
            ctx_kwargs["user_agent"] = USER_AGENT
            ctx_kwargs["storage_state"] = auth_file
        context = browser.new_context(**ctx_kwargs)
        prepare_context(context)
        result = bfs_crawl(
            context,
            start,
            urlparse(start).netloc,
            max_pages,
            page_type,
            crawl_root,
            app_name,
            max_interactions=max_interactions,
            check_login=post_auth,
        )
        context.close()
        browser.close()
    return result


def crawl_preauth(app_name: str, cfg: dict) -> dict:
    return _run_browser(app_name, cfg, post_auth=False)


def crawl_postauth(app_name: str, cfg: dict) -> dict:
    return _run_browser(app_name, cfg, post_auth=True)


def crawl_application(app_name: str, cfg: dict) -> dict:
    print("pre-auth crawl...")
    pre = crawl_preauth(app_name, cfg)
    print(f"  {pre['pages']} pages, {pre['interactions_saved']} interactions saved")

    print("post-auth crawl...")
    post = crawl_postauth(app_name, cfg)
    print(f"  {post['pages']} pages, {post['interactions_saved']} interactions saved")

    return {
        "pages_crawled": pre["pages"] + post["pages"],
        "interactions": pre["interactions_saved"] + post["interactions_saved"],
    }
