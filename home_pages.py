"""Generate home sub-pages (Getting Started, Recent Updates) from the dashboard template."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

GETTING_STARTED_STEPS = [
    ("inventory-product-product-creation.html", "Create your first Item", "Add products or services you sell."),
    ("contacts-new.html", "Add your first Customer", "Store customer details for invoicing."),
    ("quotes.html", "Send a Quote", "Share estimates before confirming a sale."),
    ("salesorders-new.html", "Create a Sales Order", "Track customer orders from confirmation to fulfilment."),
    ("invoices.html", "Create your first Invoice", "Bill customers and get paid faster."),
]

RECENT_UPDATES = [
    ("Finance Workshop 2026", "Two days of expert-led workshops and live demos on Zoho Finance products.", "https://www.zoho.com/financesuite/finance-workshop"),
    ("Books Mobile App", "Manage invoices and expenses on the go with the Zoho Books mobile app.", "https://www.zoho.com/in/books/accounting-mobile-apps/"),
    ("What's New in Books", "Explore the latest features and improvements in Zoho Books.", "https://www.zoho.com/in/books/whats-new.html"),
]


def _set_active_tab(soup: BeautifulSoup, active: str) -> None:
    tabs = soup.select_one("#homescreen-tabs")
    if not tabs:
        return

    for item in tabs.select(".nav-item"):
        link = item.select_one("a.nav-link, button.nav-link")
        if not link:
            continue
        label = link.get_text(strip=True)
        is_active = label == active
        link["class"] = [c for c in link.get("class", []) if c != "active"]
        if is_active:
            link["class"] = link.get("class", []) + ["active"]

        if link.name == "a":
            if label == "Dashboard":
                link["href"] = "home-dashboard.html"
            elif label == "Getting Started":
                link["href"] = "home-gettingstarted.html"
            elif label == "Recent Updates":
                link["href"] = "home-recentupdates.html"


def _replace_dashboard_content(soup: BeautifulSoup, new_html: str) -> None:
    container = soup.select_one("#home-screen .dashboard-card-container")
    if not container:
        return
    replacement = BeautifulSoup(new_html, "html.parser")
    panel = replacement.select_one(".getting-started-panel, .recent-updates-panel")
    if not panel:
        panel = replacement.find("div")
    if not panel:
        return
    container.clear()
    container.append(panel)


def _getting_started_html() -> str:
    steps = "\n".join(
        f"""<a class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3"
              href="{href}">
            <div>
              <div class="fw-semibold">{title}</div>
              <div class="text-muted font-small">{desc}</div>
            </div>
            <span class="text-primary">Start &rarr;</span>
           </a>"""
        for href, title, desc in GETTING_STARTED_STEPS
    )
    return f"""
<div class="getting-started-panel px-4 py-4">
  <div class="row g-4">
    <div class="col-lg-8">
      <h4 class="mb-2">Welcome to Zoho Books</h4>
      <p class="text-muted mb-4">Complete these steps to set up your organisation and start accounting.</p>
      <div class="list-group shadow-sm">{steps}</div>
    </div>
    <div class="col-lg-4">
      <div class="card border-0 shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Helpful Resources</h5>
          <ul class="list-unstyled mb-0 font-small">
            <li class="mb-2"><a href="https://www.zoho.com/in/books/help/getting-started" target="_blank" rel="noopener">Getting Started Guide</a></li>
            <li class="mb-2"><a href="https://www.zoho.com/in/books/welcome-guide.html" target="_blank" rel="noopener">Welcome Guide</a></li>
            <li class="mb-2"><a href="home-dashboard.html">Back to Dashboard</a></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>"""


def _recent_updates_html() -> str:
    cards = "\n".join(
        f"""<div class="card border-0 shadow-sm mb-3">
            <div class="card-body">
              <h5 class="card-title mb-1">{title}</h5>
              <p class="text-muted font-small mb-2">{desc}</p>
              <a href="{href}" target="_blank" rel="noopener" class="font-small">Learn more</a>
            </div>
          </div>"""
        for title, desc, href in RECENT_UPDATES
    )
    return f"""
<div class="recent-updates-panel px-4 py-4">
  <h4 class="mb-3">Recent Updates</h4>
  <div class="row"><div class="col-lg-8">{cards}</div></div>
</div>"""


def _load_template(pages_dir: Path) -> str:
    for name in ("home-dashboard.html", "home.html"):
        path = pages_dir / name
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("Need home.html or home-dashboard.html as template")


def generate_home_subpages(pages_dir: Path, app_base: str = "") -> list[dict]:
    """Build Getting Started and Recent Updates pages; return sitemap entries."""
    template = _load_template(pages_dir)
    entries: list[dict] = []

    specs = [
        (
            "home-gettingstarted",
            "#/home/gettingstarted",
            "Getting Started | Zoho Books",
            "Getting Started",
            _getting_started_html(),
        ),
        (
            "home-recentupdates",
            "#/home/recentupdates",
            "Recent Updates | Zoho Books",
            "Recent Updates",
            _recent_updates_html(),
        ),
    ]

    for slug, fragment, title, active_tab, content in specs:
        soup = BeautifulSoup(template, "html.parser")
        _set_active_tab(soup, active_tab)
        _replace_dashboard_content(soup, content)

        html_path = pages_dir / f"{slug}.html"
        meta_path = pages_dir / f"{slug}.meta"
        url = f"{app_base}{fragment}" if app_base else fragment

        html_path.write_text(str(soup), encoding="utf-8")
        meta_path.write_text(url, encoding="utf-8")
        entries.append({"slug": slug, "url": url, "title": title})

    return entries


def merge_sitemap(pages_dir: Path, new_entries: list[dict]) -> None:
    path = pages_dir / "sitemap.json"
    sitemap = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing = {item["slug"] for item in sitemap}
    for entry in new_entries:
        if entry["slug"] not in existing:
            sitemap.append(entry)
    path.write_text(json.dumps(sitemap, indent=2), encoding="utf-8")
