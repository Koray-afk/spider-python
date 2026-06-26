import asyncio
import subprocess
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from config import (
    AUTH_DIR,
    CHROME_MAC_PATH,
    DEBUG_PORT,
    EXTRA_WAIT_SECONDS,
    NAVIGATION_TIMEOUT_MS,
    SKIP_URL_KEYWORDS,
    USER_DATA_DIR,
    get_app_config,
)
from singlefile_capture import install_singlefile, capture_html
from mock_api import PageApiRecorder
from storage import save_page
from urls import normalize_crawl_url, resolve_href


def api_origin_for(start_url: str) -> str:
    parsed = urlparse(start_url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def setup_network_api_recorder(page, recorder: PageApiRecorder) -> None:
    async def handle_response(response) -> None:
        await recorder.handle_response(response)

    def on_response(response) -> None:
        asyncio.create_task(handle_response(response))

    page.on("response", on_response)


def auth_path_for(app_name: str) -> Path:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    return AUTH_DIR / f"{app_name}.json"


def launch_chrome(headless: bool = False) -> subprocess.Popen:
    if not Path(CHROME_MAC_PATH).exists():
        raise FileNotFoundError(
            f"Chrome not found at {CHROME_MAC_PATH}. "
            "Install Google Chrome or update CHROME_MAC_PATH in config.py."
        )

    Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)

    args = [
        CHROME_MAC_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
    ]
    if headless:
        args.append("--headless=new")

    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    cdp_url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
    for _ in range(60):
        try:
            urllib.request.urlopen(cdp_url, timeout=1)
            return process
        except (urllib.error.URLError, TimeoutError, OSError):
            if process.poll() is not None:
                raise RuntimeError("Chrome exited before CDP became available")
            time.sleep(0.5)

    process.terminate()
    raise RuntimeError(f"Chrome did not start CDP on port {DEBUG_PORT}")


