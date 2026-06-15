"""Infer expected_action from DOM attributes without calling Gemini."""

from __future__ import annotations

import re
from typing import Any

VALID = {"navigate", "submit", "toggle", "open_modal", "filter", "display", "unknown", "none"}


def _safe(val: str | None, default: str = "unknown") -> str:
    return val if val in VALID else default


def infer_from_record(rec: dict[str, Any], html_snippet: str = "") -> dict[str, Any]:
    """Return {role, purpose, expected_action, expected_target} for one element record."""
    tag = (rec.get("tag") or "").lower()
    text = (rec.get("text") or "").strip()
    href = rec.get("href") or ""
    eid = rec.get("id", "")

    role = "unknown"
    action = "unknown"
    target = None
    purpose = text[:80] or f"{tag} element"

    if tag == "a" and href:
        if href.endswith(".html"):
            role, action, target = "navigation", "navigate", href
            purpose = f"Navigate to {href}"
        elif href.startswith("#/"):
            role, action = "navigation", "navigate"
            target = href.split("?")[0]
            purpose = f"Route {target}"
        else:
            role, action = "navigation", "none"

    elif tag == "button" or (tag in {"div", "span"} and "button" in text.lower()):
        if re.search(r"role=[\"']tab[\"']", html_snippet) or "tab" in text.lower()[:20]:
            role, action = "menu", "toggle"
            purpose = f"Switch tab: {text}"
        elif re.search(r"dropdown-toggle", html_snippet):
            role, action = "menu", "toggle"
            purpose = "Open dropdown menu"
        elif re.search(r"accordion-button|aria-expanded", html_snippet):
            role, action = "menu", "toggle"
            purpose = "Expand/collapse section"
        elif re.search(r"\b(new|create|add)\b", text, re.I):
            role, action = "action", "open_modal"
            purpose = f"Open form: {text}"
        elif re.search(r"\b(save|submit)\b", text, re.I):
            role, action = "action", "submit"
            purpose = f"Submit: {text}"
        else:
            role, action = "action", "toggle"
            purpose = text or "Button action"

    elif tag in {"input", "select", "textarea"}:
        role, action = "input", "none"
        purpose = f"Form field: {text or tag}"

    # HTML snippet lookup for elements identified only by id
    if action == "unknown" and eid and html_snippet:
        pat = rf'data-agent-id="{re.escape(eid)}"[^>]*'
        m = re.search(pat, html_snippet)
        if m:
            chunk = html_snippet[m.start() : m.start() + 400]
            if 'role="tab"' in chunk or "nav-link" in chunk:
                role, action = "menu", "toggle"
            elif "dropdown-toggle" in chunk:
                role, action = "menu", "toggle"
            elif "accordion-button" in chunk or "aria-expanded" in chunk:
                role, action = "menu", "toggle"
            elif tag == "a" and 'href="' in chunk:
                hm = re.search(r'href="([^"]+)"', chunk)
                if hm:
                    href = hm.group(1)
                    if href.endswith(".html"):
                        role, action, target = "navigation", "navigate", href

    return {
        "role": role,
        "purpose": purpose,
        "expected_action": _safe(action),
        "expected_target": target,
    }
