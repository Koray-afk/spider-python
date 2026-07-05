"""Normalize DataTables markup for static clones (no JS resize after capture).

Crawl-time: `_prepare_snapshot_dom()` in crawler_v2.py calls the shared JS helper.
Stitch-time: `fix_datatables_layout()` repairs existing crawl HTML in-place.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

DATATABLES_FIX_CSS = """
/* DataTables — drop baked pixel widths, scroll inside wrapper not page */
.dt-container:has(table.dataTable),
.dataTables_wrapper:has(table.dataTable) {
    overflow-x: auto !important;
    max-width: 100% !important;
    width: 100% !important;
}
.table-responsive:has(table.dataTable) {
    overflow-x: auto !important;
    max-width: 100% !important;
}
table.dataTable[data-stitch-datatable="1"],
table.dataTable {
    width: 100% !important;
    max-width: 100% !important;
    table-layout: auto !important;
}
"""

# Shared with crawler_v2._normalize_datatables (browser evaluate).
DATATABLES_LAYOUT_JS = """() => {
  document.querySelectorAll('table.dataTable').forEach((table) => {
    table.style.width = '100%';
    table.style.maxWidth = '100%';
    table.removeAttribute('width');
    table.querySelectorAll('colgroup').forEach((cg) => cg.remove());
    table.setAttribute('data-stitch-datatable', '1');
    const wrapper = table.closest('.dt-container, .dataTables_wrapper');
    if (wrapper) {
      wrapper.style.overflowX = 'auto';
      wrapper.style.maxWidth = '100%';
      wrapper.style.width = '100%';
    }
    const responsive = table.closest('.table-responsive');
    if (responsive) {
      responsive.style.overflowX = 'auto';
      responsive.style.maxWidth = '100%';
    }
  });
}"""

_WRAPPER_CLASSES = frozenset({"dt-container", "dataTables_wrapper"})
_PX_WIDTH_RE = re.compile(r"width:\s*\d+(?:\.\d+)?px", re.I)


def _append_style(existing: str, extra: str) -> str:
    base = (existing or "").strip().rstrip(";")
    add = extra.strip().rstrip(";")
    if not base:
        return add
    if not add:
        return base
    return f"{base}; {add}"


def _is_datatable(table: Tag) -> bool:
    return isinstance(table, Tag) and table.name == "table" and "dataTable" in (table.get("class") or [])


def _normalize_table_style(table: Tag) -> bool:
    changed = False
    style = table.get("style") or ""
    if _PX_WIDTH_RE.search(style):
        cleaned = _PX_WIDTH_RE.sub("", style).strip().rstrip(";")
        table["style"] = _append_style(cleaned, "width:100%;max-width:100%")
        changed = True
    elif not style or "width" not in style.lower():
        table["style"] = _append_style(style, "width:100%;max-width:100%")
        changed = True
    if table.has_attr("width"):
        del table["width"]
        changed = True
    return changed


def _fix_datatable(table: Tag) -> int:
    fixes = 0
    if _normalize_table_style(table):
        fixes += 1

    for colgroup in table.find_all("colgroup", recursive=False):
        colgroup.decompose()
        fixes += 1

    table["data-stitch-datatable"] = "1"

    wrapper: Tag | None = table.parent
    while wrapper is not None and wrapper.name not in (None, "[document]", "body", "html"):
        if not isinstance(wrapper, Tag):
            break
        classes = set(wrapper.get("class") or [])
        if classes & _WRAPPER_CLASSES:
            wrapper["style"] = _append_style(
                wrapper.get("style", ""),
                "overflow-x:auto;max-width:100%;width:100%",
            )
            fixes += 1
            break
        wrapper = wrapper.parent if isinstance(wrapper.parent, Tag) else None

    responsive = table.find_parent(class_="table-responsive")
    if responsive is not None:
        responsive["style"] = _append_style(
            responsive.get("style", ""),
            "overflow-x:auto;max-width:100%",
        )
        fixes += 1

    return fixes


def fix_datatables_layout(soup: BeautifulSoup) -> int:
    """Remove DataTables pixel widths so tables stay inside their containers."""
    total = 0
    for table in soup.find_all("table"):
        if not _is_datatable(table):
            continue
        total += _fix_datatable(table)
    return total


def inject_datatables_fix_css(soup: BeautifulSoup) -> None:
    """Inject DataTables containment CSS once per page."""
    if soup.find("style", attrs={"data-stitch-datatable-fix": "1"}):
        return
    style = soup.new_tag("style", attrs={"data-stitch-datatable-fix": "1"})
    style.string = DATATABLES_FIX_CSS
    head = soup.find("head")
    if head:
        head.append(style)
    elif soup.body:
        soup.body.insert(0, style)
