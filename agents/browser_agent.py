"""Browser Agent V1 — deterministic navigation layer for the demo platform.

Connects the Knowledge Layer (catalog, modules) to BrowserService.
No LLM reasoning, no ReAct loops, no memory.

Usage:

    import asyncio
    from services import BrowserService
    from agents import BrowserAgent

    async def main():
        browser = await BrowserService.create()
        agent = BrowserAgent(browser, app_name="zoho")
        result = await agent.navigate("show invoices")
        print(result)

    asyncio.run(main())
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.browser_service import BrowserService

# --------------------------------------------------------------------------
# Synonym table — maps common user phrases to canonical catalog page IDs
# ---------------------------------------------------------------------------

SYNONYMS: dict[str, str] = {
    # Invoices
    "invoice": "invoices",
    "invoices": "invoices",
    "billing": "invoices",
    "bills received": "invoices",
    # Customers / Contacts
    "customer": "contacts",
    "customers": "contacts",
    "contact": "contacts",
    "contacts": "contacts",
    "client": "contacts",
    "clients": "contacts",
    # Credit notes
    "credit note": "creditnotes",
    "credit notes": "creditnotes",
    "creditnote": "creditnotes",
    "creditnotes": "creditnotes",
    "refund": "creditnotes",
    "refunds": "creditnotes",
    # Payments received
    "payment": "paymentsreceived",
    "payments": "paymentsreceived",
    "payment received": "paymentsreceived",
    "payments received": "paymentsreceived",
    "receipt": "paymentsreceived",
    "receipts": "paymentsreceived",
    # Vendors
    "vendor": "vendors",
    "vendors": "vendors",
    "supplier": "vendors",
    "suppliers": "vendors",
    # Quotes / Estimates
    "quote": "quotes",
    "quotes": "quotes",
    "estimate": "quotes",
    "estimates": "quotes",
    "proposal": "quotes",
    "proposals": "quotes",
    # Sales orders
    "sales order": "salesorders",
    "sales orders": "salesorders",
    "salesorder": "salesorders",
    "salesorders": "salesorders",
    "order": "salesorders",
    "orders": "salesorders",
    # Delivery challans
    "delivery challan": "deliverychallans",
    "delivery challans": "deliverychallans",
    "deliverychallan": "deliverychallans",
    "deliverychallans": "deliverychallans",
    "delivery": "deliverychallans",
    "shipment": "deliverychallans",
    # Dashboard / home
    "dashboard": "home-dashboard",
    "home": "home-dashboard",
    "home dashboard": "home-dashboard",
}

# Words to strip from user input before lookup
_FILLER = re.compile(
    r"\b(show|open|go to|navigate to|take me to|display|view|see|get|load)\b",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s-]")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class NavigationPlan:
    """Ordered list of browser actions to reach *page_id*."""

    page_id: str
    page_title: str
    steps: list[dict] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"NavigationPlan(page_id={self.page_id!r}, "
            f"page_title={self.page_title!r}, steps={self.steps!r})"
        )


@dataclass
class AgentResult:
    """Result returned by BrowserAgent.navigate()."""

    success: bool
    goal: str
    page: str
    current_url: str
    screenshot: str | None
    error: str | None = None

    def __repr__(self) -> str:
        if self.success:
            return (
                f"AgentResult(success=True, goal={self.goal!r}, "
                f"page={self.page!r}, url={self.current_url!r})"
            )
        return (
            f"AgentResult(success=False, goal={self.goal!r}, "
            f"error={self.error!r})"
        )


# ---------------------------------------------------------------------------
# BrowserAgent
# ---------------------------------------------------------------------------


class BrowserAgent:
    """Deterministic navigation agent.

    Responsibilities:
      1. Resolve a user goal string to a catalog page ID.
      2. Build a NavigationPlan (list of BrowserService actions).
      3. Execute the plan through BrowserService.
      4. Return an AgentResult.

    Does NOT implement LLM reasoning, ReAct loops, memory, or self-healing.
    """

    def __init__(
        self,
        browser: BrowserService,
        app_name: str = "zoho",
    ) -> None:
        self._browser = browser
        self._app_name = app_name
        self._catalog: dict = {}
        self._page_index: dict[str, dict] = {}
        self._load_knowledge()

    # ------------------------------------------------------------------
    # Knowledge loading
    # ------------------------------------------------------------------

    def _load_knowledge(self) -> None:
        from storage.storage_manager import get_app_catalog_dir, get_metadata_dir

        catalog_dir = get_app_catalog_dir(self._app_name)
        catalog_path = catalog_dir / "catalog.json"

        if not catalog_path.exists():
            raise FileNotFoundError(
                f"catalog.json not found at {catalog_path} — "
                f"run `python main.py catalog {self._app_name}` first"
            )

        self._catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

        for page in self._catalog.get("pages") or []:
            pid = page.get("id", "")
            if pid:
                self._page_index[pid] = {
                    "title": page.get("title", ""),
                    "url": "",
                    "purpose": page.get("purpose", ""),
                }

        # Load authenticated URLs from sitemap.json
        sitemap_path = get_metadata_dir(self._app_name) / "sitemap.json"
        if sitemap_path.exists():
            sitemap = json.loads(sitemap_path.read_text(encoding="utf-8"))
            for entry in sitemap:
                slug = entry.get("slug", "")
                url = entry.get("url", "")
                # Strip org-ID prefix: "app-60073808761-invoices" → "invoices"
                page_id = re.sub(r"^app-\d+-", "", slug)
                if page_id in self._page_index:
                    self._page_index[page_id]["url"] = url
            print(
                f"  [agent] sitemap loaded — URLs resolved for "
                f"{sum(1 for p in self._page_index.values() if p['url'])} pages"
            )

        print(
            f"  [agent] knowledge loaded — "
            f"{len(self._page_index)} pages from {self._app_name} catalog"
        )

    # ------------------------------------------------------------------
    # Auth helper
    # ------------------------------------------------------------------

    @staticmethod
    def get_auth_path(app_name: str = "zoho") -> Path | None:
        """Return the path to the app's Playwright auth.json, or None if absent.

        Pass the result to ``BrowserService.create(storage_state_path=...)`` so
        the browser starts already authenticated:

            auth = BrowserAgent.get_auth_path("zoho")
            browser = await BrowserService.create(storage_state_path=str(auth))
        """
        from storage.storage_manager import get_metadata_dir

        auth_path = get_metadata_dir(app_name) / "auth.json"
        return auth_path if auth_path.exists() else None

    # ------------------------------------------------------------------
    # Intent resolution
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        text = _FILLER.sub("", text)
        text = _PUNCT.sub("", text)
        return " ".join(text.lower().split())

    def resolve_page(self, goal: str) -> str | None:
        """Map a user goal string to a catalog page ID.

        Stage 1: static SYNONYMS table (exact match after normalisation).
        Stage 2: substring scan of catalog page ids and titles.
        Returns None if no match is found.
        """
        normalized = self._normalize(goal)

        # Stage 1 — synonym map (exact match)
        if normalized in SYNONYMS:
            page_id = SYNONYMS[normalized]
            if page_id in self._page_index:
                return page_id
            # synonym exists but page not in this catalog — fall through

        # Stage 1b — check individual words against synonym map
        # (handles "show the invoices" where normalized is "the invoices")
        for token in normalized.split():
            if token in SYNONYMS:
                page_id = SYNONYMS[token]
                if page_id in self._page_index:
                    return page_id

        # Stage 2 — substring scan of catalog ids and titles
        for pid, meta in self._page_index.items():
            if normalized in pid.replace("-", " "):
                return pid
            if normalized in meta.get("title", "").lower():
                return pid
            if pid.replace("-", " ") in normalized:
                return pid

        return None

    # ------------------------------------------------------------------
    # Navigation plan
    # ------------------------------------------------------------------

    def build_plan(self, page_id: str) -> NavigationPlan:
        """Build a NavigationPlan for *page_id*.

        Primary strategy: direct URL navigation using the authenticated URL from
        sitemap.json. This works regardless of where the browser currently is
        and avoids fragile text-matching on sidebar labels.

        Fallback: if no URL is available, attempt a sidebar text-click using the
        catalog page title.
        """
        meta = self._page_index.get(page_id, {})
        title = meta.get("title", "")
        url = meta.get("url", "")

        steps: list[dict] = []

        if url:
            steps.append({"action": "goto", "url": url})
        elif title:
            # No URL in sitemap — fall back to sidebar click
            steps.append({"action": "click", "target": f"text={title}"})

        return NavigationPlan(page_id=page_id, page_title=title, steps=steps)

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    async def execute_plan(self, plan: NavigationPlan) -> tuple[bool, str | None]:
        """Execute *plan* through BrowserService.

        Returns (success, error_message).
        Iterates over steps in order and stops on the first success.
        """
        for step in plan.steps:
            action = step.get("action")

            if action == "goto":
                result = await self._browser.goto(step["url"])
                if result.ok:
                    return True, None
                print(f"  [agent] goto failed ({step['url']!r}) — {result.error}")
                return False, result.error

            elif action == "click":
                result = await self._browser.click(
                    step["target"], timeout=8_000
                )
                if result.ok:
                    return True, None
                print(
                    f"  [agent] click failed ({step['target']!r}) — "
                    f"{result.error}"
                )
                return False, result.error

        return False, f"No executable steps in plan for page {plan.page_id!r}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def navigate(self, goal: str) -> AgentResult:
        """Resolve *goal*, build a plan, execute it, and return an AgentResult.

        Example:
            result = await agent.navigate("show invoices")
        """
        print(f"\n[agent] goal: {goal!r}")

        # 1. Resolve intent → page_id
        page_id = self.resolve_page(goal)
        if page_id is None:
            return AgentResult(
                success=False,
                goal=goal,
                page="",
                current_url=self._browser.current_url(),
                screenshot=None,
                error=f"Could not resolve goal {goal!r} to a known page",
            )
        print(f"  [agent] resolved → {page_id!r}")

        # 2. Build navigation plan
        plan = self.build_plan(page_id)
        print(f"  [agent] plan → {plan}")

        # 3. Execute plan
        await self._browser.wait(0.5)
        success, err = await self.execute_plan(plan)

        # 4. Let the SPA settle, then capture a screenshot
        await self._browser.wait(1.5)
        shot = await self._browser.take_screenshot()
        screenshot_path = str(shot.data) if shot.ok else None

        if not success:
            return AgentResult(
                success=False,
                goal=goal,
                page=page_id,
                current_url=self._browser.current_url(),
                screenshot=screenshot_path,
                error=err,
            )

        current_url = self._browser.current_url()
        print(f"  [agent] navigated → {current_url}")

        return AgentResult(
            success=True,
            goal=goal,
            page=page_id,
            current_url=current_url,
            screenshot=screenshot_path,
        )
