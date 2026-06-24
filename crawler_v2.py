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

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

from storage.storage_manager import (
    ensure_app_dirs,
    get_auth_file,
    get_crawl_checkpoint_path,
    get_crawl_dir,
    get_sitemap_path,
)

_SCRIPTS = json.loads(Path(__file__).with_name("crawler_scripts.json").read_text(encoding="utf-8"))
DISCOVER_JS = _SCRIPTS["discover"]
CLASSIFY_JS = _SCRIPTS["classify"]
DOM_FINGERPRINT_JS = _SCRIPTS["fingerprint"]
EXTRACT_ELEMENT_JS = _SCRIPTS["extract_element"]
ACTIVE_TABS_JS = _SCRIPTS["active_tabs"]
ACTIVE_TAB_PANEL_JS = _SCRIPTS["active_tab_panel"]
SIDEBAR_LINKS_JS = _SCRIPTS["sidebar_links"]

MUTATION_OBSERVER_SETUP_JS = """() => {
  window.__stitch_muts = [];
  window.__stitch_mo = new MutationObserver(function(recs) {
    recs.forEach(function(r) {
      if (r.addedNodes.length) {
        r.addedNodes.forEach(function(n) {
          if (n.nodeType !== 1) return;
          window.__stitch_muts.push({
            kind: 'added',
            tag: n.tagName,
            id: n.id || '',
            cls: (n.className && typeof n.className === 'string')
                 ? n.className.split(' ').slice(0,3).join(' ') : '',
            parentId: n.parentElement ? n.parentElement.id : '',
            parentTag: n.parentElement ? n.parentElement.tagName : '',
          });
        });
      }
      if (r.type === 'attributes') {
        window.__stitch_muts.push({
          kind: 'attr', attr: r.attributeName,
          tag: r.target.tagName, id: r.target.id || '',
          cls: (r.target.className && typeof r.target.className === 'string')
               ? r.target.className.split(' ').slice(0,3).join(' ') : '',
        });
      }
    });
  });
  window.__stitch_mo.observe(document.body, {
    childList: true, subtree: true,
    attributes: true, attributeFilter: ['class','style','aria-hidden','hidden']
  });
}"""

MUTATION_OBSERVER_READ_JS = """() => {
  if (window.__stitch_mo) window.__stitch_mo.disconnect();
  return window.__stitch_muts || [];
}"""

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
NETWORKIDLE_TIMEOUT_MS = 8000

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


_WAIT_FOR_STYLED_COMPONENTS_JS = """
() => new Promise(resolve => {
  var deadline = Date.now() + 15000;
  function cssomStats() {
    var total = 0;
    var styled = 0;
    Array.from(document.styleSheets).forEach(function(sheet) {
      var rules;
      try { rules = sheet.cssRules || sheet.rules; } catch (e) { return; }
      if (!rules) return;
      Array.from(rules).forEach(function(rule) {
        var text = rule.cssText || '';
        total += text.length;
        if (/\\.sc-|Styled[A-Z]|__[A-Za-z]{4,}/.test(text)) styled += 1;
      });
    });
    return { total: total, styled: styled };
  }
  function check() {
    var stats = cssomStats();
    // styled-components rules live in the CSSOM, not <style>.textContent.
    if (stats.styled >= 80 || stats.total >= 120000 || Date.now() > deadline) {
      resolve(stats);
      return;
    }
    setTimeout(check, 300);
  }
  check();
})
"""

_EXTRACT_HUBSPOT_CSS_JS = """
() => {
  var parts = [];
  var seen = new Set();
  function add(text) {
    text = (text || '').trim();
    if (!text || seen.has(text)) return;
    seen.add(text);
    parts.push(text);
  }
  Array.from(document.styleSheets).forEach(function(sheet) {
    var rules;
    try { rules = sheet.cssRules || sheet.rules; } catch (e) { return; }
    if (!rules) return;
    Array.from(rules).forEach(function(rule) { add(rule.cssText); });
  });
  Array.from(document.querySelectorAll('style')).forEach(function(el) {
    add(el.textContent || '');
  });
  return parts.join('\\n');
}
"""


def _inline_hubspot_styled_css(page, html: str) -> str:
    """Persist all JS-injected CSS before scripts are stripped.

    HubSpot styled-components writes rules into the CSSOM via insertRule, so
    <style data-styled> tags often have empty textContent. We wait until the
    live page has enough styled-component rules, then serialize document.styleSheets
    (plus any inline <style> text) into a single captured block.
    """
    try:
        page.evaluate(_WAIT_FOR_STYLED_COMPONENTS_JS)
        css = page.evaluate(_EXTRACT_HUBSPOT_CSS_JS) or ""
    except Exception:
        return html
    if not css.strip():
        return html
    block = f'<style id="hs-captured-styles">\n{css}\n</style>'
    if "</head>" in html:
        return html.replace("</head>", block + "\n</head>", 1)
    return html + block


_BAKE_SELECTORS = [
    "#hs-global-toolbar",
    "#hs-global-toolbar *",
    "#hs-nav-v4",
    "#hs-nav-v4 > *",
    "[data-test-id='nav-primary']",
    "[data-test-id='nav-primary'] *",
    ".private-page__outer",
    ".copilot-app-container",
    "[data-test-id='crm-visualization-toolbar']",
    "[data-test-id='crm-visualization-toolbar'] *",
    "[data-observer-type='COLUMN']",
    "[data-test-id^='cell-']",
    "[data-test-id='AvatarDisplay-avatarContent']",
    "header",
    "nav",
]

