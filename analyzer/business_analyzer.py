"""Analyze cleaned HTML with Gemini — one JSON file per page in business_json/."""

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

PROMPT = """You are analyzing a single page from a SaaS application.

Answer these questions using ONLY what is visible in the HTML:
1. What business purpose does this page serve?
2. What actions can users perform?
3. What business entities appear on the page (e.g. invoices, customers, items)?
4. Which user roles would typically use this page?
5. What information is important for a sales demo?

Return JSON only with this exact shape:
{{
  "pageName": "",
  "businessPurpose": "",
  "mainActions": [],
  "businessEntities": [],
  "userRoles": [],
  "importantInformation": [],
  "shortSummary": ""
}}

Rules:
- Output ONLY valid JSON. No markdown. No backticks. No explanation.
- Analyze THIS page only. Do not connect to other pages or infer workflows.
- Keep arrays concise (max 8 items each).
- shortSummary: 2-3 sentences max.

CLEANED HTML:
{html}
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


def analyze_html(client: genai.Client, html: str) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(html=html[:MAX_HTML_CHARS]),
    )
    return parse_json(response.text or "")


def analyze_all_pages(cleaned_dir: str, output_dir: str) -> dict:
    """Read each cleaned HTML file, analyze with Gemini, save JSON. Skips existing."""
    cleaned_path = Path(cleaned_dir)
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
    done = skipped = failed = 0

    for i, html_path in enumerate(html_files, 1):
        slug = page_slug(html_path)
        out_path = output_path / f"{slug}.json"

        if out_path.exists():
            print(f"  [{i}/{len(html_files)}] skip {slug} (exists)")
            skipped += 1
            continue

        print(f"  [{i}/{len(html_files)}] analyzing {slug}...")
        try:
            html = html_path.read_text(encoding="utf-8")
            result = analyze_html(client, html)
            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"    → {out_path.name}")
            done += 1
        except Exception as exc:
            print(f"    ✗ failed: {exc}")
            failed += 1

    print(f"\n✅ Analyzed {done} pages, {skipped} skipped, {failed} failed → {output_path}/")
    return {
        "pages_analyzed": done,
        "pages_skipped": skipped,
        "pages_failed": failed,
        "business_json_dir": str(output_path),
    }


def analyze_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_business_json_dir,
        get_cleaned_html_dir,
    )

    create_app_storage(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    business_dir = get_business_json_dir(app_name)
    return analyze_all_pages(str(cleaned_dir), str(business_dir))
