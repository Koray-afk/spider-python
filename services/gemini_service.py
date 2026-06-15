import json
import os
import base64
import io
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.5-flash"
_client: genai.Client | None = None
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _prepare_image_bytes(png_path: str) -> bytes:
    """Resize/compress PNG if needed so Gemini can process it."""
    with open(png_path, "rb") as f:
        raw = f.read()
    if len(raw) <= MAX_IMAGE_BYTES:
        return raw
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        img.thumbnail((1280, 1280))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        return raw[:MAX_IMAGE_BYTES]


def _image_part(png_path: str):
    """Helper — reads a PNG and returns a Gemini image part."""
    data = _prepare_image_bytes(png_path)
    return types.Part.from_bytes(data=data, mime_type="image/png")


def analyze_page(png_path: str, url: str) -> str:
    """
    Send a screenshot + URL to Gemini.
    Returns raw JSON string matching PageAnalysis schema.
    Called by: processors/analyze_page.py
    """
    prompt = f"""Analyze this webpage screenshot.

URL: {url}

Return a JSON object with ONLY these fields:
{{
  "pageType": "homepage | pricing | about | contact | etc",
  "purpose": "what this page is trying to achieve",
  "mainCTA": "the primary button or action text",
  "importantSections": ["list", "of", "visible", "sections"],
  "summary": "2-3 sentence summary"
}}

Output ONLY the JSON. No explanation. No markdown. No backticks."""

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=[_image_part(png_path), prompt]
    )

    return response.text


def catalog_page_summary(
    page_slug: str,
    page_url: str,
    element_count: int,
    html_snippet: str,
    png_path: str | None = None,
) -> str:
    """Infer page-level metadata."""
    prompt = f"""Analyze this web app page.

Page slug: {page_slug}
URL: {page_url}
Element count: {element_count}

HTML snippet:
{html_snippet[:40000]}

Return JSON ONLY:
{{
  "page_name": "human readable title",
  "page_purpose": "what this page is for",
  "summary": "2-3 sentences"
}}
No markdown."""

    parts: list[Any] = []
    if png_path and os.path.isfile(png_path):
        parts.append(_image_part(png_path))
    parts.append(prompt)
    response = _get_client().models.generate_content(model=MODEL, contents=parts)
    return response.text


def catalog_element_batch(
    annotated_html: str,
    element_records: list[dict[str, Any]],
    page_slug: str,
    page_url: str,
    png_path: str | None = None,
) -> str:
    """Infer purpose for a batch of elements from annotated HTML."""
    records_json = json.dumps(element_records, indent=2)
    ids = [r.get("id") for r in element_records]
    html_snippet = annotated_html[:80000]

    prompt = f"""Analyze elements on page '{page_slug}' ({page_url}).

Catalog ONLY these element ids: {ids}

Inventory:
{records_json}

Relevant HTML:
{html_snippet}

Return JSON ONLY:
{{
  "elements": [
    {{
      "id": "el-001",
      "tag": "a",
      "text": "label",
      "role": "navigation | action | input | display | filter | menu",
      "purpose": "what it does",
      "expected_action": "navigate | submit | toggle | open_modal | filter | display | unknown | none",
      "expected_target": "slug or null",
      "href": "href or null"
    }}
  ]
}}

Include every id listed. No markdown."""

    parts: list[Any] = [prompt]
    if png_path and os.path.isfile(png_path) and len(element_records) <= 15:
        parts.insert(0, _image_part(png_path))

    response = _get_client().models.generate_content(model=MODEL, contents=parts)
    return response.text


def ask_with_tools(messages: list, tools: list) -> Any:
    """Multi-turn Gemini call with function-calling tools."""
    return _get_client().models.generate_content(
        model=MODEL,
        contents=messages,
        config=types.GenerateContentConfig(tools=tools),
    )


def generate_interaction_js(
    page_slug: str,
    cleaned_html: str,
    interactive_elements: list[dict],
    png_path: str | None = None,
    failures: list[dict] | None = None,
) -> str:
    """Generate vanilla JS IIFE to make offline page interactive."""
    elements_json = json.dumps(interactive_elements[:40], indent=2)
    fail_text = ""
    if failures:
        fail_text = (
            "\n\nThese elements FAILED validation — fix them:\n"
            + json.dumps(failures, indent=2)
        )

    prompt = f"""You are an expert frontend engineer. Write ONE vanilla JavaScript IIFE for offline page "{page_slug}".

RULES (violating breaks the site):
1. NEVER use addEventListener with capture=true (third arg must be false or omitted).
2. NEVER call preventDefault/stopPropagation when e.target.closest('a[href$=".html"]') is truthy — let browser navigate.
3. For a[href$=".html"] links: do NOTHING — stitched href already works.
4. For a[href^="#/"]: preventDefault + show a toast "not recorded yet".
5. [role=tab]: switch active tab + show/hide tabpanel (aria-controls / *-panel id).
6. .dropdown-toggle: toggle .show on .dropdown and .dropdown-menu.
7. .accordion-button / [aria-expanded][aria-controls]: toggle submenu visibility.
8. .btn-primary / buttons with "New|Create|Add": show a simple modal overlay.
9. Use event delegation on document (bubble phase, NOT capture).
10. Output ONLY the IIFE code — no markdown, no explanation.

Interactive elements (data-agent-id):
{elements_json}

Cleaned HTML (context):
{cleaned_html[:50000]}
{fail_text}

Output the complete IIFE starting with (function() {{ and ending with }})();"""

    parts: list[Any] = [prompt]
    if png_path and os.path.isfile(png_path):
        parts.insert(0, _image_part(png_path))

    response = _get_client().models.generate_content(model=MODEL, contents=parts)
    return response.text


def generate_replica(png_path: str, url: str) -> str:
    """
    Send a screenshot to Gemini.
    Returns a complete HTML string that visually replicates the page.
    Called by: replica_generator.py
    """
    prompt = f"""You are an expert frontend developer.

This is a screenshot of: {url}

Generate a COMPLETE, self-contained HTML file that visually replicates 
this page as closely as possible.

Rules:
- Use only HTML + inline CSS + Tailwind CDN
- Match colors, fonts, layout, spacing exactly
- Include all visible text
- Replicate navbar, hero, buttons, sections, footer
- Output ONLY the raw HTML. No explanation. No markdown. No backticks."""

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=[_image_part(png_path), prompt]
    )

    html = response.text

    # Clean if Gemini wraps in markdown
    if "```html" in html:
        html = html.split("```html")[1].split("```")[0].strip()
    elif "```" in html:
        html = html.split("```")[1].split("```")[0].strip()

    return html