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

You are selecting interactive elements for a sales demo prototype.

Below is a numbered list of clickable UI elements discovered on this page.
Each entry shows: index, label, HTML tag, accessible name/role, page region,
states, and CSS classes when available.

{numbered_candidates}

MANDATORY — always include these regardless of the limit:
- Any element that is a tab switch (role="tab", or className contains "nav-link",
  or it toggles/reveals a section within the current page) → ALWAYS include ALL of them
- Any element whose label contains: "Getting Started", "Recent Updates", "Dashboard",
  "Overview", "Summary", "Transactions", "History", "Comments", "Mails", "Statement"

THEN fill the remaining slots (up to {top_n} total) with, in this priority order:
1. Primary CTA buttons: "New", "Create", "Add", "Import"
2. Dropdown filters: date range, fiscal year, status
3. Popover triggers: amount breakdowns, charts
4. Everything else

NEVER include:
- Settings, Help, Notifications, Profile
- Search bars
- Pagination controls
- Language/theme toggles

For each selected element, classify its interaction type:
- "navigation": clicking will navigate the browser to a different page
- "tab_switch": toggles or reveals a section within the current page
- "interaction": opens a popup, modal, dropdown, or drawer without navigating

Return ONLY a valid JSON array — no markdown, no backticks, no explanation.
Order the array by priority, and ALL "tab_switch" elements MUST appear first:
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
        ax_name = (c.get("ax_name") or "").strip()
        ax_role = (c.get("ax_role") or "").strip()
        region = (c.get("region") or "").strip()
        states = c.get("ax_states") or []
        parts = [f"{i}. [{tag}]", f'label="{label}"']
        if ax_name and ax_name.lower() != label.lower():
            parts.append(f'ax_name="{ax_name}"')
        if ax_role:
            parts.append(f'role="{ax_role}"')
        if region:
            parts.append(f'region="{region}"')
        if states:
            parts.append(f'states="{",".join(states)}"')
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


def _candidate_key(c: dict) -> tuple:
    return (
        (c.get("selector") or "").strip(),
        (c.get("label") or "").strip(),
        (c.get("id") or "").strip(),
    )


def _inject_mandatory_labels(
    candidates: list[dict],
    ranked: list[dict],
    *,
    top_n: int,
    mandatory_labels: list[str] | None,
) -> list[dict]:
    """Ensure tab/detail labels are ranked even if the LLM skipped them."""
    if not mandatory_labels:
        return ranked[:top_n]

    seen_keys = {_candidate_key(r) for r in ranked}
    injected: list[dict] = []
    for c in candidates:
        label = (c.get("label") or "").strip()
        if not label:
            continue
        label_lower = label.lower()
        if not any(m.lower() in label_lower for m in mandatory_labels):
            continue
        key = _candidate_key(c)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        item = dict(c)
        item["llm_type"] = item.get("llm_type") or "tab_switch"
        injected.append(item)

    merged = injected + ranked
    return merged[:top_n]


def rank_candidates(
    page_title: str,
    page_url: str,
    candidates: list[dict],
    *,
    top_n: int = 15,
    mandatory_labels: list[str] | None = None,
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
        return _inject_mandatory_labels(
            candidates, candidates[:top_n], top_n=top_n, mandatory_labels=mandatory_labels
        )

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
            return _inject_mandatory_labels(
                candidates, candidates[:top_n], top_n=top_n, mandatory_labels=mandatory_labels
            )

        return _inject_mandatory_labels(
            candidates, results, top_n=top_n, mandatory_labels=mandatory_labels
        )

    except Exception as exc:
        print(f"[RANK] LLM ranking failed ({exc}) — using full candidate list")
        return _inject_mandatory_labels(
            candidates, candidates[:top_n], top_n=top_n, mandatory_labels=mandatory_labels
        )
