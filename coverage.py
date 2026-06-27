"""Audit crawl + stitch coverage — find dead buttons and missing routes."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from stitcher_v1 import _build_route_index, _norm_route
from storage.storage_manager import get_crawl_dir, get_stitched_dir


def audit_app(app_name: str) -> dict:
    crawl = get_crawl_dir(app_name)
    stitched = get_stitched_dir(app_name)
    if not crawl.exists():
        raise FileNotFoundError(f"No crawl data for '{app_name}'")

    valid = {d.name for d in crawl.iterdir() if d.is_dir()}
    sitemap_path = crawl.parent / "metadata" / "sitemap.json"
    sitemap = json.loads(sitemap_path.read_text()) if sitemap_path.exists() else []
    route_index = _build_route_index(list(crawl.iterdir()), sitemap, valid)

    missing_routes: Counter[str] = Counter()
    nav_edges = nav_resolved = 0
    for page in crawl.iterdir():
        if not page.is_dir():
            continue
        nav_path = page / "navigations.json"
        if not nav_path.exists():
            continue
        for nav in json.loads(nav_path.read_text()):
            nav_edges += 1
            slug = nav.get("target_slug", "")
            if slug in valid:
                nav_resolved += 1
                continue
            url = nav.get("target_url", "")
            frag = urlparse(url).fragment
            route = _norm_route("#" + frag if frag else "")
            missing_routes[route or slug] += 1

    total_btns = wired_ui = wired_go = wired_tab = wired_acc = 0
    unresolved_anchors = 0
    unwired_dropdown_pages: list[dict] = []

    if stitched.exists():
        for page in stitched.iterdir():
            if not page.is_dir() or not (page / "page.html").exists():
                continue
            html = (page / "page.html").read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for el in soup.select(
                "button, [role='button'], .dropdown-toggle, input[type='submit'], input[type='button']"
            ):
                total_btns += 1
                if el.get("data-stitch-ui-id"):
                    wired_ui += 1
                elif el.get("data-stitch-go"):
                    wired_go += 1
                elif el.get("data-stitch-tab-id"):
                    wired_tab += 1
                elif el.get("data-stitch-accordion"):
                    wired_acc += 1
            unresolved_anchors += len(soup.select("a[data-stitch-unresolved]"))
            dd = len(soup.select('[aria-haspopup="true"], .dropdown-toggle'))
            ui = len(soup.select("[data-stitch-ui-id]"))
            if dd > ui:
                unwired_dropdown_pages.append(
                    {"slug": page.name, "dropdown_triggers": dd, "wired": ui, "gap": dd - ui}
                )

    interactions_total = interactions_bound = 0
    for page in crawl.iterdir():
        if not page.is_dir():
            continue
        ix_path = page / "interactions" / "interactions.json"
        if not ix_path.exists():
            continue
        for item in json.loads(ix_path.read_text()):
            if not item.get("interaction_path"):
                continue
            interactions_total += 1
            stitched_page = stitched / page.name / "page.html"
            if stitched_page.exists():
                html = stitched_page.read_text(encoding="utf-8", errors="ignore")
                ui_id = item.get("ui_id") or ""
                if ui_id and ui_id in html:
                    interactions_bound += 1

    return {
        "pages_crawled": len(valid),
        "nav_edges": nav_edges,
        "nav_resolved": nav_resolved,
        "missing_routes": missing_routes,
        "route_index_size": len(route_index),
        "total_buttons": total_btns,
        "wired_ui": wired_ui,
        "wired_go": wired_go,
        "wired_tab": wired_tab,
        "wired_acc": wired_acc,
        "unresolved_anchors": unresolved_anchors,
        "unwired_dropdown_pages": sorted(unwired_dropdown_pages, key=lambda r: -r["gap"])[:15],
        "interactions_total": interactions_total,
    }


def print_audit(app_name: str) -> None:
    r = audit_app(app_name)
    wired = r["wired_ui"] + r["wired_go"] + r["wired_tab"] + r["wired_acc"]
    dead_approx = max(0, r["total_buttons"] - wired)

    print(f"Coverage audit — {app_name}")
    print(f"  Pages crawled:        {r['pages_crawled']}")
    print(f"  Routes in index:      {r['route_index_size']}")
    print(f"  Nav edges:            {r['nav_edges']} ({r['nav_resolved']} resolved, "
          f"{r['nav_edges'] - r['nav_resolved']} missing page)")
    print(f"  Interactions captured:{r['interactions_total']}")
    print()
    print(f"  Buttons / triggers:   {r['total_buttons']}")
    print(f"    wired (interaction):{r['wired_ui']}")
    print(f"    wired (navigation): {r['wired_go']}")
    print(f"    wired (tabs):       {r['wired_tab']}")
    print(f"    wired (accordion):  {r['wired_acc']}")
    print(f"    ~dead (unwired):    {dead_approx}")
    print(f"  Dead sidebar links:   {r['unresolved_anchors']} (uncrawled routes)")
    print()

    if r["missing_routes"]:
        print("Top missing routes (add to seed_url_patterns in config.py):")
        for route, cnt in r["missing_routes"].most_common(12):
            print(f"  {cnt:3d}x  {route}")
        print()

    if r["unwired_dropdown_pages"]:
        print("Pages with most unwired dropdowns:")
        for row in r["unwired_dropdown_pages"][:8]:
            print(f"  {row['slug']}: {row['dropdown_triggers']} triggers, {row['wired']} wired "
                  f"({row['gap']} dead)")
        print()

    print("How to fix dead buttons:")
    print("  1. Raise max_pages_post_auth + add seed_url_patterns in config.py")
    print("  2. Re-crawl:  python main.py crawl-postauth", app_name)
    print("  3. Reconcile:  python main.py reconcile", app_name)
    print("  4. Re-stitch:  python main.py stitch", app_name)