_BAKE_PROPS = [
    "background-color", "color", "font-family", "font-size", "font-weight",
    "line-height", "border", "border-radius", "padding", "margin",
    "display", "flex", "flex-direction", "flex-shrink", "align-items",
    "justify-content", "gap", "width", "height", "min-width", "max-width",
    "min-height", "max-height", "overflow", "position", "top", "left",
    "right", "bottom", "box-shadow", "opacity", "white-space",
]

_BAKE_JS = (
    "(function(selectors, props) {"
    "  var seen = new Set();"
    "  selectors.forEach(function(sel) {"
    "    var els = document.querySelectorAll(sel);"
    "    els.forEach(function(el) {"
    "      if (seen.has(el)) return;"
    "      seen.add(el);"
    "      var cs = window.getComputedStyle(el);"
    "      var parts = [];"
    "      props.forEach(function(p) {"
    "        var v = cs.getPropertyValue(p);"
    "        if (v && v !== 'initial' && v !== 'inherit' && v !== 'auto'"
    "            && v !== 'normal' && v !== 'none' && v !== '') {"
    "          parts.push(p + ':' + v);"
    "        }"
    "      });"
    "      if (parts.length) {"
    "        var existing = el.getAttribute('style') || '';"
    "        el.setAttribute('style', existing + ';' + parts.join(';'));"
    "      }"
    "    });"
    "  });"
    "})(['" + "','".join(_BAKE_SELECTORS) + "'], ['" + "','".join(_BAKE_PROPS) + "'])"
)


_HUBSPOT_LOADING_REMOVE_JS = """() => {
  var sels = [
    '[data-test-id="loading-spinner"]',
    '.private-loading-page',
    '.private-spinner-container',
    '.loading-page-wrapper',
    '[aria-label="Loading"]',
    '[data-loading="true"]',
    '.UIOverlay--blocker',
    '.UIModalDialog--loading',
    '.UIPlaceholderBubble__Placeholder-mfCgX',
  ];
  sels.forEach(function(s) {
    document.querySelectorAll(s).forEach(function(el) { el.remove(); });
  });
}"""


def _strip_hubspot_loading_elements(page, page_url: str) -> None:
    """Remove HubSpot loading spinners and skeleton screens from the live DOM.

    Called before page.content() so the static snapshot never contains
    loading states that would never resolve in the static clone (since
    the API calls they wait on are never made).
    """
    if "hubspot" not in page_url.lower():
        return
    try:
        page.evaluate(_HUBSPOT_LOADING_REMOVE_JS)
    except Exception:
        pass


def _bake_hubspot_computed_styles_in_page(page, page_url: str) -> None:
    """Inline computed styles on key HubSpot structural elements.

    Runs JS against the live DOM to read window.getComputedStyle for nav/toolbar
    elements and write critical visual properties directly onto el.style so the
    static snapshot retains the rendered appearance even after hashed class names
    become stale or missing.

    Must be called BEFORE page.content() so the mutations are included in the
    captured HTML.
    """
    if "hubspot" not in page_url.lower():
        return
    try:
        page.evaluate(_BAKE_JS)
    except Exception:
        pass


def _make_css_urls_absolute(html: str, page_url: str) -> str:
    """Absolutize url() references inside <style> blocks.

    make_assets_absolute() only rewrites src= and href= HTML attributes.
    @font-face src, background-image, and other url() calls inside <style>
    text are untouched by that pass. This function handles them so that
    fonts and images referenced in inline CSS are not left as broken
    relative paths in the static snapshot.
    """
    def _fix_url(um: re.Match) -> str:
        raw = um.group(1).strip()
        u = raw.strip("'\"")
        if not u or u.startswith(("http", "data:", "#", "blob:")):
            return um.group(0)
        return f"url({urljoin(page_url, u)})"

    def _fix_style_block(m: re.Match) -> str:
        return re.sub(r"url\(([^)]*)\)", _fix_url, m.group(0))

    return re.sub(
        r"<style\b[^>]*>[\s\S]*?</style>",
        _fix_style_block,
        html,
        flags=re.IGNORECASE,
    )


def static_snapshot_html(html: str, page_url: str, *, page=None) -> str:
    """Produce a static UI snapshot: absolutized assets, no base tag, no JS.

    Pass page= (the live Playwright page object) to capture any CSS that was
    injected by JavaScript (e.g. HubSpot's styled-components) before scripts
    are stripped from the snapshot.
    """
    if page is not None and "hubspot" in page_url.lower():
        html = _inline_hubspot_styled_css(page, html)
    html = make_assets_absolute(html, page_url, include_js=False)
    html = _make_css_urls_absolute(html, page_url)
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
        # HubSpot: no workspaceconf localStorage — use the configured post_auth_home.
        if "hubspot.com" in o:
            return fallback.rstrip("/")
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


def _should_skip_url(url: str, patterns: list[str]) -> bool:
    return bool(patterns) and any(p in url for p in patterns)


def _route_fragment(url: str) -> str:
    return urlparse(url).fragment.split("?")[0].rstrip("/")


