"""Prepare crawled HTML for LLM analysis without modifying source files."""

from __future__ import annotations

import re
from pathlib import Path

# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup, Comment, Tag

REMOVE_TAGS = {
    "script", "style", "noscript", "iframe", "canvas", "meta", "link",
}
STRIP_ATTRS = {"style", "tabindex", "role"}
# Keep class/id on icon-bearing elements so LLM can infer meaning from labels + icons.
ICON_TAGS = { "path", "i",}
KEEP_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "button", "input", "select",
    "textarea", "label", "table", "thead", "tbody", "tr", "th", "td", "caption",
    "nav", "form", "ul", "ol", "li", "img", "svg", "path", "i", "use",
}


def _is_icon_element(tag: Tag) -> bool:
    if tag.name in ICON_TAGS:
        return True
    classes = tag.get("class") or []
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
    return any(
        token in class_str.lower()
        for token in ("icon", "zgs18", "zgs19", "glyph", "fa-", "material")
    )


def _should_strip_attr(tag: Tag, attr: str) -> bool:
    if attr in STRIP_ATTRS:
        return True
    if attr.startswith("aria-"):
        return True
    if attr.startswith("data-") and attr != "data-agent-id":
        return True
    if attr in {"class", "id"} and _is_icon_element(tag):
        return False
    if attr in {"class", "id"}:
        return True
    return False


def clean_html_for_llm(html: str) -> str:
    """Return simplified HTML string optimized for Gemini token usage."""
    soup = BeautifulSoup(html or "", "html.parser")

    for node in soup.find_all(string=lambda text: isinstance(text, Comment)):
        node.extract()

    for name in REMOVE_TAGS:
        for tag in soup.find_all(name):
            tag.decompose()

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        for attr in list(tag.attrs):
            if _should_strip_attr(tag, attr):
                del tag[attr]

    changed = True
    while changed:
        changed = False
        for tag in list(soup.find_all(["div", "span"])):
            if tag.get_text(strip=True):
                continue
            if tag.find_all(list(KEEP_TAGS)):
                continue
            tag.decompose()
            changed = True

    root = soup.body if soup.body else soup
    output = root.decode_contents() if soup.body else str(soup)
    output = re.sub(r">\s+<", ">\n<", output)
    output = re.sub(r"\n{2,}", "\n", output)
    return output.strip()


def discover_page_html_files(pages_dir: Path) -> list[Path]:
    folder_pages = sorted(pages_dir.glob("*/index.html"))
    if folder_pages:
        return folder_pages
    return sorted(p for p in pages_dir.glob("*.html") if p.name != "index.html")


def clean_all_pages(pages_dir: str = "pages", output_dir: str = "analysis/cleaned") -> int:
    """Read each HTML under pages_dir, clean it, save to output_dir. Never touches originals."""
    pages_path = Path(pages_dir)
    output_path = Path(output_dir)

    if not pages_path.is_dir():
        raise FileNotFoundError(f"Pages directory not found: {pages_path}")

    html_files = discover_page_html_files(pages_path)
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {pages_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    for i, html_file in enumerate(html_files, 1):
        cleaned = clean_html_for_llm(html_file.read_text(encoding="utf-8"))
        rel = html_file.relative_to(pages_path)
        out = output_path / rel.parent / "index.cleaned.html" if rel.name == "index.html" else output_path / f"{rel.stem}.cleaned.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(cleaned, encoding="utf-8")
        print(f"  [{i}/{len(html_files)}] {rel} → {out.relative_to(output_path)}")

    print(f"\n✅ Cleaned {len(html_files)} pages → {output_path}/")
    return len(html_files)


if __name__ == "__main__":
    print("[*] Cleaning crawled HTML for LLM analysis...")
    clean_all_pages()
