"""Normalize frozen AmCharts canvas snapshots for responsive static layout.

Crawl-time: `_freeze_chart_canvases()` in crawler_v2.py calls the same JS helper.
Stitch-time: `fix_frozen_chart_layout()` repairs existing crawl HTML in-place.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

CHART_FIX_CSS = """
/* Frozen AmCharts layers — clip to card, scale with container width */
.chart-container:has([data-stitch-frozen-chart]),
.chart-container:has(img[class*="am5-layer"]),
[id$="Chart"]:has([data-stitch-frozen-chart]),
[id$="Chart"]:has(img[class*="am5-layer"]) {
    overflow: hidden !important;
    position: relative !important;
}
[data-stitch-frozen-chart],
img[class*="am5-layer"][src^="data:image/png"] {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    max-width: 100% !important;
    object-fit: contain !important;
}
"""

# Shared with crawler_v2._freeze_chart_canvases (browser evaluate).
CHART_LAYOUT_JS = """() => {
  function isFrozen(img) {
    return img.matches('[data-stitch-frozen-chart], img[class*="am5-layer"][src^="data:image/png"]');
  }
  function findRoot(img) {
    let node = img.parentElement;
    let heightHost = null;
    while (node && node !== document.body) {
      const internal = node.getAttribute('aria-hidden') === 'true'
        || Array.from(node.classList || []).some((c) => c.startsWith('am5-'));
      if (!internal) {
        if (node.classList && node.classList.contains('chart-container')) return node;
        if (node.id && /Chart$/i.test(node.id)) return node;
        const style = node.getAttribute('style') || '';
        if (/height:\\s*\\d+px/i.test(style)) heightHost = node;
      }
      node = node.parentElement;
    }
    return heightHost;
  }
  document.querySelectorAll('[data-stitch-frozen-chart], img[class*="am5-layer"][src^="data:image/png"]').forEach((img) => {
    img.removeAttribute('width');
    img.removeAttribute('height');
    img.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain;';
    if (!img.hasAttribute('data-stitch-frozen-chart')) {
      img.setAttribute('data-stitch-frozen-chart', '1');
    }
  });
  const roots = new Set();
  document.querySelectorAll('[data-stitch-frozen-chart]').forEach((img) => {
    const root = findRoot(img);
    if (root) roots.add(root);
  });
  roots.forEach((root) => {
    root.style.overflow = 'hidden';
    if (!root.style.position || root.style.position === 'static') {
      root.style.position = 'relative';
    }
    root.querySelectorAll('div[aria-hidden="true"], .am5-html-container, .am5-focus-container, div[style*="width:"]').forEach((div) => {
      const style = div.getAttribute('style') || '';
      if (!/width:\\s*\\d+px/i.test(style) && !div.matches('.am5-html-container, .am5-focus-container, [aria-hidden="true"]')) return;
      if (!root.contains(div)) return;
      div.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden;';
    });
    const rel = root.querySelector(':scope > div[style*="relative"]') || root.querySelector('div[style*="relative"]');
    if (rel) {
      rel.style.width = '100%';
      rel.style.height = '100%';
      rel.style.overflow = 'hidden';
      if (!rel.style.position) rel.style.position = 'relative';
    }
  });
}"""

_AM5_LAYER_RE = re.compile(r"am5-layer")
_FROZEN_IMG_STYLE = (
    "position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain;"
)
_WRAPPER_STYLE = "position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden;"


def _is_frozen_chart_img(img: Tag) -> bool:
    if not isinstance(img, Tag) or img.name != "img":
        return False
    if img.get("data-stitch-frozen-chart") == "1":
        return True
    src = img.get("src") or ""
    classes = " ".join(img.get("class") or [])
    return src.startswith("data:image/png") and _AM5_LAYER_RE.search(classes) is not None


def _append_style(existing: str, extra: str) -> str:
    base = (existing or "").strip().rstrip(";")
    add = extra.strip().rstrip(";")
    if not base:
        return add
    if not add:
        return base
    return f"{base}; {add}"


def _find_chart_root(img: Tag) -> Tag | None:
    node: Tag | None = img.parent
    height_host: Tag | None = None
    while node is not None and node.name not in (None, "[document]", "body", "html"):
        if not isinstance(node, Tag):
            break
        node_id = node.get("id") or ""
        classes = node.get("class") or []
        aria = node.get("aria-hidden")
        internal = aria == "true" or any(c.startswith("am5-") for c in classes)
        if not internal:
            if "chart-container" in classes:
                return node
            if node_id.endswith("Chart"):
                return node
            style = node.get("style") or ""
            if re.search(r"height:\s*\d+px", style, re.I):
                height_host = node
        node = node.parent if isinstance(node.parent, Tag) else None
    return height_host


def _contains_frozen_img(tag: Tag) -> bool:
    return any(_is_frozen_chart_img(img) for img in tag.find_all("img"))


def _fix_chart_root(root: Tag) -> int:
    fixes = 0
    root["style"] = _append_style(root.get("style", ""), "overflow:hidden;position:relative;")
    fixes += 1

    for div in root.find_all("div", style=True):
        style = div.get("style") or ""
        classes = " ".join(div.get("class") or [])
        has_px_width = re.search(r"width:\s*\d+px", style) is not None
        is_wrapper = (
            (has_px_width and "absolute" in style)
            or div.get("aria-hidden") == "true"
            or "am5-html-container" in classes
            or "am5-focus-container" in classes
        )
        if not is_wrapper:
            continue
        if not (
            _contains_frozen_img(div)
            or div.get("aria-hidden") == "true"
            or "am5-" in classes
        ):
            continue
        div["style"] = _WRAPPER_STYLE
        fixes += 1

    for img in root.find_all("img"):
        if not _is_frozen_chart_img(img):
            continue
        img.attrs.pop("width", None)
        img.attrs.pop("height", None)
        img["style"] = _FROZEN_IMG_STYLE
        img["data-stitch-frozen-chart"] = "1"
        fixes += 1

    for div in root.find_all("div", style=True, recursive=True):
        style = div.get("style") or ""
        if "position:" in style and "relative" in style and _contains_frozen_img(div):
            div["style"] = _append_style(style, "overflow:hidden;width:100%;height:100%;")
            fixes += 1
            break

    return fixes


def fix_frozen_chart_layout(soup: BeautifulSoup) -> int:
    """Repair fixed-pixel AmCharts snapshots so charts stay inside their cards."""
    roots: dict[int, Tag] = {}
    for img in soup.find_all("img"):
        if not _is_frozen_chart_img(img):
            continue
        root = _find_chart_root(img)
        if root is None:
            continue
        roots[id(root)] = root

    total = 0
    for root in roots.values():
        total += _fix_chart_root(root)
    return total


def inject_chart_fix_css(soup: BeautifulSoup) -> None:
    """Inject responsive chart CSS once per page."""
    if soup.find("style", attrs={"data-stitch-chart-fix": "1"}):
        return
    style = soup.new_tag("style", attrs={"data-stitch-chart-fix": "1"})
    style.string = CHART_FIX_CSS
    head = soup.find("head")
    if head:
        head.append(style)
    elif soup.body:
        soup.body.insert(0, style)
