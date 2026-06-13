"""Interactive Browser Agent CLI.

Run:
    python run_agent.py

Chrome opens already logged into Zoho Books. Type any natural-language goal and
the browser navigates to that page in real time. Type 'quit' to close.

Examples:
    > show invoices
    > show customers
    > show credit notes
    > show payments
    > show vendors
    > show quotes
    > show sales orders
    > show delivery challans
    > show dashboard
"""

from __future__ import annotations

import asyncio

from agents import BrowserAgent
from services import BrowserService


async def main() -> None:
    auth = BrowserAgent.get_auth_path("zoho")

    if auth is None:
        print(
            "\n[agent] WARNING: No auth.json found at "
            "storage/apps/zoho/metadata/auth.json\n"
            "  Browser will open without login — navigation to app pages may fail.\n"
            "  Run `python main.py crawl zoho` first to save auth state.\n"
        )

    browser = await BrowserService.create(
        storage_state_path=str(auth) if auth else None
    )
    agent = BrowserAgent(browser, app_name="zoho")

    print("\n[agent] Chrome is open and ready.")
    print("Type a goal to navigate (e.g. 'show invoices'), or 'quit' to exit.\n")

    while True:
        try:
            goal = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not goal:
            continue

        if goal.lower() in ("quit", "exit", "q", ":q"):
            break

        result = await agent.navigate(goal)

        if not result.success:
            print(f"  [agent] could not navigate — {result.error}\n")
        else:
            print(f"  [agent] navigated → {result.current_url}\n")

    print("  Closing browser...")
    await browser.close()
    print("  Done.")


if __name__ == "__main__":
    asyncio.run(main())
