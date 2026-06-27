"""Build a global application catalog from per-page business_json + semantic_tree."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

load_dotenv()

MODEL = "gemini-2.5-flash"
NAV_TYPES = frozenset({"nav_item", "link", "navigation", "button"})

PROMPT = """You are an expert software architect building an application knowledge graph.

Your task is to analyze ALL page business descriptions and semantic trees of an application and generate a GLOBAL APPLICATION CATALOG that represents the structure and workflows of the application.

This catalog must represent how the application behaves as a system.

---

## PRIMARY GOAL

Generate a SPARSE knowledge graph describing:

• pages
• navigation flows
• shared entities
• multi-page workflows
• logical modules

This is NOT a full connectivity graph of every page.

DO NOT connect every page to every other page.

Only include meaningful, real-world business relationships.

---

## INPUTS

For every page, you are given a pre-summarized object (business context + navigation labels only — not full component trees):

{pages_json}

Application name: {application_name}

---

## MENTAL MODEL

Think of the application as:

pages → interactions → entities → workflows

Examples of workflows:

Quote to Cash:
Quotes → Sales Orders → Invoices → Payments

Vendor Payment:
Bills → Payments → Vendor Credits

Customer Refund:
Credit Notes → Refunds

Build workflows only when there is clear navigation or entity evidence.

---

## OUTPUT SCHEMA

Return JSON using this structure:

{{
  "applicationName": "",
  "pages": [
    {{
      "id": "",
      "title": "",
      "purpose": ""
    }}
  ],
  "relationships": [
    {{
      "from": "",
      "to": "",
      "type": ""
    }}
  ],
  "sharedEntities": [
    {{
      "entity": "",
      "usedBy": []
    }}
  ],
  "workflows": [
    {{
      "name": "",
      "steps": []
    }}
  ],
  "modules": [
    {{
      "id": "",
      "pages": []
    }}
  ]
}}

---

## RELATIONSHIP RULES

Include only meaningful relationships.

Allowed relationship types include:

navigation
entity_reference
workflow_step
sibling_module
reports_from

Do NOT create relationships unless there is evidence.

Example navigation:

Quotes → Sales Orders
Payments → Invoices

Example entity_reference:

Invoices → Customers
Products referenced across inventory and sales pages

---

## MODULE RULES

Group related pages into logical modules.

Examples:

sales
purchases
banking
inventory
reports
configuration

Each module must represent a business domain, not UI layout.

---

## WORKFLOW RULES

Workflows must include ordered steps referencing page ids.

Only include workflows that represent real business processes.

---

## OUTPUT RULES

1. Use stable page IDs from input.
2. Modules must group related pages.
3. Shared entities should connect multiple pages.
4. Relationships must be sparse and meaningful.
5. Do NOT include HTML or UI components.
6. Return ONLY valid JSON.
7. No markdown.
8. No backticks.
9. No explanation.

This catalog will later be used for:

