"""Analyze cleaned HTML pages with Gemini — one JSON file per page."""

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
CLEANED_DIR = Path("analysis")
OUTPUT_DIR = Path("analysis/page_knowledge")

PROMPT = """You are analyzing a single page from Zoho Books (accounting/invoicing SaaS).

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

def discover_cleaned_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    files = [
        p for p in sorted(root.rglob("*.cleaned.html"))
        if "page_knowledge" not in p.parts
    ]
    if files:
        return files
    return [
        p for p in sorted((root / "cleaned").rglob("*.html"))
        if p.is_file() and "page_knowledge" not in p.parts
    ]


def page_slug(html_path: Path) -> str:
    """app-60073668069-invoices/index.cleaned.html → invoices"""
    name = html_path.parent.name if html_path.name.startswith("index") else html_path.stem
    name = re.sub(r"\.cleaned$", "", name)
    name = re.sub(r"^app-\d+-", "", name)
    return name or html_path.stem.replace(".cleaned", "")


def parse_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def analyze_html(client: genai.Client, html: str) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(html=html[:120000]),
    )
    return parse_json(response.text or "")


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    cleaned_files = discover_cleaned_files(CLEANED_DIR)
    if not cleaned_files:
        raise SystemExit(f"No cleaned HTML found under {CLEANED_DIR}/ — run html_cleaner.py first")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    done = skipped = failed = 0

    for i, html_path in enumerate(cleaned_files, 1):
        slug = page_slug(html_path)
        out_path = OUTPUT_DIR / f"{slug}.json"

        if out_path.exists():
            print(f"  [{i}/{len(cleaned_files)}] skip {slug} (exists)")
            skipped += 1
            continue

        print(f"  [{i}/{len(cleaned_files)}] analyzing {slug}...")
        try:
            html = html_path.read_text(encoding="utf-8")
            result = analyze_html(client, html)
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            done += 1
        except Exception as exc:
            print(f"    ✗ failed: {exc}")
            failed += 1

    print(f"\n✅ Done — {done} saved, {skipped} skipped, {failed} failed → {OUTPUT_DIR}/")


if __name__ == "__main__":
    print("[*] Analyzing cleaned pages with Gemini...")
    main()
