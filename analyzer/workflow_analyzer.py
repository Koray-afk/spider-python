"""Discover rich ERP business workflows from catalog.json + business_json/."""

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

PROMPT = """You are an expert ERP consultant and business process architect.

Your task is to discover business workflows across the application.

Think in terms of real-world business processes rather than pages.

Examples:

Quote To Cash:

Customer
→ Quote
→ Sales Order
→ Delivery Challan
→ Invoice
→ Payment Received

Customer Refund:

Customer
→ Invoice
→ Credit Note

Vendor Management:

Vendor
→ Bill
→ Payment Made

Inventory Management:

Item
→ Inventory
→ Sales Order
→ Invoice

Rules:

1. Focus on business processes.
2. Ignore low-level UI details.
3. Steps should represent meaningful transitions.
4. Include involved entities.
5. Include entry page and exit page.
6. Generate stable workflow IDs.
7. Infer dependencies between workflows.
8. Return only valid JSON.

---

## INPUTS

Application catalog (pages, relationships, modules, shallow workflows):

{catalog_json}

Page business context:

{pages_json}

---

## OUTPUT

Return a JSON array where each item follows this schema exactly:

[
{{
"id": "",
"name": "",
"purpose": "",
"entities": [],
"entryPage": "",
"exitPage": "",
"steps": [
{{
"page": "",
"action": "",
"nextPage": ""
}}
]
}}
]

Rules:
- Return ONLY a valid JSON array.
- No markdown. No backticks. No explanation.
- Use stable snake_case IDs (e.g. quote_to_cash, customer_refund).
- Steps must reference real page IDs from the catalog.
- The last step's nextPage should be empty string or null.
- Include all meaningful workflows you can discover.
"""


def parse_json(text: str) -> list:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    result = json.loads(text)
    if isinstance(result, dict) and "workflows" in result:
        return result["workflows"]
    return result


def load_business_summaries(business_dir: Path) -> list[dict]:
    """Load compact per-page business context from business_json/."""
    if not business_dir.is_dir():
        return []
    pages = []
    for path in sorted(business_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            pages.append({
                "id": path.stem,
                "title": data.get("pageName", ""),
                "purpose": data.get("businessPurpose") or data.get("shortSummary") or "",
                "entities": data.get("businessEntities") or [],
                "actions": data.get("mainActions") or [],
            })
        except Exception:
            pass
    return pages


def build_workflows(
    client: genai.Client,
    catalog: dict,
    pages_compact: list[dict],
) -> list[dict]:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(
            catalog_json=json.dumps(catalog, indent=2, ensure_ascii=False),
            pages_json=json.dumps(pages_compact, indent=2, ensure_ascii=False),
        ),
    )
    return parse_json(response.text or "")


def build_workflows_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_app_catalog_dir,
        get_business_json_dir,
        get_workflows_path,
    )

    create_app_storage(app_name)
    catalog_dir = get_app_catalog_dir(app_name)
    catalog_path = catalog_dir / "catalog.json"
    workflows_path = get_workflows_path(app_name)

    if workflows_path.exists():
        print(f"  skip workflows (exists) → {workflows_path}")
        return {
            "workflows_skipped": True,
            "workflows_path": str(workflows_path),
        }

    if not catalog_path.exists():
        raise FileNotFoundError(
            f"catalog.json not found at {catalog_path} — run catalog first"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env or your environment")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    business_dir = get_business_json_dir(app_name)
    pages_compact = load_business_summaries(business_dir)

    if not pages_compact:
        print("  note: no business_json found — using catalog data only")

    print(f"  discovering workflows from catalog ({len(catalog.get('pages', []))} pages)...")
    client = genai.Client(api_key=api_key)
    workflows = build_workflows(client, catalog, pages_compact)

    catalog_dir.mkdir(parents=True, exist_ok=True)
    workflows_path.write_text(
        json.dumps(workflows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"    → {workflows_path.name} ({len(workflows)} workflows)")

    return {
        "workflows_discovered": len(workflows),
        "workflows_path": str(workflows_path),
    }