def _is_bare_home(url: str, *, hash_routes: bool = True) -> bool:
    if hash_routes:
        frag = _route_fragment(url)
        return frag in ("home", "/home", "")
    # Path-based SPA (e.g. HubSpot): only the literal root or /login counts as home.
    path = urlparse(url).path.rstrip("/") or "/"
    return path in ("/", "/login")


def _is_redundant_route(url: str, *, hash_routes: bool = True) -> bool:
    """Skip routes that duplicate a better page already in the crawl plan."""
    if _is_bare_home(url, hash_routes=hash_routes):
        return True
    route = _route_fragment(url) if hash_routes else urlparse(url).path
    # Edit sub-routes are almost always the same form as /new.
    if re.search(r"/(edit|productedit)(/|$)", route):
        return True
    return False


def _visited_global_count(visited: set[str], pattern: str, exclude: str = "") -> int:
    count = 0
    for norm in visited:
        if pattern not in norm:
            continue
        if exclude and exclude in norm:
            continue
        count += 1
    return count


def _prune_queues(
    sidebar_queue: list[tuple[str, int]],
    deferred_queue: list[tuple[str, int]],
    *,
    visited: set[str],
    skip_patterns: list[str],
    seed_norms: set[str],
    global_link_limits: list[dict] | None,
    hash_routes: bool = True,
) -> tuple[int, int]:
    """Drop duplicate/redundant URLs already satisfied or over global caps."""

    def _keep(url: str) -> bool:
        norm = normalize_url(url)
        if norm in visited:
            return False
        if _is_redundant_route(url, hash_routes=hash_routes) and norm not in seed_norms:
            return False
        if _should_skip_url(url, skip_patterns) and norm not in seed_norms:
            return False
        for lim in global_link_limits or []:
            pat = lim.get("pattern", "")
            if pat not in url:
                continue
            excl = lim.get("exclude_pattern", "")
            if excl and excl in url:
                continue
            if _visited_global_count(visited, pat, excl) >= lim.get("max_total", 999):
                return False
            break
        return True

    before = len(sidebar_queue) + len(deferred_queue)
    sidebar_queue[:] = [(u, d) for u, d in sidebar_queue if _keep(u)]
    deferred_queue[:] = [(u, d) for u, d in deferred_queue if _keep(u)]
    return before, len(sidebar_queue) + len(deferred_queue)


def _should_enqueue_link(
    link: str,
    source_url: str,
    *,
    skip_patterns: list[str],
    seed_norms: set[str],
    list_detail_limits: list[dict],
    link_counters: dict[str, dict[str, int]],
    cross_page_rules: list[dict] | None = None,
    global_link_limits: list[dict] | None = None,
    hash_routes: bool = True,
) -> bool:
    """Filter BFS links: skip patterns, cap list→detail fan-out, block redundant hops."""
    link_norm = normalize_url(link)
    if _is_redundant_route(link, hash_routes=hash_routes) and link_norm not in seed_norms:
        return False
    if _should_skip_url(link, skip_patterns) and link_norm not in seed_norms:
        return False

    for rule in cross_page_rules or []:
        link_pat = rule.get("link_pattern", "")
        source_pat = rule.get("source_pattern", "")
        if link_pat not in link or source_pat not in source_url:
            continue
        source_allow = rule.get("source_allow", "")
        source_allow_regex = rule.get("source_allow_regex", "")
        if source_allow_regex:
            if not re.search(source_allow_regex, source_url):
                return False
        elif source_allow and source_allow not in source_url:
            return False

    global_counts = link_counters.setdefault("__global__", {})
    for lim in global_link_limits or []:
        pat = lim.get("pattern", "")
        if pat not in link:
            continue
        excl = lim.get("exclude_pattern")
        if excl and excl in link:
            continue
        max_n = lim.get("max_total", 3)
        count = global_counts.get(pat, 0)
        if count >= max_n:
            return False
        global_counts[pat] = count + 1
        break

    src_key = normalize_url(source_url)
    page_counts = link_counters.setdefault(src_key, {})
    for lim in list_detail_limits or []:
        pat = lim.get("pattern", "")
        if pat not in link:
            continue
        excl = lim.get("exclude_pattern")
        if excl and excl in link:
            continue
        max_n = lim.get("max_from_page", 3)
        count = page_counts.get(pat, 0)
        if count >= max_n:
            return False
        page_counts[pat] = count + 1
        break

    return True


def _stabilize_page(
    page,
    *,
    wait_ms: int,
    use_networkidle: bool = False,
    networkidle_ms: int = NETWORKIDLE_TIMEOUT_MS,
) -> None:
    if use_networkidle:
        try:
            page.wait_for_load_state("networkidle", timeout=networkidle_ms)
        except Exception:
            pass
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)


def _goto_clean(page, url: str, *, use_networkidle: bool, wait_ms: int) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    _stabilize_page(page, wait_ms=wait_ms, use_networkidle=use_networkidle)


