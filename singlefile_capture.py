from pathlib import Path

from playwright.async_api import BrowserContext, Page

from config import ENGINE_DIST_DIR

HOOK_BUNDLE = ENGINE_DIST_DIR / "hook.bundle.js"
MAIN_BUNDLE = ENGINE_DIST_DIR / "singlefile.bundle.js"

CAPTURE_OPTIONS = {
    "compressHTML": False,
    "compressContent": False,
    "blockScripts": False,
    "blockImages": False,
    "blockVideos": False,
    "loadDeferredImages": True,
    "removeHiddenElements": False,
}


def _read_bundle(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing SingleFile bundle: {path}\n"
            "Run: bash scripts/build_singlefile.sh"
        )
    return path.read_text(encoding="utf-8")


async def _inject_into_page(page: Page, hook_source: str, main_source: str) -> None:
    await page.add_script_tag(content=hook_source)
    await page.add_script_tag(content=main_source)


async def _singlefile_diagnostics(page: Page) -> dict:
    return await page.evaluate(
        """() => ({
            typeofSinglefile: typeof window.singlefile,
            typeofSingleFile: typeof window.SingleFile,
            singleKeys: Object.keys(window).filter(
                (key) => key.toLowerCase().includes("single")
            ),
        })"""
    )


async def ensure_singlefile(page: Page) -> None:
    diag = await _singlefile_diagnostics(page)
    print(f"[SINGLEFILE] Pre-capture URL: {page.url}")
    print(f"[SINGLEFILE] typeof window.singlefile: {diag['typeofSinglefile']}")
    print(f"[SINGLEFILE] typeof window.SingleFile: {diag['typeofSingleFile']}")
    print(f"[SINGLEFILE] window keys containing 'single': {diag['singleKeys']}")

    if diag["typeofSinglefile"] == "object":
        return

    print("[SINGLEFILE] Runtime missing on page; injecting bundles")
    await _inject_into_page(page, _read_bundle(HOOK_BUNDLE), _read_bundle(MAIN_BUNDLE))

    diag = await _singlefile_diagnostics(page)
    if diag["typeofSinglefile"] != "object":
        raise RuntimeError("SingleFile is not available in page context")


async def install_singlefile(context: BrowserContext) -> None:
    hook_source = _read_bundle(HOOK_BUNDLE)
    main_source = _read_bundle(MAIN_BUNDLE)

    print("[SINGLEFILE] Installing runtime on browser context")
    await context.add_init_script(script=hook_source)
    await context.add_init_script(script=main_source)

    for page in context.pages:
        print(f"[SINGLEFILE] Injecting into existing page: {page.url}")
        await _inject_into_page(page, hook_source, main_source)


async def capture_html(page: Page) -> str:
    await ensure_singlefile(page)
    print("[SINGLEFILE] blockScripts=True")

    url = page.url
    title = await page.title()

    page_data = await page.evaluate(
        """async (options) => {
            if (!window.singlefile || !window.singlefile.getPageData) {
                throw new Error("SingleFile is not available in page context");
            }
            return await window.singlefile.getPageData(options);
        }""",
        {
            **CAPTURE_OPTIONS,
            "url": url,
            "title": title,
        },
    )

    content = page_data["content"]
    if isinstance(content, list):
        content = bytes(content).decode("utf-8", errors="replace")
    return content