def stop_chrome(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


LOGIN_FAILURE_PATH_SEGMENTS = (
    "/login", "/signin", "/signup", "/relogin", "/sign-in", "/oauth",
)
LOGIN_FAILURE_QUERY_MARKERS = (
    "authfailurereason",
    "loginredirecturl",
    "session+timed+out",
    "session%20timed%20out",
)
AUTH_OBSERVE_SECONDS = 15
AUTH_URL_STABLE_SECONDS = 2
POST_LOGIN_STABILIZE_SECONDS = 5


def _app_hostname(post_auth_home: str) -> str:
    return urlparse(post_auth_home).netloc.lower()


def _is_on_app_domain(url: str, post_auth_home: str) -> bool:
    return urlparse(url).netloc.lower() == _app_hostname(post_auth_home)


def _is_login_failure_url(url: str) -> bool:
    parsed = urlparse(url.lower())
    path = parsed.path.lower()
    query = parsed.query.lower()

    for segment in LOGIN_FAILURE_PATH_SEGMENTS:
        if segment in path:
            return True

    for marker in LOGIN_FAILURE_QUERY_MARKERS:
        if marker in query:
            return True

    if "oauth" in query:
        return True

    return False


async def _page_shows_login_form(page) -> bool:
    try:
        return await page.locator('input[type="password"]:visible').count() > 0
    except Exception:
        return False


async def _observe_redirect_chain(
    page,
    post_auth_home: str,
    timeout_seconds: int = AUTH_OBSERVE_SECONDS,
) -> tuple[list[str], str]:
    chain: list[str] = []

    def record(url: str) -> None:
        if not url:
            return
        if not chain or chain[-1] != url:
            chain.append(url)

    def on_navigated(frame) -> None:
        if frame == page.main_frame:
            record(frame.url)

    page.on("framenavigated", on_navigated)
    record(page.url)

    try:
        await page.goto(
            post_auth_home,
            wait_until="domcontentloaded",
            timeout=NAVIGATION_TIMEOUT_MS,
        )
    except Exception:
        try:
            await page.goto(
                post_auth_home,
                wait_until="commit",
                timeout=NAVIGATION_TIMEOUT_MS,
            )
        except Exception:
            pass

    record(page.url)

    deadline = time.monotonic() + timeout_seconds
    stable_start: float | None = None
    last_url = page.url

    while time.monotonic() < deadline:
        await asyncio.sleep(0.5)
        current = page.url
        record(current)

        if current == last_url:
            if stable_start is None:
                stable_start = time.monotonic()
            elif time.monotonic() - stable_start >= AUTH_URL_STABLE_SECONDS:
                await asyncio.sleep(POST_LOGIN_STABILIZE_SECONDS)
                record(page.url)
                settled_url = page.url
                if (
                    settled_url == current
                    and not _is_login_failure_url(settled_url)
                    and not await _page_shows_login_form(page)
                ):
                    break
                stable_start = None
                last_url = settled_url
        else:
            stable_start = None
            last_url = current

    record(page.url)
    page.remove_listener("framenavigated", on_navigated)

    final_url = page.url
    print("[AUTH] Redirect chain:")
    for i, url in enumerate(chain, 1):
        print(f"[AUTH]   {i} {url}")
    print(f"[AUTH] Final URL: {final_url}")

    return chain, final_url


async def _evaluate_session(
    page,
    app_name: str,
    post_auth_home: str,
    pre_auth_home: str | None,
    final_url: str,
) -> bool:
    if pre_auth_home:
        pre_host = urlparse(pre_auth_home).netloc.lower()
        if urlparse(final_url).netloc.lower() == pre_host:
            print(f"[AUTH] Session missing or expired for {app_name} — redirected to pre-auth site")
            return False

    if _is_on_app_domain(final_url, post_auth_home):
        if _is_login_failure_url(final_url):
            print(f"[AUTH] Session missing or expired for {app_name} — login page on app domain")
            return False

        if await _page_shows_login_form(page):
            print(f"[AUTH] Session missing or expired for {app_name} — password field visible")
            return False

        print(f"[AUTH] Session valid for {app_name}")
        return True

    if _is_login_failure_url(final_url):
        print(f"[AUTH] Session missing or expired for {app_name} — login page detected")
        return False

    expected_host = _app_hostname(post_auth_home)
    actual_host = urlparse(final_url).netloc.lower()
    print(
        f"[AUTH] Session missing or expired for {app_name} — "
        f"final URL not on app domain (expected {expected_host}, got {actual_host})"
    )
    return False


async def validate_session(
    page,
    app_name: str,
    post_auth_home: str,
    pre_auth_home: str | None = None,
    after_manual_login: bool = False,
) -> bool:
    if after_manual_login:
        print("[AUTH] Revalidating after manual login...")
        print(f"[AUTH] Expected URL: {post_auth_home}")
        print(f"[AUTH] Current URL: {page.url}")
        await asyncio.sleep(2)
    else:
        print(f"[AUTH] Validating session for {app_name}")
        print(f"[AUTH] Expected post-auth URL: {post_auth_home}")

    _, final_url = await _observe_redirect_chain(page, post_auth_home)

    return await _evaluate_session(
        page, app_name, post_auth_home, pre_auth_home, final_url
    )


async def select_auth_page(context, post_auth_home: str):
    expected_host = urlparse(post_auth_home).netloc.lower()
    pages = context.pages

    print("[AUTH] Open tabs:")
    for i, tab in enumerate(pages):
        print(f"[AUTH]   {i} {tab.url}")

    matching = [
        tab for tab in pages
        if urlparse(tab.url).netloc.lower() == expected_host
    ]

    if not matching:
        matching = [
            tab for tab in pages
            if expected_host in tab.url.lower()
        ]

    if matching:
        page = matching[-1]
    elif pages:
        page = pages[-1]
    else:
        page = await context.new_page()

    await page.bring_to_front()
    print(f"[AUTH] Selected tab: {page.url}")
    return page


async def connect_to_chrome(playwright, headless: bool):
    chrome = launch_chrome(headless=headless)
    browser = await playwright.chromium.connect_over_cdp(
        f"http://127.0.0.1:{DEBUG_PORT}"
    )
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
    return chrome, browser, context, page


async def ensure_authenticated(
    playwright,
    app_name: str,
    login_url: str,
    post_auth_home: str,
    pre_auth_home: str | None,
    auth_path: Path,
    headless: bool,
):
    print("=" * 80)
    print("[AUTH] Starting auth validation")
    print(f"[AUTH] App: {app_name}")
    print(f"[AUTH] Post auth url: {post_auth_home}")

    chrome, browser, context, page = await connect_to_chrome(playwright, headless)

    valid = await validate_session(page, app_name, post_auth_home, pre_auth_home)
    print(f"[AUTH] Initial validation result: {valid}")

    if valid:
        print("=" * 80)
        return chrome, browser, context, page

    print(f"[AUTH] Session missing or expired for {app_name}")
    if auth_path.exists():
        auth_path.unlink()
        print(f"[AUTH] Deleted backup {auth_path}")

    await browser.close()
    stop_chrome(chrome)

    print("[AUTH] Triggering manual login")
    chrome, browser, context = await manual_login(playwright, login_url, auth_path)
    print("[AUTH] Manual login finished")

    page = await select_auth_page(context, post_auth_home)

    valid = await validate_session(
        page, app_name, post_auth_home, pre_auth_home, after_manual_login=True
    )
    print(f"[AUTH] Validation after login: {valid}")

    if not valid:
        print("[AUTH] Still invalid after login")
        await browser.close()
        stop_chrome(chrome)
        print("=" * 80)
        raise RuntimeError(
            f"Authentication failed for {app_name} after manual login. "
            f"Check Chrome profile at {USER_DATA_DIR}"
        )

    print("=" * 80)
    return chrome, browser, context, page


def should_skip_url(url: str) -> bool:
    lower = url.lower()
    return any(keyword in lower for keyword in SKIP_URL_KEYWORDS)


def is_same_app(url: str, base_url: str) -> bool:
    return urlparse(url).netloc == urlparse(base_url).netloc


async def capture_accessibility_tree(page) -> dict:
    cdp = await page.context.new_cdp_session(page)
    try:
        await cdp.send("Accessibility.enable")
        await cdp.send("DOM.enable")
        tree = await cdp.send("Accessibility.getFullAXTree")
        return tree
    finally:
        await cdp.detach()


async def manual_login(playwright, login_url: str, auth_path: Path):
    print("[AUTH] Starting real Chrome for manual login...")
    print(f"[AUTH] Using profile: {USER_DATA_DIR}")

    chrome = launch_chrome(headless=False)
    browser = await playwright.chromium.connect_over_cdp(
        f"http://127.0.0.1:{DEBUG_PORT}"
    )
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()

    await page.goto(login_url, wait_until="domcontentloaded")
    await page.bring_to_front()

    input("[AUTH] Complete login in the browser, then press ENTER here... ")

    print("[AUTH] Waiting for session to stabilize...")
    await asyncio.sleep(3)

    await context.storage_state(path=str(auth_path))
    print(f"[AUTH] Saved storage state backup to {auth_path}")

    return chrome, browser, context


async def discover_links(page, base_url: str) -> list[str]:
    hrefs = await page.eval_on_selector_all(
        "a[href]",
        "elements => elements.map(el => el.href)",
    )

    print(f"[DISCOVER] Found {len(hrefs)} anchor links")

    links: list[str] = []
    seen: set[str] = set()

    for href in hrefs:
        absolute = resolve_href(base_url, href)
        if not absolute:
            continue
        normalized = normalize_crawl_url(absolute)
        if not is_same_app(absolute, base_url):
            continue
        if should_skip_url(absolute):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append(absolute)

    print(f"[DISCOVER] Found {len(links)} unique routes")
    return links


async def crawl_app(app_name: str, headless: bool = True) -> None:
    app_config = get_app_config(app_name)
    login_url = app_config["login_url"]
    start_url = app_config["post_auth_home"]
    pre_auth_home = app_config.get("pre_auth_home")
    use_singlefile = app_config.get("use_singlefile", False)
    auth_path = auth_path_for(app_name)

    queue: deque[str] = deque([start_url])
    visited: set[str] = set()

    chrome = None

    try:
        async with async_playwright() as playwright:
            chrome, browser, context, auth_page = await ensure_authenticated(
                playwright,
                app_name,
                login_url,
                start_url,
                pre_auth_home,
                auth_path,
                headless,
            )
            if use_singlefile:
                print("[CAPTURE] Strategy: singlefile")
                await install_singlefile(context)
            else:
                print("[CAPTURE] Strategy: native")

            await auth_page.close()

            while queue:
                url = queue.popleft()
                normalized_url = normalize_crawl_url(url)

                if normalized_url in visited:
                    print(f"[SKIP] already visited {normalized_url}")
                    continue

                visited.add(normalized_url)

                page = await context.new_page()
                print("[PAGE] Opened new page")
                print(f"[VISIT] {url}")

                try:
                    api_recorder = PageApiRecorder(app_name, api_origin_for(start_url))
                    await setup_network_api_recorder(page, api_recorder)

                    try:
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=NAVIGATION_TIMEOUT_MS,
                        )
                    except Exception as exc:
                        print(f"[ERROR] navigation failed {url}: {exc}")
                        continue

                    await asyncio.sleep(EXTRA_WAIT_SECONDS)

                    actual_url = page.url
                    if _is_login_failure_url(actual_url) or await _page_shows_login_form(page):
                        print(f"[ERROR] Session expired — landed on login page: {actual_url}")
                        raise RuntimeError(
                            f"Session expired for {app_name}. "
                            "Re-run the crawler and complete login when prompted."
                        )

                    title = await page.title()

                    try:
                        screenshot = await page.screenshot(full_page=True)
                        # ====================================================================
                        # --- FIXED: CONDITIONALLY USE SINGLEFILE ENGINE EXTRACTION ---
                        # ====================================================================
                        if use_singlefile:
                            print(f"[CAPTURE] Processing page content via SingleFile Engine...")
                            html = await capture_html(page)
                        else:
                            print(f"[CAPTURE] Processing page content via Native Browser DOM...")
                            html = await page.content()
                        accessibility_tree = await capture_accessibility_tree(page)
                        page_dir = save_page(
                            app_name,
                            actual_url,
                            title,
                            html,
                            screenshot,
                            accessibility_tree,
                        )
                        api_recorder.save_page_manifest(page_dir, page_dir.name)
                        api_recorder.merge_into_global_registry(page_dir.name)
                    except Exception as exc:
                        print(f"[ERROR] capture failed {url}: {exc}")
                        continue

                    try:
                        for link in await discover_links(page, start_url):
                            link_normalized = normalize_crawl_url(link)
                            if link_normalized not in visited:
                                queue.append(link)
                    except Exception as exc:
                        print(f"[ERROR] link discovery failed {url}: {exc}")
                finally:
                    print("[PAGE] Closing page")
                    await page.close()

            await browser.close()
    finally:
        if chrome is not None:
            stop_chrome(chrome)