def save_page_capture(
    page_dir: Path,
    page,
    url: str,
    title: str,
    page_type: str,
    *,
    skip_screenshots: bool = False,
) -> None:
    page_dir.mkdir(parents=True, exist_ok=True)

    print("[PAGE] Saving HTML")
    _strip_hubspot_loading_elements(page, page.url)
    _bake_hubspot_computed_styles_in_page(page, page.url)
    html = static_snapshot_html(page.content(), page.url, page=page)
    (page_dir / "page.html").write_text(html, encoding="utf-8")

    print("[PAGE] Saving Screenshot")
    if not skip_screenshots:
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
    tab_panel: dict | None = None,
    skip_screenshots: bool = False,
    mutations: list | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    element = element or {}

    after_url = page.url
    after_title = page.title()
    rel_folder = str(folder.relative_to(crawl_root))

    print("[PAGE] Saving HTML")
    _strip_hubspot_loading_elements(page, page.url)
    _bake_hubspot_computed_styles_in_page(page, page.url)
    html = static_snapshot_html(page.content(), page.url, page=page)
    (folder / "page.html").write_text(html, encoding="utf-8")

    print("[PAGE] Saving Screenshot")
    if not skip_screenshots:
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
    if tab_panel and tab_panel.get("selector"):
        relationship["tab_content"] = {
            "selector": tab_panel["selector"],
            "file": "tab-content.html",
        }
    (folder / "relationship.json").write_text(
        json.dumps(relationship, indent=2), encoding="utf-8"
    )
    tab_html = (tab_panel.get("innerHTML") or tab_panel.get("outerHTML") or "") if tab_panel else ""
    if tab_html:
        (folder / "tab-content.html").write_text(tab_html, encoding="utf-8")
    if mutations:
        (folder / "mutations.json").write_text(
            json.dumps(mutations, indent=2), encoding="utf-8"
        )


def build_seed_urls(start_url: str, patterns: list[str], *, hash_routes: bool = True) -> list[str]:
    """Turn route patterns into full app URLs queued at crawl start.

    When hash_routes=True (Zoho-style), patterns are treated as #/fragment routes.
    When hash_routes=False (HubSpot-style), patterns that start with "/" are used
    as absolute paths directly on the origin.
    """
    if not patterns:
        return []
    p = urlparse(start_url)
    base = f"{p.scheme}://{p.netloc}"
    m = re.search(r"(/app/\d+)", start_url)
    app_prefix = m.group(1) if m else ""
    seeds: list[str] = []
    seen: set[str] = set()
    for raw in patterns:
        if hash_routes or raw.startswith("#"):
            route = raw if raw.startswith("#") else "#" + raw.lstrip("/")
            url = f"{base}{app_prefix}{route}" if app_prefix else f"{base}{route}"
        else:
            # Path-based routing: use the pattern as an absolute path on the origin.
            path = raw if raw.startswith("/") else "/" + raw
            url = f"{base}{path}"
        key = normalize_url(url)
        if key not in seen:
            seen.add(key)
            seeds.append(url)
    return seeds


def _build_seed_norms(start_url: str, seed_patterns: list[str] | None, *, hash_routes: bool = True) -> set[str]:
    norms = {normalize_url(start_url)}
    for seed_url in build_seed_urls(start_url, seed_patterns or [], hash_routes=hash_routes):
        norms.add(normalize_url(seed_url))
    return norms


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


def collect_sidebar_links(page, page_url: str, base_domain: str) -> list[dict]:
    """Left-nav module links in DOM order (skips quick-add /new shortcuts)."""
    try:
        raw = page.evaluate(SIDEBAR_LINKS_JS) or []
    except Exception:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        href = (item.get("href") or "").strip()
        full = abs_url(href, page_url)
        if not full:
            continue
        p = urlparse(full)
        if p.netloc and p.netloc != base_domain:
            continue
        key = normalize_url(full)
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": full, "label": (item.get("label") or "").strip()})
    return out


_LOGIN_PAGE_MARKERS = (
    "<title>HubSpot Login",
    "data-application-name=\"LoginUI\"",
    "data-error-type=\"SESSION_TIMED_OUT\"",
    "Your authentication has expired",
    "Sign in to HubSpot",
)


def _is_login_html(html: str) -> bool:
    """Return True if the saved HTML is actually a login/auth redirect page."""
    snippet = html[:4000]
    return any(m in snippet for m in _LOGIN_PAGE_MARKERS)


def _page_on_disk(crawl_root: Path, url: str) -> bool:
    p = crawl_root / page_slug(url) / "page.html"
    if not p.is_file():
        return False
    # Do not treat a login-redirect capture as a real saved page.
    try:
        if _is_login_html(p.read_text(encoding="utf-8", errors="ignore")[:4000]):
            return False
    except Exception:
        pass
    return True


def _visited_from_disk(crawl_root: Path) -> set[str]:
    norms: set[str] = set()
    if not crawl_root.is_dir():
        return norms
    for page_dir in crawl_root.iterdir():
        meta_path = page_dir / "metadata.json"
        html_path = page_dir / "page.html"
        if not html_path.is_file() or not meta_path.is_file():
            continue
        try:
            # Skip pages that are actually login redirects.
            if _is_login_html(html_path.read_text(encoding="utf-8", errors="ignore")[:4000]):
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            url = meta.get("url", "")
            if url:
                norms.add(normalize_url(url))
        except Exception:
            pass
    return norms


