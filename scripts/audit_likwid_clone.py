#!/usr/bin/env python3
"""Playwright audit of the local Likwid stitched clone."""

import json
import sys
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
PAGES = [
    "/",
    "/home-v2/page.html",
    "/flow-ai-bi-dashboard-inventory-intelligence/page.html",
    "/flow-ai-customers-list/page.html",
    "/rise-crm-leads-list/page.html",
    "/flow-ai-inventory-stock-list/page.html",
]


def audit_page(page, url: str) -> dict:
    failed: list[dict] = []
    console_errors: list[str] = []

    def on_request_failed(req):
        failed.append({"url": req.url, "failure": req.failure or "unknown"})

    def on_console(msg):
        if msg.type == "error":
            console_errors.append(msg.text)

    page.on("requestfailed", on_request_failed)
    page.on("console", on_console)

    full_url = url if url.startswith("http") else f"{BASE}{url}"
    resp = page.goto(full_url, wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(2000)

    stats = page.evaluate("""() => {
      const imgs = [...document.images];
      const brokenImgs = imgs.filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src);
      const links = [...document.querySelectorAll('a[href]')].slice(0, 200);
      const stylesheets = [...document.styleSheets];
      let cssErrors = 0;
      for (const ss of stylesheets) {
        try { void ss.cssRules; } catch (e) { cssErrors++; }
      }
      return {
        title: document.title,
        bodyChars: (document.body?.innerText || '').trim().length,
        imgTotal: imgs.length,
        brokenImgs,
        linkCount: links.length,
        cssSheetCount: stylesheets.length,
        cssLoadErrors: cssErrors,
        hasSidebar: !!document.querySelector('#kt_app_sidebar, .app-sidebar'),
        hasRuntime: !!document.querySelector('script[src*="runtime.js"]'),
      };
    }""")

    http_status = resp.status if resp else 0
    final_url = page.url

    return {
        "requested": url,
        "final_url": final_url,
        "http_status": http_status,
        "failed_requests": failed,
        "console_errors": console_errors,
        **stats,
    }


def main() -> int:
    headless = "--headed" not in sys.argv
    out_path = Path(__file__).resolve().parents[1] / "storage/apps/likwid/metadata/playwright_audit.json"

    results: list[dict] = []
    all_failed: Counter = Counter()
    all_console: Counter = Counter()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, channel="chrome")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        for url in PAGES:
            print(f"[AUDIT] {url}")
            try:
                row = audit_page(page, url)
            except Exception as exc:
                row = {"requested": url, "error": str(exc)}
            results.append(row)
            for f in row.get("failed_requests", []):
                all_failed[f["url"]] += 1
            for e in row.get("console_errors", []):
                all_console[e[:200]] += 1

        shot = Path(__file__).resolve().parents[1] / "storage/apps/likwid/metadata/playwright_audit.png"
        page.goto(f"{BASE}/home-v2/page.html", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(shot), full_page=False)
        browser.close()

    summary = {
        "pages_audited": len(results),
        "top_failed_urls": all_failed.most_common(30),
        "top_console_errors": all_console.most_common(20),
        "pages": results,
    }
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== LIKWID CLONE AUDIT ===")
    for row in results:
        req = row.get("requested", "?")
        if row.get("error"):
            print(f"  FAIL {req}: {row['error']}")
            continue
        status = row.get("http_status")
        chars = row.get("bodyChars", 0)
        broken = len(row.get("brokenImgs", []))
        failed = len(row.get("failed_requests", []))
        css_err = row.get("cssLoadErrors", 0)
        print(
            f"  {req}: status={status} chars={chars} "
            f"failed_req={failed} broken_imgs={broken} css_errors={css_err}"
        )

    if all_failed:
        print("\n-- Top failed network requests --")
        for url, n in all_failed.most_common(15):
            print(f"  [{n}x] {url[:120]}")

    if all_console:
        print("\n-- Top console errors --")
        for msg, n in all_console.most_common(10):
            print(f"  [{n}x] {msg[:120]}")

    print(f"\nFull report: {out_path}")
    print(f"Screenshot: {shot}")
    return 1 if any(r.get("error") or r.get("http_status", 200) >= 400 for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
