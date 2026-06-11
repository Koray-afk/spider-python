"""Compress detailed semantic trees into high-level React component trees."""

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
MAX_SEMANTIC_TREE_CHARS = 120_000

PROMPT = """You are an expert Frontend Architect and React component designer.

Your task is to transform a detailed semantic tree into a higher-level component tree suitable for React component generation.

The input semantic tree contains thousands of low-level nodes.

Your job is to compress these nodes into meaningful reusable components.

Think like a senior frontend engineer.

Examples:

Do NOT preserve:

* labels
* descriptions
* helper text
* icons
* checkboxes used only for settings
* decorative nodes
* unnecessary wrappers

Combine low-level nodes into higher-level components such as:

* Sidebar
* Header
* Toolbar
* Footer
* SearchBar
* Table
* DataGrid
* Form
* Modal
* Tabs
* Card
* Chart
* NotificationPanel
* ChatPanel
* UserProfileCard
* FilterPanel
* Pagination
* DashboardSection

Rules:

1. Preserve business meaning.
2. Remove noisy implementation details.
3. Group related elements together.
4. Generate stable semantic IDs.

Bad IDs:

node_234
wrapper_52

Good IDs:

customer_form
invoice_table
sidebar
global_search_modal
create_invoice_button
payment_card

Prefer component hierarchy over DOM hierarchy.

Return ONLY valid JSON.

Schema:

{{
"pageId": "",

"components":[
{{
"id":"",
"type":"",
"purpose":"",
"children":[]
}}
]
}}

Think in terms of React components rather than HTML elements.

The output should contain tens of components, not thousands of nodes.

The component tree should be suitable for future React generation, Browser Agents, and application understanding.

Semantic Tree:

{semantic_tree_json}
"""


def discover_semantic_tree_files(semantic_tree_dir: Path) -> list[Path]:
    if not semantic_tree_dir.is_dir():
        return []
    return sorted(p for p in semantic_tree_dir.glob("*.json") if p.is_file())


def parse_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def compress_tree(client: genai.Client, semantic_tree: dict) -> dict:
    tree_json = json.dumps(semantic_tree, ensure_ascii=False)
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(semantic_tree_json=tree_json[:MAX_SEMANTIC_TREE_CHARS]),
    )
    return parse_json(response.text or "")


def compress_all_pages(semantic_tree_dir: str, output_dir: str) -> dict:
    """Read each semantic tree JSON; write compressed component tree JSON."""
    input_path = Path(semantic_tree_dir)
    output_path = Path(output_dir)

    if not input_path.is_dir():
        raise FileNotFoundError(f"Semantic tree directory not found: {input_path}")

    tree_files = discover_semantic_tree_files(input_path)
    if not tree_files:
        raise FileNotFoundError(
            f"No semantic trees found under {input_path} — run semantic_tree first"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env or your environment")

    output_path.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    done = skipped = failed = 0

    for i, tree_path in enumerate(tree_files, 1):
        slug = tree_path.stem
        out_path = output_path / f"{slug}.json"

        if out_path.exists():
            print(f"  [{i}/{len(tree_files)}] skip {slug} (exists)")
            skipped += 1
            continue

        print(f"  [{i}/{len(tree_files)}] compressing component tree for {slug}...")
        try:
            semantic_tree = json.loads(tree_path.read_text(encoding="utf-8"))
            result = compress_tree(client, semantic_tree)
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
        f"\n✅ Component trees: {done} built, {skipped} skipped, "
        f"{failed} failed → {output_path}/"
    )
    return {
        "pages_built": done,
        "pages_skipped": skipped,
        "pages_failed": failed,
        "component_tree_dir": str(output_path),
    }


def compress_component_tree_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_component_tree_dir,
        get_semantic_tree_dir,
    )

    create_app_storage(app_name)
    semantic_tree_dir = get_semantic_tree_dir(app_name)
    component_tree_dir = get_component_tree_dir(app_name)
    return compress_all_pages(str(semantic_tree_dir), str(component_tree_dir))
