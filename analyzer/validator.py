"""Validate Gemini output against deterministically extracted PageFacts."""

from __future__ import annotations

from typing import Any


def _actionable_links(links: list[dict]) -> int:
    count = 0
    for link in links:
        text = (link.get("text") or "").strip()
        href = (link.get("href") or "").strip()
        if text and href and not href.startswith("#"):
            count += 1
    return count


def count_extracted_actions(page_facts: dict[str, Any]) -> int:
    buttons = len(page_facts.get("buttons") or [])
    links = _actionable_links(page_facts.get("links") or [])
    tabs = len(page_facts.get("tabs") or [])
    return buttons + links + tabs


def count_reported_clickables(analysis: dict[str, Any]) -> int:
    return len(analysis.get("clickableElements") or [])


def count_extracted_tables(page_facts: dict[str, Any]) -> int:
    return len(page_facts.get("tables") or [])


def count_reported_tables(analysis: dict[str, Any]) -> int:
    return len(analysis.get("tables") or [])


def count_extracted_forms(page_facts: dict[str, Any]) -> int:
    return len(page_facts.get("forms") or [])


def count_reported_forms(analysis: dict[str, Any]) -> int:
    return len(analysis.get("forms") or [])


def _is_major_mismatch(extracted: int, reported: int) -> bool:
    if extracted == 0:
        return False
    if reported == 0:
        return True
    if reported < extracted:
        gap = extracted - reported
        return gap >= max(2, int(extracted * 0.4))
    return False


def validate_analysis(page_facts: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    """Return validation report; needsRetry=True if major element count mismatch."""
    extracted_actions = count_extracted_actions(page_facts)
    reported_clickables = count_reported_clickables(analysis)
    extracted_tables = count_extracted_tables(page_facts)
    reported_tables = count_reported_tables(analysis)
    extracted_forms = count_extracted_forms(page_facts)
    reported_forms = count_reported_forms(analysis)

    clickable_mismatch = _is_major_mismatch(extracted_actions, reported_clickables)
    table_mismatch = _is_major_mismatch(extracted_tables, reported_tables)
    form_mismatch = _is_major_mismatch(extracted_forms, reported_forms)

    return {
        "extracted": {
            "clickableActions": extracted_actions,
            "tables": extracted_tables,
            "forms": extracted_forms,
        },
        "reported": {
            "clickableElements": reported_clickables,
            "tables": reported_tables,
            "forms": reported_forms,
        },
        "mismatches": {
            "clickableElements": clickable_mismatch,
            "tables": table_mismatch,
            "forms": form_mismatch,
        },
        "needsRetry": clickable_mismatch or table_mismatch or form_mismatch,
    }
