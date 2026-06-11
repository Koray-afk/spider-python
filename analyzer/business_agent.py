"""Agent 1: page-level business analysis via Gemini + structured JSON."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

from analyzer.html_fact_extractor import extract_page_facts
from analyzer.validator import validate_analysis

load_dotenv()

MODEL = "gemini-2.5-pro"
MAX_HTML_SNIPPET_CHARS = 40_000
ANALYZER_ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ANALYZER_ROOT / "prompts" / "page_analysis_prompt.txt"
SCHEMA_PATH = ANALYZER_ROOT / "schemas" / "page_analysis_schema.json"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def discover_cleaned_files(cleaned_dir: Path) -> list[Path]:
    if not cleaned_dir.is_dir():
        return []
    return sorted(p for p in cleaned_dir.glob("*.html") if p.is_file())


def page_name_from_path(html_path: Path) -> str:
    return html_path.stem


def parse_json_response(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def build_gemini_payload(
    page_facts: dict[str, Any],
    html: str,
    page_file_name: str,
    schema: dict[str, Any],
    *,
    retry: bool = False,
) -> str:
    snippet = html[:MAX_HTML_SNIPPET_CHARS]
    payload = {
        "pageFacts": page_facts,
        "htmlSnippet": snippet,
        "pageFileName": page_file_name,
        "outputSchema": schema,
    }
    if retry:
        payload["retryInstruction"] = (
            "Previous response missed extracted elements. "
            "Include ALL buttons, actionable links, tables, and forms from pageFacts."
        )
    return json.dumps(payload, ensure_ascii=False)


def analyze_page_with_gemini(
    client: genai.Client,
    page_facts: dict[str, Any],
    html: str,
    page_file_name: str,
    *,
    retry: bool = False,
) -> dict[str, Any]:
    prompt = load_prompt()
    schema = load_schema()
    payload = build_gemini_payload(
        page_facts, html, page_file_name, schema, retry=retry
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=f"{prompt}\n\nINPUT:\n{payload}",
    )
    return parse_json_response(response.text or "")


def analyze_single_page(
    client: genai.Client,
    html_path: Path,
) -> dict[str, Any]:
    page_name = page_name_from_path(html_path)
    html = html_path.read_text(encoding="utf-8")
    page_facts = extract_page_facts(html)

    print(f"INPUT FILE: {html_path}")
    print(
        f"  facts: buttons={page_facts['counts']['buttons']} "
        f"tables={page_facts['counts']['tables']} "
        f"forms={page_facts['counts']['forms']}"
    )

    analysis = analyze_page_with_gemini(client, page_facts, html, html_path.name)
    validation = validate_analysis(page_facts, analysis)

    if validation["needsRetry"]:
        print(f"  validation mismatch — retrying {page_name} once")
        print(f"  extracted: {validation['extracted']}")
        print(f"  reported:  {validation['reported']}")
        analysis = analyze_page_with_gemini(
            client, page_facts, html, html_path.name, retry=True
        )
        validation = validate_analysis(page_facts, analysis)

    analysis["_meta"] = {
        "sourceFile": html_path.name,
        "pageFactsCounts": page_facts["counts"],
        "validation": validation,
        "model": MODEL,
    }
    return analysis


def analyze_all_pages(cleaned_dir: str, output_dir: str) -> int:
    """Read cleaned HTML, analyze each page, write business_json. Never touches cleaned HTML."""
    cleaned_path = Path(cleaned_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — add it to .env")

    html_files = discover_cleaned_files(cleaned_path)
    if not html_files:
        raise FileNotFoundError(f"No cleaned HTML files in {cleaned_path}")

    client = genai.Client(api_key=api_key)
    done = failed = 0

    for i, html_path in enumerate(html_files, 1):
        page_name = page_name_from_path(html_path)
        out_path = output_path / f"{page_name}.json"

        print(f"  [{i}/{len(html_files)}] analyzing {page_name}...")
        try:
            result = analyze_single_page(client, html_path)
            if result is None:
                failed += 1
                continue
            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"OUTPUT FILE: {out_path}")
            done += 1
        except Exception as exc:
            print(f"    ✗ failed: {exc}")
            failed += 1

    print(f"\n✅ Analyzed {done} pages → {output_path}/ ({failed} failed)")
    return done


def analyze_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_business_json_dir,
        get_cleaned_html_dir,
    )

    create_app_storage(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    business_dir = get_business_json_dir(app_name)

    if not cleaned_dir.is_dir() or not any(cleaned_dir.glob("*.html")):
        raise FileNotFoundError(
            f"No cleaned HTML at {cleaned_dir}. Run: python main.py clean {app_name}"
        )

    count = analyze_all_pages(str(cleaned_dir), str(business_dir))
    return {"pages_analyzed": count, "business_json_dir": str(business_dir)}