• Browser Agents navigation planning
• React UI generation
• workflow reasoning
"""


def parse_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def slug_from_crawl_slug(crawl_slug: str) -> str:
    return re.sub(r"^app-\d+-", "", crawl_slug)


def build_sitemap_index(sitemap: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for entry in sitemap:
        crawl_slug = entry.get("slug", "")
        flat = slug_from_crawl_slug(crawl_slug)
        index[flat] = entry
        index[crawl_slug] = entry
    return index


def extract_navigation_labels(tree: dict) -> list[dict]:
    """Collect nav-related labels from a semantic tree (deduplicated)."""
    seen: set[tuple[str, str]] = set()
    results: list[dict] = []

    def walk(node: dict) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("type", "")
        label = (node.get("label") or "").strip()
        if node_type in NAV_TYPES and label:
            key = (node_type, label)
            if key not in seen:
                seen.add(key)
                results.append({"label": label, "kind": node_type})
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(tree)
    return results


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compact_page_summary(
    slug: str,
    business_path: Path,
    tree_path: Path,
    sitemap_entry: dict | None = None,
) -> dict:
    business = load_json(business_path)
    tree = load_json(tree_path)

    title = business.get("pageName") or ""
    if not title and sitemap_entry:
        title = sitemap_entry.get("title", "")

    summary: dict = {
        "id": slug,
        "title": title,
        "purpose": business.get("businessPurpose") or business.get("shortSummary") or "",
        "entities": business.get("businessEntities") or [],
        "actions": business.get("mainActions") or [],
        "navigation": extract_navigation_labels(tree),
    }

    if sitemap_entry:
        summary["url"] = sitemap_entry.get("url", "")
        if sitemap_entry.get("title") and not summary["title"]:
            summary["title"] = sitemap_entry["title"]

    return summary


def discover_semantic_tree_files(semantic_tree_dir: Path) -> list[Path]:
    if not semantic_tree_dir.is_dir():
        return []
    return sorted(p for p in semantic_tree_dir.glob("*.json") if p.is_file())


def build_compact_input(
    business_dir: Path,
    semantic_tree_dir: Path,
    sitemap: list[dict],
) -> tuple[list[dict], int]:
    sitemap_index = build_sitemap_index(sitemap)
    tree_files = discover_semantic_tree_files(semantic_tree_dir)
    pages: list[dict] = []
    missing_business = 0

    for tree_path in tree_files:
        slug = tree_path.stem
        business_path = business_dir / f"{slug}.json"
        if not business_path.exists():
            missing_business += 1
        pages.append(
            compact_page_summary(
                slug,
                business_path,
                tree_path,
                sitemap_index.get(slug),
            )
        )

    return pages, missing_business


def build_catalog(client: genai.Client, app_name: str, pages_compact: list[dict]) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(
            application_name=app_name,
            pages_json=json.dumps(pages_compact, indent=2, ensure_ascii=False),
        ),
    )
    result = parse_json(response.text or "")
    if not result.get("applicationName"):
        result["applicationName"] = app_name
    return result


def build_catalog_application(app_name: str) -> dict:
    from pipeline_io import load_sitemap
    from storage.storage_manager import (
        create_app_storage,
        get_app_catalog_dir,
        get_business_json_dir,
        get_metadata_dir,
        get_semantic_tree_dir,
    )

    create_app_storage(app_name)
    business_dir = get_business_json_dir(app_name)
    semantic_tree_dir = get_semantic_tree_dir(app_name)
    catalog_dir = get_app_catalog_dir(app_name)
    catalog_path = catalog_dir / "catalog.json"

    if catalog_path.exists():
        print(f"  skip catalog (exists) → {catalog_path}")
        return {
            "pages_in_catalog": 0,
            "catalog_skipped": True,
            "catalog_path": str(catalog_path),
        }

    tree_files = discover_semantic_tree_files(semantic_tree_dir)
    if not tree_files:
        raise FileNotFoundError(
            f"No semantic trees at {semantic_tree_dir} — run semantic_tree first"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env or your environment")

    sitemap = load_sitemap(get_metadata_dir(app_name))
    pages_compact, missing_business = build_compact_input(
        business_dir,
        semantic_tree_dir,
        sitemap,
    )

    if missing_business:
        print(
            f"  note: {missing_business}/{len(pages_compact)} pages "
            "without business_json (using navigation + sitemap only)"
        )

    print(f"  building catalog from {len(pages_compact)} pages...")
    client = genai.Client(api_key=api_key)
    catalog = build_catalog(client, app_name, pages_compact)

    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"    → {catalog_path.name}")

    return {
        "pages_in_catalog": len(pages_compact),
        "pages_missing_business_json": missing_business,
        "catalog_path": str(catalog_path),
        "modules": len(catalog.get("modules") or []),
        "relationships": len(catalog.get("relationships") or []),
        "workflows": len(catalog.get("workflows") or []),
    }
