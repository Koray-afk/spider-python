import os
import base64
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


def _image_part(png_path: str):
    """Helper — reads a PNG and returns a Gemini image part."""
    with open(png_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return types.Part.from_bytes(
        data=base64.b64decode(data),
        mime_type="image/png"
    )


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

    response = client.models.generate_content(
        model=MODEL,
        contents=[_image_part(png_path), prompt]
    )

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

    response = client.models.generate_content(
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