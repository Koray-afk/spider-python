"""Browser execution primitives — the "hands" of the demo platform.

BrowserService wraps one BrowserSession and exposes clean async methods for
every browser action: navigation, interaction, observation, and lifecycle.

It does NOT implement AI reasoning, workflow execution, or React generation.

Usage:

    import asyncio
    from services import BrowserService

    async def main():
        browser = await BrowserService.create()
        await browser.goto("https://books.zoho.com")
        await browser.click("text=Invoices")
        await browser.fill("input[name='search']", "customer")
        result = await browser.screenshot()
        print(browser.current_url())
        await browser.close()

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from sandbox.browser_session import BrowserSession
from sandbox.sandbox_manager import SandboxManager


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Uniform return value for every BrowserService method.

    Attributes:
        ok      True if the action succeeded.
        action  Human-readable name of the action performed.
        data    Optional payload (screenshot Path, page title string, URL, etc.)
        error   Error message when ok=False, None otherwise.
    """

    ok: bool
    action: str
    data: Any = field(default=None)
    error: str | None = field(default=None)

    def __repr__(self) -> str:
        if self.ok:
            return f"ActionResult(ok=True, action={self.action!r}, data={self.data!r})"
        return f"ActionResult(ok=False, action={self.action!r}, error={self.error!r})"


# ---------------------------------------------------------------------------
# BrowserService
# ---------------------------------------------------------------------------