def _load_checkpoint(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_checkpoint(
    path: Path,
    *,
    visited: set[str],
    sidebar_queue: list[tuple[str, int]],
    deferred_queue: list[tuple[str, int]],
    pages: int,
    sitemap: list[dict],
    link_counters: dict,
    sidebar_discovered: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": _now(),
                "visited": sorted(visited),
                "sidebar_queue": [{"url": u, "depth": d} for u, d in sidebar_queue],
                "deferred_queue": [{"url": u, "depth": d} for u, d in deferred_queue],
                "pages_completed": pages,
                "sitemap": sitemap,
                "link_counters": link_counters,
                "sidebar_discovered": sidebar_discovered,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _save_sidebar_order(crawl_root: Path, urls: list[str]) -> None:
    (crawl_root / "_sidebar_order.json").write_text(
        json.dumps(urls, indent=2), encoding="utf-8"
    )


def _load_sidebar_order(crawl_root: Path) -> list[str]:
    path = crawl_root / "_sidebar_order.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [u for u in data if isinstance(u, str)]
    except Exception:
        return []


def _not_scraped_entry(item: dict, reason: str, *, detail: str = "") -> dict:
    entry = {
        "label": item.get("label", ""),
        "selector": item.get("selector", ""),
        "elementType": item.get("elementType", ""),
        "status": "not_scraped",
        "reason": reason,
    }
    if detail:
        entry["detail"] = detail[:500]
    return entry


def dom_changed(before: dict, after: dict) -> bool:
    if after.get("overlays", 0) > before.get("overlays", 0):
        return True
    b, a = before.get("len", 0), after.get("len", 0)
    if b == 0:
        return a > 300
    return abs(a - b) >= 300 or (b and abs(a - b) / b >= 0.02)


def detect_tab_switch(
    before_fp: dict,
    after_fp: dict,
    before_tabs: list,
    after_tabs: list,
) -> bool:
    """Return True if click switched an active tab rather than opening an overlay."""
    if after_fp.get("overlays", 0) > before_fp.get("overlays", 0):
        return False

    def _key(t: dict) -> str:
        return t.get("text", "") + "|" + t.get("id", "")

    return {_key(t) for t in before_tabs} != {_key(t) for t in after_tabs}


def discover_with_scroll(page) -> list[dict]:
    """Scroll through the page to trigger lazy rendering, then discover all triggers."""
    try:
        h = page.evaluate("() => document.body.scrollHeight") or 0
        for pct in [0.3, 0.6, 1.0]:
            page.evaluate(f"() => window.scrollTo(0, {int(h * pct)})")
            page.wait_for_timeout(500)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
    except Exception:
        pass
    return page.evaluate(DISCOVER_JS)


def crawl_interactions(
    context,
    page_url: str,
    source_slug: str,
    page_dir: Path,
    crawl_root: Path,
    candidates: list[dict],
    max_interactions: int = DEFAULT_MAX_INTERACTIONS,
    *,
    wait_after_load_ms: int = WAIT_AFTER_LOAD_MS,
    use_networkidle: bool = True,
    skip_screenshots: bool = False,
) -> dict:
    """Replay each discovered trigger, reusing one tab (reload between clicks)."""
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
    not_scraped: list[dict] = []

    # Always process every llm_type="tab_switch" item — tab panels can be missed
    # if they fall outside the max_interactions budget. Non-tab items fill the
    # remaining budget in their original order.
    tab_items = [c for c in candidates if c.get("llm_type") == "tab_switch"]
    other_items = [c for c in candidates if c.get("llm_type") != "tab_switch"]
    to_process = tab_items + other_items[:max(0, max_interactions - len(tab_items))]
    to_process_keys = {
        (c.get("selector", ""), c.get("label", ""), c.get("id", "")) for c in to_process
    }
    for c in candidates:
        key = (c.get("selector", ""), c.get("label", ""), c.get("id", ""))
        if key not in to_process_keys:
            not_scraped.append(_not_scraped_entry(c, "over_budget"))

    ipage = None
    try:
        ipage = context.new_page()
        for idx, item in enumerate(to_process, start=1):
            selector = item.get("selector", "")
            if not selector:
                not_scraped.append(_not_scraped_entry(item, "no_selector"))
                continue
            # Anchors are navigation — BFS owns them. Never click/capture here.
            if (item.get("elementType") or "").lower() == "a":
                not_scraped.append(_not_scraped_entry(item, "anchor_navigation"))
                continue

            try:
                _goto_clean(
                    ipage,
                    page_url,
                    use_networkidle=use_networkidle,
                    wait_ms=wait_after_load_ms,
                )
                ipage.evaluate(DISCOVER_JS)

                locator = ipage.locator(selector).first
                if locator.count() == 0 or not locator.is_visible():
                    not_scraped.append(_not_scraped_entry(item, "not_visible"))
                    continue

                before_url = ipage.url
                before_title = ipage.title()
                before_fp = ipage.evaluate(DOM_FINGERPRINT_JS)
                before_tabs = ipage.evaluate(ACTIVE_TABS_JS)

                # Capture the complete trigger element BEFORE clicking — after a
                # navigation/DOM mutation the element may detach and outerHTML is lost.
                try:
                    element_meta = locator.evaluate(EXTRACT_ELEMENT_JS)
                except Exception:
                    element_meta = {}

                # For tab_switch elements, read aria-controls before clicking so we
                # can look up the exact panel by ID after the click.
                aria_controls_val = ""
                if item.get("llm_type") == "tab_switch":
                    try:
                        aria_controls_val = locator.get_attribute("aria-controls") or ""
                    except Exception:
                        aria_controls_val = ""

                try:
                    ipage.evaluate(MUTATION_OBSERVER_SETUP_JS)
                except Exception:
                    pass

                locator.click(timeout=5000)
                ipage.wait_for_timeout(WAIT_AFTER_CLICK_MS)
                if use_networkidle:
                    try:
                        ipage.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass

                try:
                    click_mutations = ipage.evaluate(MUTATION_OBSERVER_READ_JS)
                except Exception:
                    click_mutations = []

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
                # Tab-switch panels often swap equally-sized content so dom_changed
                # may return False; never skip them on that basis.
                if not dom_changed(before_fp, after_fp) and item.get("llm_type") != "tab_switch":
                    not_scraped.append(_not_scraped_entry(item, "no_ui_change"))
                    continue

                tab_panel = None
                if item.get("llm_type") == "tab_switch":
                    # Force the type — don't let CLASSIFY_JS re-label it as dropdown/modal.
                    itype = "tab-switch"
                    if aria_controls_val:
                        try:
                            tab_panel = ipage.evaluate(
                                "(panelId) => {"
                                "  const el = document.getElementById(panelId);"
                                "  if (!el) return null;"
                                "  return { selector: '#' + CSS.escape(panelId), innerHTML: el.innerHTML };"
                                "}",
                                aria_controls_val,
                            )
                        except Exception:
                            tab_panel = None
                else:
                    after_tabs = ipage.evaluate(ACTIVE_TABS_JS)
                    if detect_tab_switch(before_fp, after_fp, before_tabs, after_tabs):
                        itype = "tab-switch"
                        try:
                            tab_panel = ipage.evaluate(ACTIVE_TAB_PANEL_JS)
                        except Exception:
                            tab_panel = None
                    else:
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
                    tab_panel=tab_panel,
                    skip_screenshots=skip_screenshots,
                    mutations=click_mutations,
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
                not_scraped.append(_not_scraped_entry(item, "click_failed", detail=str(exc)))
                print(f"[BFS] Interaction not scraped ({selector}): {exc}")
    finally:
        if ipage:
            try:
                ipage.close()
            except Exception:
                pass

    (interactions_dir / "interactions.json").write_text(
        json.dumps(registry, indent=2), encoding="utf-8"
    )
    (interactions_dir / "not_scraped.json").write_text(
        json.dumps(not_scraped, indent=2), encoding="utf-8"
    )
    if not_scraped:
        print(f"[BFS] Not scraped: {len(not_scraped)}")
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
    priority_url_patterns: list[str] | None = None,
    seed_url_patterns: list[str] | None = None,
    skip_url_patterns: list[str] | None = None,
    list_detail_link_limits: list[dict] | None = None,
    link_cross_page_rules: list[dict] | None = None,
    global_link_limits: list[dict] | None = None,
    mandatory_tab_labels: list[str] | None = None,
    max_interactions: int = DEFAULT_MAX_INTERACTIONS,
    max_ranked_interactions: int = 15,
    max_interaction_depth: int | None = 3,
    check_login: bool = False,
    skip_screenshots: bool = False,
    wait_after_load_ms: int = WAIT_AFTER_LOAD_MS,
    use_networkidle: bool = True,
    sidebar_first: bool = True,
    resume: bool = True,
    hash_routes: bool = True,
) -> dict:
    checkpoint_path = get_crawl_checkpoint_path(app_name)
    start_norm = normalize_url(start_url)
    seed_norms = _build_seed_norms(start_url, seed_url_patterns, hash_routes=hash_routes)
    visited: set[str] = _visited_from_disk(crawl_root)
    sidebar_queue: list[tuple[str, int]] = []
    deferred_queue: list[tuple[str, int]] = []
    sidebar_discovered = False
    link_counters: dict[str, dict[str, int]] = {}
    sitemap: list[dict] = []

    ckpt = _load_checkpoint(checkpoint_path) if resume else None
    if ckpt:
        visited.update(ckpt.get("visited") or [])
        sidebar_queue = [(e["url"], e["depth"]) for e in ckpt.get("sidebar_queue") or []]
        deferred_queue = [(e["url"], e["depth"]) for e in ckpt.get("deferred_queue") or []]
        link_counters = ckpt.get("link_counters") or {}
        sidebar_discovered = bool(ckpt.get("sidebar_discovered"))
        sitemap = ckpt.get("sitemap") or []
        pages = int(ckpt.get("pages_completed") or len(sitemap))
        print(f"[BFS] Resuming crawl — {pages} pages on disk, {len(sidebar_queue)} sidebar + {len(deferred_queue)} deferred queued")
    else:
        pages = len(visited)
        sidebar_queue = [(start_url, 0)]
        if not sidebar_first:
            for seed_url in build_seed_urls(start_url, seed_url_patterns or [], hash_routes=hash_routes):
                if normalize_url(seed_url) != start_norm:
                    deferred_queue.append((seed_url, 1))
            if seed_url_patterns:
                print(f"[BFS] Seeded routes: {len(deferred_queue)}")

    def _queue_norms() -> set[str]:
        return {normalize_url(u) for u, _ in sidebar_queue + deferred_queue}

    def _enqueue_deferred(link: str, source_url: str, depth: int) -> None:
        link_norm = normalize_url(link)
        if link_norm in visited or link_norm in _queue_norms():
            return
        if not _should_enqueue_link(
            link,
            source_url,
            skip_patterns=skip_url_patterns or [],
            seed_norms=seed_norms,
            list_detail_limits=list_detail_link_limits or [],
            link_counters=link_counters,
            cross_page_rules=link_cross_page_rules,
            global_link_limits=global_link_limits,
            hash_routes=hash_routes,
        ):
            return
        if not sidebar_first and any(pat in link for pat in (priority_url_patterns or [])):
            deferred_queue.insert(0, (link, depth))
        else:
            deferred_queue.append((link, depth))

    def _enqueue_sidebar(link: str, depth: int) -> None:
        link_norm = normalize_url(link)
        if link_norm in visited or link_norm in _queue_norms():
            return
        if _should_skip_url(link, skip_url_patterns or []) and link_norm not in seed_norms:
            return
        sidebar_queue.append((link, depth))

    def _pop_next() -> tuple[str, int] | None:
        while sidebar_queue:
            item = sidebar_queue.pop(0)
            if normalize_url(item[0]) not in visited:
                return item
        while deferred_queue:
            item = deferred_queue.pop(0)
            if normalize_url(item[0]) not in visited:
                return item
        return None

    if sidebar_first and _load_sidebar_order(crawl_root):
        if not ckpt:
            for link in _load_sidebar_order(crawl_root):
                _enqueue_sidebar(link, 1)
            sidebar_discovered = True
            print(f"[BFS] Restored sidebar order: {len(sidebar_queue)} modules queued")
        else:
            missing = 0
            for link in _load_sidebar_order(crawl_root):
                link_norm = normalize_url(link)
                if link_norm in visited or _page_on_disk(crawl_root, link):
                    continue
                before_q = len(sidebar_queue) + len(deferred_queue)
                _enqueue_sidebar(link, 1)
                if len(sidebar_queue) + len(deferred_queue) > before_q:
                    missing += 1
            if missing:
                print(f"[BFS] Re-queued {missing} uncrawled sidebar module(s)")
    elif not ckpt and visited and resume and sidebar_first:
        print(
            "[BFS] Saved pages on disk but no checkpoint/sidebar order — "
            "will discover sidebar on next new page"
        )

    before, after = _prune_queues(
        sidebar_queue,
        deferred_queue,
        visited=visited,
        skip_patterns=skip_url_patterns or [],
        seed_norms=seed_norms,
        global_link_limits=global_link_limits,
        hash_routes=hash_routes,
    )
    if before != after:
        print(f"[BFS] Pruned duplicate queue URLs: {before - after}")

    interactions_found = 0
    interactions_saved = 0

    while pages < max_pages:
        nxt = _pop_next()
        if not nxt:
            break
        url, depth = nxt
        norm = normalize_url(url)
        if norm in visited:
            continue
        if _page_on_disk(crawl_root, url):
            visited.add(norm)
            print(f"[BFS] Skip (already saved): {url}")
            continue
        if _is_redundant_route(url, hash_routes=hash_routes) and norm not in seed_norms:
            print(f"[BFS] Skipped duplicate route: {url}")
            visited.add(norm)
            continue
        if _should_skip_url(url, skip_url_patterns or []) and norm not in seed_norms:
            print(f"[BFS] Skipped URL (pattern): {url}")
            visited.add(norm)
            continue
        p = urlparse(url)
        if p.netloc and p.netloc != base_domain:
            continue

        visited.add(norm)
        slug = page_slug(url)

        print(f"[BFS] Sidebar queue: {len(sidebar_queue)} | Deferred: {len(deferred_queue)}")
        print(f"[BFS] Current URL: {url}")
        print(f"[BFS] Depth: {depth}")
        print(f"[BFS] Pages completed: {pages}")

        page = None
        candidates: list[dict] = []
        page_title = ""
        try:
            page = context.new_page()
            _goto_clean(
                page,
                url,
                use_networkidle=use_networkidle,
                wait_ms=wait_after_load_ms,
            )

            if check_login and is_login_page(page):
                print("[AUTH] Session expired — delete metadata/auth.json and re-run")
                page.close()
                break

            page_dir = crawl_root / slug
            page_title = page.title()
            save_page_capture(
                page_dir, page, url, page_title, page_type, skip_screenshots=skip_screenshots
            )
            pages += 1

            if sidebar_first and not sidebar_discovered:
                nav_items = collect_sidebar_links(page, page.url, base_domain)
                if nav_items:
                    has_dashboard = any(
                        "home/dashboard" in _route_fragment(n["url"]) for n in nav_items
                    )
                    print(f"[BFS] Sidebar modules (in order): {len(nav_items)}")
                    order_urls: list[str] = []
                    for nav in nav_items:
                        link = nav["url"]
                        if has_dashboard and _is_bare_home(link, hash_routes=hash_routes):
                            print(f"    · skip duplicate home: {link}")
                            continue
                        label = nav.get("label") or ""
                        order_urls.append(link)
                        print(f"    · {label or link}")
                        _enqueue_sidebar(link, 1)
                    _save_sidebar_order(crawl_root, order_urls)
                    sidebar_discovered = True
                else:
                    print("[BFS] Sidebar not found — falling back to link discovery")

            try:
                candidates = discover_with_scroll(page)
            except Exception as exc:
                print(f"[BFS] Interaction discovery failed: {exc}")
                candidates = []

            links = collect_links(page, page.url, base_domain)
            print(f"[BFS] Links Found: {len(links)}")
            for link in links:
                _enqueue_deferred(link, url, depth + 1)

            page.close()
            page = None

            _SKIP_CLASSES = {"accordion-button", "accordion-title"}
            _SKIP_LABELS = {"button", "div", "Subscribe", "TAKE A LIVE PRODUCT TOUR", "testing"}
            candidates = [
                c for c in candidates
                if not any(cls in (c.get("className") or "") for cls in _SKIP_CLASSES)
                and (c.get("label") or "").strip() not in _SKIP_LABELS
            ]

            run_interactions = max_interaction_depth is None or depth < max_interaction_depth
            if run_interactions and candidates and os.getenv("GEMINI_API_KEY"):
                from ranker.interaction_ranker import rank_candidates
                candidates = rank_candidates(
                    page_title,
                    url,
                    candidates,
                    top_n=max_ranked_interactions,
                    mandatory_labels=mandatory_tab_labels,
                )
                print(f"[BFS] Ranked Candidates: {len(candidates)}")

            if run_interactions:
                ix = crawl_interactions(
                    context,
                    url,
                    slug,
                    page_dir,
                    crawl_root,
                    candidates,
                    max_interactions,
                    wait_after_load_ms=wait_after_load_ms,
                    use_networkidle=use_networkidle,
                    skip_screenshots=skip_screenshots,
                )
                interactions_found += ix["found"]
                interactions_saved += ix["saved"]
                print(f"[BFS] Interactions Found: {ix['found']}")
                print(f"[BFS] Interactions Saved: {ix['saved']}")

                nav_targets = ix.get("nav_targets", [])
                if nav_targets:
                    print(f"[BFS] Navigations Found: {len(nav_targets)}")
                for link in nav_targets:
                    _enqueue_deferred(link, url, depth + 1)
            else:
                print(f"[BFS] Depth {depth} — interactions skipped (max_interaction_depth={max_interaction_depth})")

            sitemap.append({"slug": slug, "url": url, "title": page_title, "page_type": page_type})
            get_sitemap_path(app_name).write_text(json.dumps(sitemap, indent=2), encoding="utf-8")
            pruned = _prune_queues(
                sidebar_queue,
                deferred_queue,
                visited=visited,
                skip_patterns=skip_url_patterns or [],
                seed_norms=seed_norms,
                global_link_limits=global_link_limits,
                hash_routes=hash_routes,
            )
            if pruned[0] != pruned[1]:
                print(f"[BFS] Pruned duplicate queue URLs: {pruned[0] - pruned[1]}")
            _save_checkpoint(
                checkpoint_path,
                visited=visited,
                sidebar_queue=sidebar_queue,
                deferred_queue=deferred_queue,
                pages=pages,
                sitemap=sitemap,
                link_counters=link_counters,
                sidebar_discovered=sidebar_discovered,
            )

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

    if not sidebar_queue and not deferred_queue:
        print("[BFS] Queue Exhausted")
        if checkpoint_path.is_file():
            checkpoint_path.unlink()
    elif pages >= max_pages:
        print("[BFS] Page Limit Reached")

    return {
        "pages": pages,
        "interactions_found": interactions_found,
        "interactions_saved": interactions_saved,
        "resumed": bool(ckpt),
    }


def _run_browser(app_name: str, cfg: dict, *, post_auth: bool) -> dict:
    crawl_root = ensure_app_dirs(app_name)
    max_interactions = cfg.get("max_interactions_per_page", DEFAULT_MAX_INTERACTIONS)
    max_ranked_interactions = cfg.get("max_ranked_interactions", 15)
    max_interaction_depth = cfg.get("max_interaction_depth", 3)
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
        priority_url_patterns = cfg.get("priority_url_patterns") or []
        seed_url_patterns = cfg.get("seed_url_patterns") or []
        result = bfs_crawl(
            context,
            start,
            urlparse(start).netloc,
            max_pages,
            page_type,
            crawl_root,
            app_name,
            priority_url_patterns=priority_url_patterns,
            seed_url_patterns=seed_url_patterns if post_auth else [],
            skip_url_patterns=cfg.get("skip_url_patterns") or [],
            list_detail_link_limits=cfg.get("list_detail_link_limits") or [],
            link_cross_page_rules=cfg.get("link_cross_page_rules") or [],
            global_link_limits=cfg.get("global_link_limits") or [],
            mandatory_tab_labels=cfg.get("mandatory_tab_labels") or [],
            max_interactions=max_interactions,
            max_ranked_interactions=max_ranked_interactions,
            max_interaction_depth=max_interaction_depth,
            check_login=post_auth,
            skip_screenshots=bool(cfg.get("crawl_skip_screenshots")),
            wait_after_load_ms=int(cfg.get("crawl_wait_after_load_ms", WAIT_AFTER_LOAD_MS)),
            use_networkidle=bool(cfg.get("crawl_use_networkidle", True)),
            sidebar_first=bool(cfg.get("crawl_sidebar_first", True)),
            resume=bool(cfg.get("crawl_resume", True)),
            hash_routes=bool(cfg.get("crawl_hash_routes", True)),
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

