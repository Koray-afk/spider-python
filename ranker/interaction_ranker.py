"""LLM-powered interaction ranker.

Calls Gemini once per page to select and type-tag the top N most important
clickable candidates from the discovered list before the crawler clicks them.
Falls back to the original list on any error so the crawler is never blocked.
"""

from __future__ import annotations

import json
import os
import re

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.5-flash"

PROMPT = """Page: "{page_title}"
URL:  "{page_url}"

Below is a numbered list of clickable UI elements discovered on this page.
Each entry shows: index, label, HTML tag, and CSS classes.

{numbered_candidates}

Task:
Select the top {top_n} most important elements a user would interact with during
a sales demo of this SaaS application.

Exclusion rules (never pick these):
- Duplicate header chrome: "Navigate To", "Show dropdown menu" appearing more than once
- Notification bells, user avatars, icon-only buttons with no label
- Sidebar accordion toggles (label matches a module name like "Items", "Sales", "Purchases", etc.)
- Collapse/Expand buttons
- Labels exactly matching: "Subscribe", "testing", "TAKE A LIVE PRODUCT TOUR", "button", "div"

Preference rules (pick these first):
- Primary CTAs: "New", "Save", "Create", "Add"
- Filter dropdowns: fiscal year, date range, status, category pickers
- Modal triggers: "Delete", "More Actions", "Advanced Search"
- Tab switches that reveal page sections (role="tab" or className contains "nav-link")
- Table action menus: per-row action buttons

For each selected element, classify its interaction type:
- "navigation": clicking will navigate the browser to a different page
- "tab_switch": toggles or reveals a section within the current page
- "interaction": opens a popup, modal, dropdown, or drawer without navigating

Return ONLY a valid JSON array — no markdown, no backticks, no explanation:
[
  {{"index": <original_index>, "type": "navigation|tab_switch|interaction"}},
  ...
]"""


def _build_numbered_list(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates):
        label = (c.get("label") or "").strip() or c.get("elementType", "")
        tag = c.get("elementType", "")
        cls = (c.get("className") or "").strip()
        cid = (c.get("id") or "").strip()
        parts = [f"{i}. [{tag}]", f'label="{label}"']
        if cid:
            parts.append(f'id="{cid}"')
        if cls:
            parts.append(f'class="{cls[:80]}"')
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _parse_response(text: str) -> list[dict]:
    text = text.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return json.loads(text.strip())


def rank_candidates(
    page_title: str,
    page_url: str,
    candidates: list[dict],
    *,
    top_n: int = 8,
) -> list[dict]:
    """Return up to top_n candidates ranked by LLM importance.

    Each returned candidate is the original dict (with all Playwright-needed
    fields intact) plus an added ``llm_type`` key.

    Falls back to returning the original list unchanged on any error.
    """
    if not candidates:
        return candidates

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return candidates

    try:
        from google import genai  # pyrefly: ignore [missing-import]

        numbered = _build_numbered_list(candidates)
        prompt = PROMPT.format(
            page_title=page_title,
            page_url=page_url,
            numbered_candidates=numbered,
            top_n=top_n,
        )

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=MODEL, contents=prompt)
        ranked_raw = _parse_response(response.text or "[]")

        results: list[dict] = []
        seen_indices: set[int] = set()
        for item in ranked_raw:
            idx = item.get("index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(candidates):
                continue
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            candidate = dict(candidates[idx])
            candidate["llm_type"] = item.get("type", "interaction")
            results.append(candidate)
            if len(results) >= top_n:
                break

        if not results:
            print("[RANK] LLM returned no valid indices — using full candidate list")
            return candidates

        return results

    except Exception as exc:
        print(f"[RANK] LLM ranking failed ({exc}) — using full candidate list")
        return candidates
