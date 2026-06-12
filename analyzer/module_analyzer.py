"""Organize the application into high-level business domain modules."""

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

PROMPT = """You are an expert ERP architect and business domain analyst.

Your task is to organize the application into high-level business modules.

Inputs:

1. Catalog information.
2. Existing workflows.
3. Pages and their purposes.
4. Shared entities.

Think like a business consultant organizing departments within a company.

Examples of modules include:

- Sales
- Purchases
- Inventory
- Banking
- Payroll
- Reports
- Settings
- CRM
- Projects

A module represents a major business capability and should contain:

- Related pages.
- Related workflows.
- Important entities.
- Responsibilities.
- Relationships to other modules.

DO NOT organize based on UI layout.

DO NOT organize based on folders.

Think in terms of business domains.

Examples:

Sales Module:
    Contacts
    Quotes
    Sales Orders
    Delivery Challans
    Invoices
    Payments Received
    Credit Notes

Purchase Module:
    Vendors
    Bills
    Purchase Orders
    Payments Made

Inventory Module:
    Items
    Warehouses
    Stock Adjustments

Payroll Module:
    Employees
    Salary Components
    Attendance
    Tax Forms

Rules:

1. Group pages that naturally belong together.
2. Group workflows under their owning module.
3. Avoid excessive overlap between modules.
4. Use stable IDs.
5. Describe the responsibility of each module.
6. Identify key business entities managed by the module.
7. Identify dependencies between modules.
8. Return only valid JSON.
9. Think at the application level, not page level.
10. Create 5-15 modules maximum.

---

## INPUTS

Application catalog (pages, relationships, shared entities):

{catalog_json}

Existing workflows:

{workflows_json}

---

## OUTPUT

Return JSON using this exact structure:

{{
  "applicationName": "",

  "modules": [
    {{
      "id": "",
      "name": "",
      "purpose": "",

      "entities": [],

      "pages": [],

      "workflows": [],

      "dependsOnModules": [],

      "providesCapabilities": []
    }}
  ]
}}

Rules:
- Return ONLY valid JSON. No markdown. No backticks. No explanation.
- Use stable snake_case IDs (e.g. sales, purchases, inventory).
- Pages must reference real page IDs from the catalog.
- Workflows must reference real workflow IDs from the workflows input.
- Each module should have a clear, distinct purpose.
- dependsOnModules must reference other module IDs in this output.
"""


def parse_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def build_modules(
    client: genai.Client,
    catalog: dict,
    workflows: list,
) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(
            catalog_json=json.dumps(catalog, indent=2, ensure_ascii=False),
            workflows_json=json.dumps(workflows, indent=2, ensure_ascii=False),
        ),
    )
    result = parse_json(response.text or "")
    if not result.get("applicationName") and catalog.get("applicationName"):
        result["applicationName"] = catalog["applicationName"]
    return result


def build_modules_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_app_catalog_dir,
        get_modules_path,
        get_workflows_path,
    )

    create_app_storage(app_name)
    catalog_dir = get_app_catalog_dir(app_name)
    catalog_path = catalog_dir / "catalog.json"
    workflows_path = get_workflows_path(app_name)
    modules_path = get_modules_path(app_name)

    if modules_path.exists():
        print(f"  skip modules (exists) → {modules_path}")
        return {
            "modules_skipped": True,
            "modules_path": str(modules_path),
        }

    if not catalog_path.exists():
        raise FileNotFoundError(
            f"catalog.json not found at {catalog_path} — run catalog first"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env or your environment")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    workflows: list = []
    if workflows_path.exists():
        workflows = json.loads(workflows_path.read_text(encoding="utf-8"))
        print(f"  loaded {len(workflows)} workflows from workflows.json")
    else:
        print("  note: workflows.json not found — using catalog data only")

    page_count = len(catalog.get("pages") or [])
    print(f"  organizing {page_count} pages into business modules...")

    client = genai.Client(api_key=api_key)
    result = build_modules(client, catalog, workflows)

    module_count = len(result.get("modules") or [])
    catalog_dir.mkdir(parents=True, exist_ok=True)
    modules_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"    → {modules_path.name} ({module_count} modules)")

    return {
        "modules_discovered": module_count,
        "modules_path": str(modules_path),
    }
