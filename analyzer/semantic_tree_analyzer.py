"""Build semantic UI component trees from cleaned HTML + business context."""

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
MAX_HTML_CHARS = 120_000

PROMPT = """You are an expert UI Architect and Frontend Engineer.

Your task is to analyze the given webpage HTML, screenshot information, and business context and produce a semantic representation of the page.

The goal is NOT to reproduce raw HTML.

The goal is to understand the UI hierarchy and assign stable semantic IDs that future agents can use for React component generation and browser automation.

### Requirements

1. Generate meaningful IDs instead of random IDs.
   Examples:

* sidebar
* header
* search_input
* create_creditnote_button
* invoice_table
* customer_form

2. Build a parent-child hierarchy.

3. Identify the following component types whenever present:

* page
* navigation
* nav_item
* sidebar
* header
* footer
* section
* card
* table
* row
* column
* form
* textbox
* textarea
* dropdown
* checkbox
* radio
* button
* modal
* tabs
* breadcrumb
* chart
* notification

4. Include labels whenever possible.

5. Do not preserve CSS classes or raw HTML attributes.

6. Ignore styling details.

7. The output must represent structure, not appearance.

8. Return ONLY valid JSON.

Schema:

{{
"pageId": "",
"type": "page",
"children": [
{{
"id": "",
"type": "",
"label": "",
"children": []
}}
]
}}

Rules:
- Output ONLY valid JSON. No markdown. No backticks. No explanation.
- Analyze THIS page only. Do not connect to other pages or infer workflows.

HTML:

{html}

Business Context:

{business_json}
"""


def discover_cleaned_files(cleaned_dir: Path) -> list[Path]:
    if not cleaned_dir.is_dir():
        return []
    return sorted(p for p in cleaned_dir.glob("*.html") if p.is_file())


def page_slug(html_path: Path) -> str:
    return html_path.stem


def parse_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def load_business_context(business_path: Path) -> dict:
    if not business_path.exists():
        return {}
    return json.loads(business_path.read_text(encoding="utf-8"))


def analyze_page(
    client: genai.Client,
    html: str,
    business_context: dict,
) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(
            html=html[:MAX_HTML_CHARS],
            business_json=json.dumps(business_context, ensure_ascii=False),
        ),
    )
    return parse_json(response.text or "")


def analyze_all_pages(
    cleaned_dir: str,
    business_dir: str,
    output_dir: str,
) -> dict:
    """Read cleaned HTML + optional business JSON per page; write semantic tree JSON."""
    cleaned_path = Path(cleaned_dir)
    business_path = Path(business_dir)
    output_path = Path(output_dir)

    if not cleaned_path.is_dir():
        raise FileNotFoundError(f"Cleaned HTML directory not found: {cleaned_path}")

    html_files = discover_cleaned_files(cleaned_path)
    if not html_files:
        raise FileNotFoundError(
            f"No cleaned HTML found under {cleaned_path} — run clean first"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env or your environment")

    output_path.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    done = skipped = failed = missing_business = 0

    for i, html_path in enumerate(html_files, 1):
        slug = page_slug(html_path)
        out_path = output_path / f"{slug}.json"
        biz_path = business_path / f"{slug}.json"

        if out_path.exists():
            print(f"  [{i}/{len(html_files)}] skip {slug} (exists)")
            skipped += 1
            continue

        if not biz_path.exists():
            print(f"  [{i}/{len(html_files)}] note: no business_json for {slug} (using {{}})")
            missing_business += 1

        print(f"  [{i}/{len(html_files)}] building semantic tree for {slug}...")
        try:
            html = html_path.read_text(encoding="utf-8")
            business_context = load_business_context(biz_path)
            result = analyze_page(client, html, business_context)
            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"    → {out_path.name}")
            done += 1
        except Exception as exc:
            print(f"    ✗ failed: {exc}")
            failed += 1

    print(
        f"\n✅ Semantic trees: {done} built, {skipped} skipped, "
        f"{failed} failed, {missing_business} without business_json → {output_path}/"
    )
    return {
        "pages_built": done,
        "pages_skipped": skipped,
        "pages_failed": failed,
        "pages_missing_business_json": missing_business,
        "semantic_tree_dir": str(output_path),
    }


def analyze_semantic_tree_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_business_json_dir,
        get_cleaned_html_dir,
        get_semantic_tree_dir,
    )

    create_app_storage(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    business_dir = get_business_json_dir(app_name)
    semantic_tree_dir = get_semantic_tree_dir(app_name)
    return analyze_all_pages(
        str(cleaned_dir),
        str(business_dir),
        str(semantic_tree_dir),
    )
