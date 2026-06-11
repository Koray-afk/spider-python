"""Prepare crawled HTML for LLM analysis without modifying source files."""

from __future__ import annotations

import re
from pathlib import Path

# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup, Comment, Tag

REMOVE_TAGS = {
    "script", "style", "svg", "path", "noscript", "iframe", "canvas", "meta", "link",
}
STRIP_ATTRS = {"class", "style", "id", "tabindex", "role"}
KEEP_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "button", "input", "select",
    "textarea", "label", "table", "thead", "tbody", "tr", "th", "td", "caption",
    "nav", "form", "ul", "ol", "li", "img",
}


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
            if (
                attr in STRIP_ATTRS
                or attr.startswith("data-")
                or attr.startswith("aria-")
            ):
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