class BrowserService:
    """Thin async wrapper around a single BrowserSession.

    All public methods return an ActionResult — exceptions are caught and
    turned into error results so the browser stays open on failures.
    """

    def __init__(self, session: BrowserSession) -> None:
        self._session = session
        self._stream_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Factory classmethods
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        session_id: str | None = None,
        storage_state_path: str | None = None,
    ) -> "BrowserService":
        """Launch a fresh Chrome window and return a ready BrowserService.

        Args:
            session_id: Optional explicit session ID (UUID by default).
            storage_state_path: Optional path to a Playwright storage-state JSON
                (cookies + localStorage). Pass the app's ``auth.json`` to start
                the browser already logged in — e.g.
                ``storage/apps/zoho/metadata/auth.json``.
        """
        manager = SandboxManager()
        session = await manager.create_session(
            session_id,
            storage_state_path=storage_state_path,
        )
        return cls(session)

    @classmethod
    async def resume(cls, session_id: str) -> "BrowserService":
        """Restore a previously saved session and return a BrowserService."""
        manager = SandboxManager()
        session = await manager.restore_session(session_id)
        return cls(session)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _page(self) -> Page:
        page = self._session._page
        if page is None:
            raise RuntimeError(
                "No active page — the session may have been closed. "
                "Call BrowserService.create() or BrowserService.resume()."
            )
        return page

    def _ok(self, action: str, data: Any = None) -> ActionResult:
        return ActionResult(ok=True, action=action, data=data)

    def _err(self, action: str, exc: Exception) -> ActionResult:
        if isinstance(exc, PlaywrightTimeoutError):
            msg = f"timeout: {exc}"
        elif isinstance(exc, PlaywrightError):
            msg = f"playwright error: {exc}"
        else:
            msg = str(exc)
        print(f"  [browser_service] warning: {action} failed — {msg}")
        return ActionResult(ok=False, action=action, error=msg)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def goto(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
    ) -> ActionResult:
        """Navigate to *url*. Waits for the DOM to load by default."""
        try:
            await self._page.goto(url, wait_until=wait_until)
            await self._session._write_metadata(status="active", last_url=self._page.url)
            return self._ok("goto", self._page.url)
        except Exception as exc:
            return self._err("goto", exc)

    async def reload(self) -> ActionResult:
        """Reload the current page."""
        try:
            await self._page.reload(wait_until="domcontentloaded")
            return self._ok("reload", self._page.url)
        except Exception as exc:
            return self._err("reload", exc)

    async def go_back(self) -> ActionResult:
        """Navigate back in browser history."""
        try:
            await self._page.go_back(wait_until="domcontentloaded")
            return self._ok("go_back", self._page.url)
        except Exception as exc:
            return self._err("go_back", exc)

    async def go_forward(self) -> ActionResult:
        """Navigate forward in browser history."""
        try:
            await self._page.go_forward(wait_until="domcontentloaded")
            return self._ok("go_forward", self._page.url)
        except Exception as exc:
            return self._err("go_forward", exc)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    async def click(self, selector: str, timeout: int = 5_000) -> ActionResult:
        """Click the element matching *selector*.

        Args:
            selector: Playwright selector (CSS, XPath, or ``text=...``).
            timeout:  Max wait in milliseconds before giving up.
        """
        try:
            await self._page.click(selector, timeout=timeout)
            return self._ok("click", selector)
        except Exception as exc:
            return self._err("click", exc)

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: int = 5_000,
    ) -> ActionResult:
        """Clear the input matching *selector* and type *value*."""
        try:
            await self._page.fill(selector, value, timeout=timeout)
            return self._ok("fill", {"selector": selector, "value": value})
        except Exception as exc:
            return self._err("fill", exc)

    async def press(self, key: str) -> ActionResult:
        """Send a keyboard *key* to the currently focused element.

        Examples: ``"Enter"``, ``"Tab"``, ``"Escape"``, ``"Control+a"``.
        """
        try:
            await self._page.keyboard.press(key)
            return self._ok("press", key)
        except Exception as exc:
            return self._err("press", exc)

    async def scroll(self, x: int, y: int) -> ActionResult:
        """Scroll the page by (*x*, *y*) pixels relative to current position."""
        try:
            await self._page.evaluate(f"window.scrollBy({x}, {y})")
            return self._ok("scroll", {"x": x, "y": y})
        except Exception as exc:
            return self._err("scroll", exc)

    async def wait(self, seconds: float) -> ActionResult:
        """Pause execution for *seconds*. Keeps the browser fully interactive."""
        try:
            await asyncio.sleep(seconds)
            return self._ok("wait", seconds)
        except Exception as exc:
            return self._err("wait", exc)

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    async def screenshot(self, full_page: bool = True) -> ActionResult:
        """Capture a screenshot and save it to the session's screenshots dir.

        Returns an ActionResult whose ``data`` is the ``Path`` of the saved PNG.
        """
        try:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            path: Path = self._session.store.screenshot_path(ts)
            await self._page.screenshot(path=str(path), full_page=full_page)
            print(f"  [browser_service] screenshot → {path.name}")
            return self._ok("screenshot", path)
        except Exception as exc:
            return self._err("screenshot", exc)

    async def take_screenshot(self, full_page: bool = True) -> ActionResult:
        """Alias for :meth:`screenshot`. Preferred name in the execution layer."""
        return await self.screenshot(full_page=full_page)

    # ------------------------------------------------------------------
    # Screenshot stream
    # ------------------------------------------------------------------

    async def start_screenshot_stream(self, interval: float = 2.0) -> None:
        """Start capturing screenshots every *interval* seconds in the background.

        Safe to call multiple times — does nothing if the stream is already running.
        Screenshots are saved to ``sandbox/sessions/{session_id}/screenshots/``.
        """
        if self._stream_task and not self._stream_task.done():
            return
        self._stream_task = asyncio.create_task(self._stream_loop(interval))
        print(f"  [browser_service] screenshot stream started (interval={interval}s)")

    async def _stream_loop(self, interval: float) -> None:
        try:
            while True:
                await self.take_screenshot()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    async def stop_screenshot_stream(self) -> None:
        """Stop the background screenshot stream if it is running."""
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._stream_task = None
        print("  [browser_service] screenshot stream stopped")

    def current_url(self) -> str:
        """Return the current page URL (synchronous)."""
        try:
            return self._page.url
        except Exception:
            return self._session.current_url()

    async def title(self) -> str:
        """Return the current page title."""
        try:
            return await self._page.title()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Stop screenshot stream, save session state, and close the browser."""
        await self.stop_screenshot_stream()
        await self._session.close()

    # ------------------------------------------------------------------
    # Session info
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session.session_id

    def __repr__(self) -> str:
        return (
            f"BrowserService(session_id={self.session_id!r}, "
            f"url={self.current_url()!r})"
        )
