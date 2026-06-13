"""Single isolated Playwright browser session."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from sandbox.session_store import SessionStore


class BrowserSession:
    """Wraps one Playwright browser/context/page triplet.

    Each instance is fully isolated — separate browser process, separate
    context, separate on-disk state directory.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.store = SessionStore(session_id)

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, storage_state_path: str | None = None) -> None:
        """Launch a fresh non-headless Chromium and create a new context.

        Args:
            storage_state_path: Optional path to a Playwright storage-state JSON
                file (cookies + localStorage). When provided the browser starts
                already authenticated — useful for injecting a saved Zoho/HubSpot
                login session without navigating through the login flow.
        """
        self.store.ensure_dirs()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--start-maximized"],
        )
        ctx_opts: dict = {"no_viewport": True}
        if storage_state_path and Path(storage_state_path).exists():
            ctx_opts["storage_state"] = storage_state_path
            print(f"  [sandbox] loading auth state from {Path(storage_state_path).name}")
        self._context = await self._browser.new_context(**ctx_opts)
        self._page = await self._context.new_page()
        await self._write_metadata(status="active", last_url="")
        print(f"  [sandbox] session {self.session_id} started")

    async def close(self) -> None:
        """Persist state, then tear down browser and Playwright."""
        try:
            await self.save_state()
        except Exception as exc:
            print(f"  [sandbox] warning: save_state failed on close — {exc}")
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            print(f"  [sandbox] warning: browser teardown error — {exc}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
        await self._write_metadata(status="closed")
        print(f"  [sandbox] session {self.session_id} closed")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def open(self, url: str) -> None:
        """Navigate the active page to *url*."""
        self._require_active()
        assert self._page is not None
        await self._page.goto(url, wait_until="domcontentloaded")
        await self._write_metadata(status="active", last_url=self._page.url)
        print(f"  [sandbox] {self.session_id} → {self._page.url}")

    def current_url(self) -> str:
        """Return the current page URL (synchronous — reads from live page)."""
        if self._page is None:
            meta = self.store.load_metadata()
            return meta.get("last_url", "")
        return self._page.url

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    async def screenshot(self) -> Path:
        """Capture the full page and save it; return the path."""
        self._require_active()
        assert self._page is not None
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = self.store.screenshot_path(ts)
        await self._page.screenshot(path=str(path), full_page=True)
        print(f"  [sandbox] screenshot saved → {path.name}")
        return path

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    async def save_state(self) -> None:
        """Persist cookies and full storage state to disk."""
        self._require_active()
        assert self._context is not None
        cookies: list[Any] = await self._context.cookies()
        self.store.save_cookies(cookies)
        await self._context.storage_state(
            path=str(self.store.storage_state_path)
        )
        await self._write_metadata(
            status="active",
            last_url=self._page.url if self._page else "",
        )
        print(f"  [sandbox] state saved for session {self.session_id}")

    async def restore_state(self) -> None:
        """Create a new context pre-loaded with the persisted storage state."""
        if not self.store.has_storage_state():
            raise FileNotFoundError(
                f"No saved state for session {self.session_id} — "
                f"run save_state() first or call start() for a fresh session."
            )
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--start-maximized"],
            )
        if self._context:
            await self._context.close()

        self._context = await self._browser.new_context(
            storage_state=str(self.store.storage_state_path),
            no_viewport=True,
        )
        self._page = await self._context.new_page()

        meta = self.store.load_metadata()
        last_url = meta.get("last_url", "")
        if last_url:
            await self._page.goto(last_url, wait_until="domcontentloaded")

        await self._write_metadata(status="active", last_url=self._page.url)
        print(f"  [sandbox] session {self.session_id} restored → {self._page.url}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_active(self) -> None:
        if self._context is None or self._page is None:
            raise RuntimeError(
                f"Session {self.session_id} is not active — call start() or restore_state() first."
            )

    async def _write_metadata(self, *, status: str, last_url: str | None = None) -> None:
        page_title = ""
        if self._page is not None:
            try:
                page_title = await self._page.title()
            except Exception:
                pass

        meta = self.store.load_metadata()
        if not meta:
            meta = {
                "session_id": self.session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        meta["status"] = status
        if last_url is not None:
            meta["current_url"] = last_url
            meta["last_url"] = last_url
        meta["page_title"] = page_title
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.store.save_metadata(meta)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        active = self._context is not None
        url = self.current_url() if active else "(closed)"
        return f"BrowserSession(id={self.session_id!r}, active={active}, url={url!r})"
