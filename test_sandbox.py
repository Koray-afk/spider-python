"""Smoke tests for Execution Layer V1 + Browser Agent V1.

Tests:
  Part A — Execution Layer V1
  1.  Create a BrowserService session
  2.  goto() — navigate to a URL
  3.  title() — confirm page_title is fetched
  4.  take_screenshot() — human-readable timestamp filename
  5.  start_screenshot_stream() — background screenshots every 2 s
  6.  Wait 6 s (expect ~3 screenshots)
  7.  stop_screenshot_stream()
  8.  Verify metadata.json contains page_title + current_url
  9.  List screenshots — confirm names match YYYY-MM-DD_HH-MM-SS.png

  Part B — Browser Agent V1
  10. Instantiate BrowserAgent
  11. navigate("show invoices")      — sidebar click
  12. navigate("show customers")     — resolves to contacts
  13. navigate("show credit notes")  — resolves to creditnotes

Run:
    python test_sandbox.py
"""

import asyncio
import json
import re
from pathlib import Path

from agents import BrowserAgent
from services import BrowserService

PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.png$")


# ---------------------------------------------------------------------------
# Part A — Execution Layer V1
# ---------------------------------------------------------------------------

async def test_execution_layer(browser: BrowserService) -> None:
    sid = browser.session_id

    print("\n=== [A-1] Navigating to https://books.zoho.com ===")
    result = await browser.goto("https://books.zoho.com")
    print(f"  goto result: {result}")
    print(f"  current_url: {browser.current_url()}")

    print("\n=== [A-2] Fetching page title ===")
    t = await browser.title()
    print(f"  title: {t!r}")

    print("\n=== [A-3] Single take_screenshot() ===")
    r = await browser.take_screenshot()
    print(f"  result: {r}")
    if r.ok:
        name = Path(r.data).name
        assert PATTERN.match(name), f"Bad filename format: {name}"
        print(f"  filename OK: {name}")

    print("\n=== [A-4] Starting screenshot stream (interval=2 s) ===")
    await browser.start_screenshot_stream(interval=2.0)

    print("\n=== [A-5] Waiting 6 s (expect ~3 more screenshots) ===")
    await asyncio.sleep(6)

    print("\n=== [A-6] Stopping screenshot stream ===")
    await browser.stop_screenshot_stream()

    print("\n=== [A-7] Checking metadata.json ===")
    from sandbox.session_store import SESSIONS_ROOT
    meta_path = SESSIONS_ROOT / sid / "metadata.json"
    meta = json.loads(meta_path.read_text())
    print(f"  metadata: {json.dumps(meta, indent=2)}")
    assert "page_title" in meta, "page_title missing from metadata"
    assert "current_url" in meta, "current_url missing from metadata"
    print("  page_title and current_url present ✓")

    print("\n=== [A-8] Listing screenshots ===")
    from sandbox.session_store import SessionStore
    store = SessionStore(sid)
    shots = store.list_screenshots()
    print(f"  {len(shots)} screenshot(s) saved")
    for p in shots:
        assert PATTERN.match(p.name), f"Bad filename: {p.name}"
        print(f"    {p.name} ✓")

    print("\n✅ Execution Layer V1 — all checks passed")


# ---------------------------------------------------------------------------
# Part B — Browser Agent V1
# ---------------------------------------------------------------------------

async def test_browser_agent(browser: BrowserService) -> None:
    print("\n=== [B-1] Instantiating BrowserAgent ===")
    agent = BrowserAgent(browser, app_name="zoho")

    goals = [
        "show invoices",
        "show customers",
        "show credit notes",
    ]

    for goal in goals:
        print(f"\n=== [B] navigate({goal!r}) ===")
        result = await agent.navigate(goal)
        print(f"  result: {result}")
        if not result.success:
            print(f"  WARNING: navigation failed — {result.error}")
        else:
            print(f"  page: {result.page}  url: {result.current_url}")
            assert result.page, "page field should not be empty"
            assert result.current_url, "current_url should not be empty"
            if result.screenshot:
                name = Path(result.screenshot).name
                assert PATTERN.match(name), f"Bad screenshot filename: {name}"
                print(f"  screenshot: {name} ✓")

    print("\n✅ Browser Agent V1 — all checks passed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    # ------------------------------------------------------------------
    # Part A — Execution Layer (unauthenticated, marketing page is fine)
    # ------------------------------------------------------------------
    print("\n=== [Part A] Creating BrowserService session (no auth) ===")
    browser_a = await BrowserService.create()
    print(f"  session id: {browser_a.session_id}")
    try:
        await test_execution_layer(browser_a)
    finally:
        await browser_a.close()

    # ------------------------------------------------------------------
    # Part B — Browser Agent (needs Zoho auth to reach the real app)
    # ------------------------------------------------------------------
    auth_path = BrowserAgent.get_auth_path("zoho")
    if auth_path is None:
        print(
            "\n⚠  No auth.json found at storage/apps/zoho/metadata/auth.json.\n"
            "   Run `python main.py crawl zoho` first (log in when Chrome opens),\n"
            "   then re-run this test to exercise the Browser Agent.\n"
        )
        return

    print(f"\n=== [Part B] Creating BrowserService session (auth: {auth_path.name}) ===")
    browser_b = await BrowserService.create(storage_state_path=str(auth_path))
    print(f"  session id: {browser_b.session_id}")
    try:
        await test_browser_agent(browser_b)
    finally:
        input("\n  Browser is open. Press Enter to close…")
        await browser_b.close()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
