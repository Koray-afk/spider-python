#!/usr/bin/env python3
"""Re-capture Likwid chart pages with canvas→img freeze (no full re-crawl)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import get_app_config
from crawler_v2 import _goto_clean, _prepare_snapshot_dom, static_snapshot_html
from playwright.sync_api import sync_playwright
from storage.storage_manager import get_auth_file, get_crawl_dir

_CHART_HINTS = ("am5-layer", "amcharts", "AmCharts", "<canvas")


def _chart_page_dirs(crawl_root: Path) -> list[Path]:
    found: set[Path] = set()
    for meta in crawl_root.rglob("metadata.json"):
        page_dir = meta.parent
        html_path = page_dir / "page.html"
        if not html_path.is_file():
            continue
        name = page_dir.name
        if "bi-dashboard" in name or name == "home-v2" or "home-v2" in str(page_dir):
            found.add(page_dir)
            continue
        try:
            snippet = html_path.read_text(encoding="utf-8", errors="ignore")[:80000]
        except OSError:
            continue
        if any(h in snippet for h in _CHART_HINTS):
            found.add(page_dir)
    return sorted(found, key=lambda p: str(p))


def _refreeze(page_dir: Path, page, cfg: dict) -> bool:
    meta_path = page_dir / "metadata.json"
    if not meta_path.is_file():
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    url = meta.get("url")
    if not url:
        return False
    print(f"[REFREEZE] {page_dir.relative_to(page_dir.parents[2])} <- {url}")
    _goto_clean(
        page,
        url,
        use_networkidle=bool(cfg.get("crawl_use_networkidle", False)),
        wait_ms=int(cfg.get("crawl_wait_after_load_ms", 6000)),
    )
    try:
        page.wait_for_selector("canvas, .am5-layer", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(4000)
    _prepare_snapshot_dom(page, page.url)
    html = static_snapshot_html(page.content(), page.url, page=page)
    (page_dir / "page.html").write_text(html, encoding="utf-8")
    frozen = html.count("data-stitch-frozen-chart")
    print(f"[REFREEZE]   frozen charts: {frozen}")
    return frozen > 0 or "<canvas" not in html


def main() -> int:
    app = "likwid"
    cfg = get_app_config(app)
    crawl_root = get_crawl_dir(app)
    auth = get_auth_file(app)
    if not auth.is_file():
        print(f"[REFREEZE] Missing auth: {auth}")
        return 1

    targets = _chart_page_dirs(crawl_root)
    print(f"[REFREEZE] {len(targets)} page(s) to refresh")

    ok = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        ctx = browser.new_context(
            storage_state=str(auth),
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        for page_dir in targets:
            try:
                if _refreeze(page_dir, page, cfg):
                    ok += 1
            except Exception as exc:
                print(f"[REFREEZE] FAILED {page_dir.name}: {exc}")
        ctx.close()
        browser.close()

    print(f"[REFREEZE] Done: {ok}/{len(targets)}")
    print("[REFREEZE] Re-run: python3 main.py stitch likwid")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
