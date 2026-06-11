"""Assign stable data-agent-id attributes to meaningful DOM nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass

# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup, Tag

CATALOG_TAGS = {
    "a", "button", "input", "select", "textarea", "label",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "nav", "form", "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "img", "svg",
}


@dataclass
class ElementRecord:
    id: str
    tag: str
    text: str
    href: str | None


def _visible_text(tag: Tag) -> str:
    text = tag.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)[:200]


def _is_meaningful(tag: Tag) -> bool:
    if tag.name in CATALOG_TAGS:
        if tag.name in {"input", "img"}:
            return bool(tag.get("type") != "hidden" or tag.get("alt") or tag.get("src"))
        if tag.name in {"a", "button"}:
            return bool(_visible_text(tag) or tag.get("href") or tag.get("aria-label"))
        return True
    if tag.name in {"div", "span"}:
        if tag.get("role") in {"button", "link", "tab", "menuitem"}:
            return True
        if tag.get("onclick") or tag.get("href"):
            return True
        if _visible_text(tag) and len(_visible_text(tag)) >= 2:
            return bool(tag.find_parent(["nav", "form", "table"]))
    return False


def assign_element_ids(html: str, prefix: str = "el") -> tuple[str, list[ElementRecord]]:
    """Inject data-agent-id on catalog-worthy nodes. Returns (html, records)."""
    soup = BeautifulSoup(html or "", "html.parser")
    records: list[ElementRecord] = []
    counter = 1

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        if tag.get("data-agent-id"):
            continue
        if not _is_meaningful(tag):
            continue
        # Skip nested duplicates: prefer leaf interactive nodes
        if tag.name in {"div", "span"} and tag.find(CATALOG_TAGS):
            child_interactive = tag.find(["a", "button", "input", "select"])
            if child_interactive and child_interactive != tag:
                continue

        element_id = f"{prefix}-{counter:03d}"
        counter += 1
        tag["data-agent-id"] = element_id
        records.append(
            ElementRecord(
                id=element_id,
                tag=tag.name,
                text=_visible_text(tag),
                href=tag.get("href"),
            )
        )

    if soup.html:
        return str(soup), records
    body = soup.body.decode_contents() if soup.body else str(soup)
    return body, records
