"""Deterministic PageFacts extraction before Gemini analysis."""

from __future__ import annotations

import re
from typing import Any

# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup, Tag


def _text(tag: Tag | None) -> str:
    if not tag:
        return ""
    return re.sub(r"\s+", " ", tag.get_text(strip=True))


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def extract_page_facts(html: str) -> dict[str, Any]:
    """Extract structured PageFacts from cleaned HTML."""
    soup = BeautifulSoup(html or "", "html.parser")

    title_tag = soup.find("title")
    title = _text(title_tag)
    if not title:
        h1 = soup.find("h1")
        title = _text(h1)

    headings: list[dict[str, str]] = []
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            text = _text(tag)
            if text:
                headings.append({"level": f"h{level}", "text": text})

    buttons: list[dict[str, str]] = []
    for tag in soup.find_all("button"):
        label = _text(tag)
        if label:
            buttons.append({"label": label, "type": tag.get("type", "button")})

    links: list[dict[str, str]] = []
    for tag in soup.find_all("a", href=True):
        label = _text(tag)
        href = tag.get("href", "")
        if label or href:
            links.append({"text": label or href, "href": href})

    labels: list[str] = []
    for tag in soup.find_all("label"):
        text = _text(tag)
        if text:
            labels.append(text)

    navigation: list[str] = []
    for nav in soup.find_all("nav"):
        for item in nav.find_all(["a", "button", "li"]):
            text = _text(item)
            if text and len(text) < 120:
                navigation.append(text)
    navigation = _unique(navigation)

    tabs: list[str] = []
    for tag in soup.find_all(["button", "a", "li"]):
        text = _text(tag)
        if not text:
            continue
        parent_text = _text(tag.parent) if tag.parent else ""
        if re.search(r"\btab\b", text, re.I) or (
            parent_text and re.search(r"\btab\b", parent_text, re.I)
        ):
            tabs.append(text)
    tabs = _unique(tabs)

    dropdown_labels: list[str] = []
    for select in soup.find_all("select"):
        name = select.get("name", "") or _text(select.find_previous("label"))
        options = [_text(opt) for opt in select.find_all("option") if _text(opt)]
        if name or options:
            dropdown_labels.append(name or "select")
            dropdown_labels.extend(options)
    dropdown_labels = _unique(dropdown_labels)

    badges: list[str] = []
    for tag in soup.find_all(["span", "small", "p"]):
        text = _text(tag)
        if not text or len(text) > 40:
            continue
        if re.search(r"\b(new|beta|pro|draft|paid|overdue|active|pending)\b", text, re.I):
            badges.append(text)
    badges = _unique(badges)

    forms: list[dict[str, Any]] = []
    for form in soup.find_all("form"):
        form_name = form.get("name", "") or form.get("id", "") or "form"
        fields: list[dict[str, str]] = []
        for field in form.find_all(["input", "select", "textarea"]):
            field_type = field.get("type", field.name)
            field_name = (
                field.get("name", "")
                or field.get("id", "")
                or _text(field.find_previous("label"))
            )
            placeholder = field.get("placeholder", "")
            label = _text(field.find_previous("label"))
            fields.append(
                {
                    "fieldName": field_name or label or placeholder or field_type,
                    "fieldType": field_type,
                    "label": label,
                    "placeholder": placeholder,
                }
            )
        forms.append({"formName": form_name, "fields": fields})

    tables: list[dict[str, Any]] = []
    for i, table in enumerate(soup.find_all("table"), 1):
        caption = _text(table.find("caption"))
        headers = [_text(th) for th in table.find_all("th") if _text(th)]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [_text(td) for td in first_row.find_all("td") if _text(td)]
        table_name = caption or f"table_{i}"
        tables.append({"tableName": table_name, "columns": headers})

    return {
        "title": title,
        "headings": headings,
        "buttons": buttons,
        "links": links,
        "forms": forms,
        "labels": labels,
        "tables": tables,
        "navigation": navigation,
        "badges": badges,
        "tabs": tabs,
        "dropdownLabels": dropdown_labels,
        "counts": {
            "buttons": len(buttons),
            "links": len(links),
            "forms": len(forms),
            "tables": len(tables),
            "headings": len(headings),
        },
    }
