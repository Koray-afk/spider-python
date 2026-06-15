"""Stitcher V1 — turn crawl snapshots into a navigable static SaaS clone.

Three responsibilities, nothing else:

1. Page navigation  — rewrite `<a href="#/route">` to `../<slug>/page.html`
                      (every anchor, even ones hidden inside collapsed menus)
2. Sidebar accordions — wire collapsible in-page menus (accordion buttons /
                      aria-controls toggles) so they expand/collapse client-side.
                      These are NEVER treated as interactions and NEVER load a
                      snapshot — the submenu already lives in the same page.
3. Interaction UI   — tag each trigger with `data-stitch-ui-id` and inject the
                      reconciled `ui_html` (from reconciliation.json) into the
                      current page on click — no reload. The captured snapshot
                      page is used only as a fallback when injection isn't
                      possible (no ui_html, parentSelector missing, or it throws).

The accordion vs. interaction split is generic (no app-specific selectors): a
toggle whose `aria-controls` target (or sibling panel) exists *in the same page*
is an accordion; a trigger whose content is created on click (dropdown / modal /
popover / drawer overlay) is reconciled and injected in place.

Injection wraps the UI in `.stitch-injected-ui` and the runtime provides generic
close behavior (click-outside, ESC, and `.close`/`.sidebar-close`/`[data-dismiss]`
/backdrop affordances). Interaction config travels to the browser as
`window.__STITCH_INTERACTIONS__`.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from storage.storage_manager import (
    clean_stitched,
    get_crawl_dir,
    get_sitemap_path,
    get_stitched_dir,
)

RUNTIME_JS = """// Stitcher runtime — page navigation, sidebar accordions, and reconciliation
// UI injection. Interaction clicks inject the reconciled UI into the CURRENT
// page (no reload); the captured snapshot page is used only as a fallback.
(function () {
  "use strict";

  var CLOSE_SELECTOR =
    ".close, .sidebar-close, .modal-close, [data-dismiss], [data-bs-dismiss]," +
    " [aria-label*='close' i], [class*='backdrop'], [class*='overlay-mask']";

  function configFor(id) {
    var all = window.__STITCH_INTERACTIONS__ || {};
    return all[id] || null;
  }

  function findPanel(toggle) {
    var id = toggle.getAttribute("data-stitch-accordion");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) {
      var ac = toggle.getAttribute("aria-controls");
      if (ac) panel = document.getElementById(ac);
    }
    if (!panel) panel = toggle.nextElementSibling;
    return panel;
  }

  function removeUI(container) {
    if (!container) return;
    if (container.__stitchOutside)
      document.removeEventListener("click", container.__stitchOutside, true);
    if (container.__stitchKey)
      document.removeEventListener("keydown", container.__stitchKey, true);
    if (container.parentNode) container.parentNode.removeChild(container);
  }

  function bindClose(container, trigger) {
    // Explicit close affordances inside the injected UI.
    container.querySelectorAll(CLOSE_SELECTOR).forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        removeUI(container);
      });
    });
    // Click anywhere outside the injected UI (and not on the trigger) closes it.
    function outside(ev) {
      if (
        !container.contains(ev.target) &&
        ev.target !== trigger &&
        !(trigger && trigger.contains && trigger.contains(ev.target))
      ) {
        removeUI(container);
      }
    }
    container.__stitchOutside = outside;
    // Defer so the click that opened the UI doesn't immediately close it.
    setTimeout(function () {
      document.addEventListener("click", outside, true);
    }, 0);
    // ESC closes too (generic, framework-agnostic).
    function onKey(ev) {
      if (ev.key === "Escape" || ev.keyCode === 27) removeUI(container);
    }
    container.__stitchKey = onKey;
    document.addEventListener("keydown", onKey, true);
  }

  function injectInteraction(trigger) {
    var id = trigger.getAttribute("data-stitch-ui-id");
    var cfg = configFor(id);
    var fallback = cfg && cfg.fallback;
    try {
      if (!cfg || !cfg.uiHtml) throw new Error("no reconciled ui_html");

      // Toggle: a second click on the same trigger closes the open UI.
      var open = document.querySelector(
        '.stitch-injected-ui[data-stitch-ui-id="' + id + '"]'
      );
      if (open) {
        removeUI(open);
        return;
      }

      var parent = cfg.parentSelector
        ? document.querySelector(cfg.parentSelector)
        : document.body;
      if (!parent) throw new Error("parentSelector not found: " + cfg.parentSelector);

      var container = document.createElement("div");
      container.className = "stitch-injected-ui";
      container.setAttribute("data-stitch-ui-id", id);
      container.setAttribute("data-stitch-type", cfg.type || "");
      if (cfg.backdropHtml) container.insertAdjacentHTML("beforeend", cfg.backdropHtml);
      container.insertAdjacentHTML("beforeend", cfg.uiHtml);

      var method = (cfg.insertMethod || "append").toLowerCase();
      if (method === "replace") {
        parent.innerHTML = "";
        parent.appendChild(container);
      } else if (method === "prepend" || method === "insert" || method === "afterbegin") {
        parent.insertAdjacentElement("afterbegin", container);
      } else {
        parent.insertAdjacentElement("beforeend", container);
      }

      bindClose(container, trigger);
      console.log("[STITCH] Inject UI", id, "type=" + (cfg.type || "?"), "→", cfg.parentSelector);
    } catch (err) {
      console.warn("[STITCH] UI injection failed → snapshot fallback", id, err);
      if (fallback) window.location.href = fallback;
    }
  }

  document.addEventListener(
    "click",
    function (e) {
      var t = e.target;
      if (!t || !t.closest) return;

      // 1. Sidebar accordion toggle — purely in-page, never loads a snapshot.
      var acc = t.closest("[data-stitch-accordion]");
      if (acc) {
        e.preventDefault();
        e.stopPropagation();
        var expanded = acc.getAttribute("aria-expanded") === "true";
        acc.setAttribute("aria-expanded", expanded ? "false" : "true");
        if (expanded) acc.classList.add("collapsed");
        else acc.classList.remove("collapsed");
        var panel = findPanel(acc);
        if (panel) {
          if (expanded) {
            panel.classList.remove("show");
            panel.setAttribute("hidden", "true");
          } else {
            panel.classList.add("show");
            panel.removeAttribute("hidden");
          }
        }
        console.log("[STITCH] Accordion Toggle", acc.getAttribute("data-stitch-accordion") || (panel && panel.id) || "?", expanded ? "→ collapse" : "→ expand");
        return;
      }

      // 2. Interaction → inject reconciled UI into the current page (no reload).
      var uiTrigger = t.closest("[data-stitch-ui-id]");
      if (uiTrigger) {
        e.preventDefault();
        e.stopPropagation();
        injectInteraction(uiTrigger);
        return;
      }

      // 3. Non-anchor page navigation discovered during crawl.
      var goTrigger = t.closest("[data-stitch-go]");
      if (goTrigger) {
        e.preventDefault();
        e.stopPropagation();
        window.location.href = goTrigger.getAttribute("data-stitch-go");
        return;
      }

      // 4. Page navigation: local rewritten anchors work natively. Block any
      //    leftover production/external link so nothing escapes the clone.
      var a = t.closest("a[href]");
      if (a) {
        var href = a.getAttribute("href") || "";
        if (a.hasAttribute("data-stitch-unresolved")) {
          console.log("[STITCH] Sidebar Link (unresolved route)", a.getAttribute("data-stitch-route") || "#");
        } else if (a.hasAttribute("data-stitch-page")) {
          console.log("[STITCH] Sidebar Link", href);
        }
        if (/^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0) {
          e.preventDefault();
        }
      }
    },
    true
  );
})();
"""

_INERT_PREFIXES = ("javascript:", "mailto:", "tel:", "data:", "blob:")

_ENTRY_TITLE_HINTS = ("dashboard",)
_ENTRY_SLUG_HINTS = ("home-dashboard", "dashboard", "home")

# Generic class tokens that mark an element as an accordion *toggle* (the
# clickable header), independent of any particular app. No Zoho-specific names.
_ACCORDION_CLASS_TOKENS = {
    "accordion-button",
    "accordion-title",
    "accordion-toggle",
    "accordion-header",
    "accordion-trigger",
}

# Inline style declarations that freeze interactivity. Pages crawled mid-load
# often capture these on nav containers, permanently disabling the clone.
_POINTER_EVENTS_NONE_RE = re.compile(r"pointer-events\s*:\s*none\s*;?", re.I)
_USER_SELECT_NONE_RE = re.compile(r"user-select\s*:\s*none\s*;?", re.I)
_INTERACTIVE_TAGS = ("a", "button", "input", "select", "textarea")

# Belt-and-suspenders CSS override injected into every page so nav stays live
# even if some inline freeze slipped through.
_INTERACTION_FIX_CSS = """#main-nav-tab,
#main-nav-tab *,
.main-nav-lhs,
.main-nav-lhs * {
    pointer-events:auto !important;
}"""

FALLBACK_404 = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found — stitched clone</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f172a;
         color: #e2e8f0; display: flex; min-height: 100vh; margin: 0;
         align-items: center; justify-content: center; }
  .card { text-align: center; max-width: 32rem; padding: 2rem; }
  h1 { font-size: 4rem; margin: 0; color: #38bdf8; }
  p { color: #94a3b8; line-height: 1.6; }
  a { color: #38bdf8; }
  code { background: #1e293b; padding: .15rem .4rem; border-radius: .25rem; }
</style>
</head>
<body>
  <div class="card">
    <h1>404</h1>
    <p><strong>Missing stitched page.</strong></p>
    <p>This page was not captured by the crawler, or the link points somewhere
       outside the local clone.</p>
    <p><a href="/">&larr; Back to the entry page</a></p>
  </div>
</body>
</html>
"""


def _resolve_entry(navigation: dict, valid_slugs: set[str]) -> str | None:
    """Pick the entry page: prefer a dashboard, then a home page, then anything."""
    for slug, info in navigation.items():
        if any(h in (info.get("title", "") or "").lower() for h in _ENTRY_TITLE_HINTS):
            return slug
    for hint in _ENTRY_SLUG_HINTS:
        for slug in navigation:
            if hint in slug.lower():
                return slug
    if navigation:
        return next(iter(navigation))
    return next(iter(sorted(valid_slugs)), None)


def _write_entry_redirect(stitched_dir: Path, entry_slug: str) -> None:
    target = f"./{entry_slug}/page.html"
    stitched_dir.joinpath("index.html").write_text(
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={target}">'
        f'<script>location.replace("{target}");</script>'
        f'</head><body>Redirecting to <a href="{target}">the clone</a>…</body></html>\n',
        encoding="utf-8",
    )


def _norm_class(value) -> str:
    if isinstance(value, (list, tuple)):
        value = " ".join(value)
    return " ".join((value or "").split())


def _norm_route(raw: str) -> str:
    """Normalize an SPA route to a comparable key (drops query, lowercased)."""
    if not raw:
        return ""
    if "#" in raw:
        raw = raw.split("#", 1)[1]
    raw = raw.split("?", 1)[0].strip()
    if not raw:
        return ""
    return "/" + raw.strip("/").lower()


def _build_route_index(
    page_dirs: list[Path], sitemap: list[dict], valid_slugs: set[str]
) -> dict[str, str]:
    """Map normalized route (with and without query) → slug for every crawled
    page. Sourced primarily from each page's own metadata.json url (so the
    index is complete even when the sitemap is missing entries), with sitemap
    urls merged in as aliases."""
    index: dict[str, str] = {}

    def add(url: str, slug: str) -> None:
        if not slug or slug not in valid_slugs:
            return
        fragment = urlparse(url or "").fragment
        for key in (_norm_route("#" + fragment), _norm_route(fragment.split("?")[0])):
            if key:
                index.setdefault(key, slug)

    for page_dir in page_dirs:
        meta = page_dir / "metadata.json"
        if meta.exists():
            try:
                add(json.loads(meta.read_text(encoding="utf-8")).get("url", ""), page_dir.name)
            except Exception:
                pass
    for entry in sitemap:
        add(entry.get("url", ""), entry.get("slug", ""))
    return index


def _resolve_anchor(href: str, route_index: dict[str, str]) -> str | None:
    """Return the target slug for an anchor href, or None if not a crawled page."""
    if not href:
        return None
    full = _norm_route(href)
    if full in route_index:
        return route_index[full]
    base = _norm_route(href.split("?")[0])
    return route_index.get(base)


def _rewrite_anchors(soup: BeautifulSoup, route_index: dict[str, str], to_root: str) -> dict[str, str]:
    """Rewrite every <a href> to a local page or neutralize it. Returns the
    slug→relative-path map of resolved page links for the navigation manifest."""
    page_links: dict[str, str] = {}
    for a in soup.find_all("a"):
        if not a.has_attr("href"):
            continue
        href = (a.get("href") or "").strip()
        low = href.lower()
        if low in ("", "#") or low.startswith(_INERT_PREFIXES):
            continue

        slug = _resolve_anchor(href, route_index)
        if slug:
            rel = f"{to_root}{slug}/page.html"
            a["href"] = rel
            a["data-stitch-page"] = slug
            page_links[slug] = rel
        else:
            # Internal hash route we never crawled, or an absolute production
            # URL — make it inert so navigation never escapes the clone. Keep
            # the original route on the element so the runtime can log it (helps
            # identify uncrawled sidebar routes).
            a["data-stitch-route"] = href
            a["href"] = "#"
            a["data-stitch-unresolved"] = "1"
    return page_links


def _is_descendant(node, ancestor) -> bool:
    p = node.parent
    while p is not None:
        if p is ancestor:
            return True
        p = p.parent
    return False


def _next_element_sibling(node):
    sib = node.next_sibling
    while sib is not None and not getattr(sib, "name", None):
        sib = sib.next_sibling
    return sib


def _show_panel(panel) -> None:
    """Make a collapsed accordion panel visible: drop `hidden`, add `.show`,
    clear any inline `display:none`."""
    if panel.has_attr("hidden"):
        del panel["hidden"]
    if panel.has_attr("aria-hidden"):
        panel["aria-hidden"] = "false"
    classes = panel.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    classes = list(classes)
    if "show" not in classes:
        classes.append("show")
    panel["class"] = classes
    style = panel.get("style") or ""
    if "display" in style.lower():
        cleaned = re.sub(r"display\s*:\s*none\s*;?", "", style, flags=re.I).strip()
        if cleaned:
            panel["style"] = cleaned
        else:
            del panel["style"]


def _resolve_panel(soup: BeautifulSoup, toggle, is_class_toggle: bool):
    """Find the in-page panel a toggle controls.

    Priority: `aria-controls` → element with that id (must exist in this page
    and not be a descendant of the toggle). For class-based accordions without
    a resolvable aria-controls, fall back to the next element sibling.

    Returns None when the controlled content does not exist in the page — that
    is the signal it's a dynamic interaction trigger (dropdown/modal/popover),
    not a sidebar accordion.
    """
    ac = toggle.get("aria-controls")
    if ac:
        target = soup.find(id=ac)
        if target is not None and not _is_descendant(target, toggle):
            return target
        # aria-controls present but target absent → dynamic content. Only a
        # class-marked accordion may fall through to sibling resolution.
        if not is_class_toggle:
            return None
    if is_class_toggle:
        sib = _next_element_sibling(toggle)
        if sib is not None and not _is_descendant(sib, toggle):
            return sib
    return None


def _wire_accordions(soup: BeautifulSoup, used: set[int], expand_default: bool) -> int:
    """Tag sidebar accordion toggles so the runtime expands/collapses their
    in-page panel. Toggles are added to `used` so interaction wiring never
    rebinds them to a snapshot. One toggle per panel (outermost in document
    order); inner clicks reach it via event bubbling / `closest`.

    Returns the number of accordions wired.
    """
    wired_panels: set[int] = set()
    count = 0
    for el in soup.find_all(True):
        if id(el) in used:
            continue
        classes = set(_norm_class(el.get("class")).split())
        is_class_toggle = bool(classes & _ACCORDION_CLASS_TOKENS)
        has_aria = el.has_attr("aria-controls") or el.has_attr("aria-expanded")
        if not (is_class_toggle or has_aria):
            continue

        panel = _resolve_panel(soup, el, is_class_toggle)
        if panel is None:
            continue  # dynamic interaction trigger or nothing to toggle
        if id(panel) in wired_panels:
            continue  # already covered by an outer toggle for this panel

        wired_panels.add(id(panel))
        el["data-stitch-accordion"] = panel.get("id") or ""
        used.add(id(el))
        count += 1

        if "collapsed" in classes:
            el["class"] = [c for c in (el.get("class") or []) if c != "collapsed"]
        if expand_default:
            el["aria-expanded"] = "true"
            _show_panel(panel)
        elif el.has_attr("aria-expanded"):
            el["aria-expanded"] = "false"
    return count


def _find_trigger(soup: BeautifulSoup, trigger: dict, used: set[int]):
    """Locate the trigger element in the snapshot DOM using stable attributes.

    The saved page.html predates the crawler's data-crawl-id tagging and inner
    ids are regenerated per load, so we score on durable attributes (tag, class,
    aria-label, text, name, role, type) and assign each interaction to the best
    not-yet-used element in document order.
    """
    tag = (trigger.get("tag_name") or "").lower() or True
    tid = trigger.get("id") or ""
    cls = _norm_class(trigger.get("class_name"))
    aria = trigger.get("aria_label") or ""
    text = (trigger.get("text") or "").strip()
    name = trigger.get("name") or ""
    role = trigger.get("role") or ""
    ttype = ""
    m = re.search(r'type=["\']([^"\']+)["\']', trigger.get("outer_html") or "")
    if m:
        ttype = m.group(1)

    best = None
    best_score = 0
    for el in soup.find_all(tag):
        if id(el) in used:
            continue
        score = 0
        if tid and el.get("id") == tid:
            score += 100
        ecls = _norm_class(el.get("class"))
        if cls:
            if ecls == cls:
                score += 40
            elif ecls and set(ecls.split()) == set(cls.split()):
                score += 35
            elif ecls and set(cls.split()) & set(ecls.split()):
                score += 10
        if aria and el.get("aria-label") == aria:
            score += 25
        if text and el.get_text(" ", strip=True) == text:
            score += 20
        if name and el.get("name") == name:
            score += 15
        if role and el.get("role") == role:
            score += 10
        if ttype and el.get("type") == ttype:
            score += 8
        if score > best_score:
            best = el
            best_score = score

    return best if best_score > 0 else None


def _wire_navigations(
    soup: BeautifulSoup,
    navigations: list[dict],
    valid_slugs: set[str],
    to_root: str,
    used: set[int],
) -> dict[str, str]:
    """Bind non-anchor navigation triggers (div/li/span/role=menuitem/button)
    discovered during the crawl. Each becomes clickable via data-stitch-go →
    the local target page, so navigation works without an anchor tag."""
    page_links: dict[str, str] = {}
    for nav in navigations:
        slug = nav.get("target_slug", "")
        if not slug or slug not in valid_slugs:
            continue
        trigger = nav.get("trigger", {}) or {}
        # Anchors are already rewritten via href; skip to avoid redundancy.
        if (trigger.get("tag_name") or nav.get("tag_name") or "").lower() == "a":
            continue
        el = _find_trigger(soup, trigger, used) if trigger else None
        if el is None:
            continue
        used.add(id(el))
        rel = f"{to_root}{slug}/page.html"
        el["data-stitch-go"] = rel
        el["data-stitch-page"] = slug
        page_links[slug] = rel
    return page_links


def _normalize_trigger(trigger: dict) -> dict:
    """Map a reconciliation-style trigger (camelCase) to the snake_case keys
    `_find_trigger` expects. Pass-through for already snake_case triggers."""
    if not trigger:
        return {}
    return {
        "tag_name": trigger.get("tag_name") or trigger.get("tagName") or "",
        "id": trigger.get("id") or "",
        "class_name": trigger.get("class_name") or trigger.get("className") or "",
        "aria_label": trigger.get("aria_label") or trigger.get("ariaLabel") or "",
        "text": trigger.get("text") or trigger.get("label") or "",
        "name": trigger.get("name") or "",
        "role": trigger.get("role") or "",
        "outer_html": trigger.get("outer_html") or trigger.get("outerHTML") or "",
    }


def _rewrite_fragment_anchors(html: str, route_index: dict[str, str], to_root: str) -> str:
    """Localize anchors inside an injected UI fragment so links opened from an
    overlay still navigate within the clone."""
    if not html or "<a" not in html.lower():
        return html
    frag = BeautifulSoup(html, "html.parser")
    _rewrite_anchors(frag, route_index, to_root)
    return str(frag)


def _wire_interactions(
    soup: BeautifulSoup,
    page_dir: Path,
    interactions: list[dict],
    used: set[int],
    route_index: dict[str, str],
    to_root: str,
) -> tuple[list[dict], dict[str, dict]]:
    """Match each interaction trigger and tag it with `data-stitch-ui-id`. Build
    a per-page config map (→ window.__STITCH_INTERACTIONS__) carrying the
    reconciled `ui_html` / `backdrop_html`, insertion location, and a snapshot
    `fallback`. Primary behavior is in-page injection; the snapshot is fallback
    only. Returns (manifest, configs)."""
    manifest: list[dict] = []
    configs: dict[str, dict] = {}
    counter = 0

    for item in interactions:
        ipath = item.get("interaction_path", "")
        if not ipath:
            continue
        fallback = f"{ipath}/page.html"

        # Reconciliation drives the primary (injection) behavior.
        recon: dict = {}
        recon_abs = page_dir / ipath / "reconciliation.json"
        if recon_abs.exists():
            try:
                recon = json.loads(recon_abs.read_text(encoding="utf-8")) or {}
            except Exception:
                recon = {}

        itype = recon.get("interaction_type", "") or "unknown"
        loc = recon.get("location", {}) or {}
        ui_html = recon.get("ui_html", "") or ""
        backdrop_html = recon.get("backdrop_html", "") or ""

        # Prefer relationship.json for *matching* (richest trigger metadata);
        # fall back to the reconciliation trigger.
        match_trigger: dict = {}
        rel_abs = page_dir / item.get("relationship_file", f"{ipath}/relationship.json")
        if rel_abs.exists():
            try:
                rel = json.loads(rel_abs.read_text(encoding="utf-8"))
                match_trigger = rel.get("trigger", {}) or {}
                if itype == "unknown":
                    itype = rel.get("interaction_type", itype)
            except Exception:
                match_trigger = {}
        if not match_trigger:
            match_trigger = _normalize_trigger(recon.get("trigger", {}) or {})

        el = _find_trigger(soup, match_trigger, used) if match_trigger else None
        bound = False
        ui_id = ""
        if el is not None:
            used.add(id(el))
            counter += 1
            ui_id = f"interaction_{counter}"
            el["data-stitch-ui-id"] = ui_id
            configs[ui_id] = {
                "type": itype,
                "parentSelector": loc.get("parentSelector", "") or "",
                "parentXPath": loc.get("parentXPath", "") or "",
                "insertMethod": loc.get("insertMethod", "append") or "append",
                "uiHtml": _rewrite_fragment_anchors(ui_html, route_index, to_root),
                "backdropHtml": _rewrite_fragment_anchors(backdrop_html, route_index, to_root),
                "fallback": fallback,
            }
            bound = True

        manifest.append(
            {
                "label": item.get("label", ""),
                "type": itype,
                "path": fallback,
                "ui_id": ui_id,
                "has_ui": bool(ui_html),
                "bound": bound,
            }
        )
    return manifest, configs


def _inject_runtime(soup: BeautifulSoup, to_root: str, configs: dict[str, dict] | None = None) -> None:
    body = soup.body or soup
    if configs:
        # Escape `</` so a literal "</script>" inside ui_html can't terminate the
        # inline script tag. ensure_ascii keeps U+2028/U+2029 etc. safe.
        data = json.dumps(configs, ensure_ascii=True).replace("</", "<\\/")
        cfg_tag = soup.new_tag("script")
        cfg_tag.string = f"window.__STITCH_INTERACTIONS__ = {data};"
        body.append(cfg_tag)
    body.append(soup.new_tag("script", src=f"{to_root}runtime.js"))


def _neutralize_disabled_state(soup: BeautifulSoup) -> tuple[int, int]:
    """Undo temporary disabled/loading state captured during the crawl so the
    offline clone stays interactive. Runs across the whole document:

      * strip `pointer-events:none` / `user-select:none` from inline styles
      * drop `disabled` + `aria-disabled="true"` from interactive controls
      * inject a CSS override keeping nav containers clickable

    Returns (pointer_events_none_removed, disabled_controls_restored).
    """
    pe_removed = 0
    for el in soup.find_all(style=True):
        style = el.get("style") or ""
        hits = len(_POINTER_EVENTS_NONE_RE.findall(style))
        if not hits and not _USER_SELECT_NONE_RE.search(style):
            continue
        pe_removed += hits
        cleaned = _USER_SELECT_NONE_RE.sub("", _POINTER_EVENTS_NONE_RE.sub("", style))
        cleaned = cleaned.strip().strip(";").strip()
        if cleaned:
            el["style"] = cleaned
        else:
            del el["style"]

    controls_restored = 0
    for el in soup.find_all(_INTERACTIVE_TAGS):
        changed = False
        if el.has_attr("disabled"):
            del el["disabled"]
            changed = True
        if (el.get("aria-disabled") or "").lower() == "true":
            del el["aria-disabled"]
            changed = True
        if changed:
            controls_restored += 1

    style_tag = soup.new_tag("style", id="stitch-interaction-fixes")
    style_tag.string = _INTERACTION_FIX_CSS
    (soup.head or soup.body or soup).append(style_tag)

    return pe_removed, controls_restored


def _process_html(
    html: str,
    *,
    to_root: str,
    route_index: dict[str, str],
    valid_slugs: set[str] | None = None,
    page_dir: Path | None = None,
    interactions: list[dict] | None = None,
    navigations: list[dict] | None = None,
    expand_sidebars: bool = True,
) -> tuple[str, dict[str, str], list[dict], int, tuple[int, int]]:
    soup = BeautifulSoup(html, "html.parser")
    page_links = _rewrite_anchors(soup, route_index, to_root)
    used: set[int] = set()
    # Accordions first: claim sidebar toggles so interaction wiring never
    # rebinds them to a snapshot, and rewritten submenu anchors stay reachable.
    accordions = _wire_accordions(soup, used, expand_sidebars)
    if navigations and valid_slugs is not None:
        page_links.update(_wire_navigations(soup, navigations, valid_slugs, to_root, used))
    inter_manifest: list[dict] = []
    configs: dict[str, dict] = {}
    if interactions and page_dir is not None:
        inter_manifest, configs = _wire_interactions(
            soup, page_dir, interactions, used, route_index, to_root
        )
    # Final pass: undo any temporary disabled/loading state before writing.
    fixes = _neutralize_disabled_state(soup)
    _inject_runtime(soup, to_root, configs)
    return str(soup), page_links, inter_manifest, accordions, fixes


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_interactions(page_dir: Path) -> list[dict]:
    f = page_dir / "interactions" / "interactions.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def stitch_app(app_name: str, expand_sidebars: bool = True) -> dict:
    crawl_dir = get_crawl_dir(app_name)
    if not crawl_dir.is_dir():
        raise FileNotFoundError(f"No crawl output for '{app_name}' at {crawl_dir}")

    sitemap_path = get_sitemap_path(app_name)
    sitemap = json.loads(sitemap_path.read_text(encoding="utf-8")) if sitemap_path.exists() else []
    titles = {e.get("slug", ""): e.get("title", "") for e in sitemap}
    urls = {e.get("slug", ""): e.get("url", "") for e in sitemap}

    page_dirs = [d for d in sorted(crawl_dir.iterdir()) if d.is_dir() and (d / "page.html").exists()]
    valid_slugs = {d.name for d in page_dirs}
    route_index = _build_route_index(page_dirs, sitemap, valid_slugs)

    stitched_dir = get_stitched_dir(app_name)
    clean_stitched(app_name)
    stitched_dir.mkdir(parents=True, exist_ok=True)

    (stitched_dir / "runtime.js").write_text(RUNTIME_JS, encoding="utf-8")

    navigation: dict[str, dict] = {}
    pages_done = 0
    interactions_bound = 0
    interactions_total = 0
    accordions_total = 0
    pointer_events_fixed = 0
    controls_restored = 0

    for page_dir in page_dirs:
        slug = page_dir.name
        out_dir = stitched_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        interactions = _load_interactions(page_dir)
        navigations = _load_json_list(page_dir / "navigations.json")
        html = (page_dir / "page.html").read_text(encoding="utf-8")
        new_html, page_links, inter_manifest, accordions, fixes = _process_html(
            html,
            to_root="../",
            route_index=route_index,
            valid_slugs=valid_slugs,
            page_dir=page_dir,
            interactions=interactions,
            navigations=navigations,
            expand_sidebars=expand_sidebars,
        )
        (out_dir / "page.html").write_text(new_html, encoding="utf-8")
        pages_done += 1
        accordions_total += accordions
        pointer_events_fixed += fixes[0]
        controls_restored += fixes[1]

        # Copy each interaction snapshot whole (do not reconstruct/merge), but
        # still localize its anchors + inject runtime so nothing escapes.
        for item in inter_manifest:
            interactions_total += 1
            if item["bound"]:
                interactions_bound += 1
            src = page_dir / item["path"]
            if not src.exists():
                continue
            dst = out_dir / item["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            ihtml = src.read_text(encoding="utf-8")
            new_ihtml, _, _, _, ifixes = _process_html(
                ihtml,
                to_root="../../../",
                route_index=route_index,
                valid_slugs=valid_slugs,
                navigations=navigations,
                expand_sidebars=expand_sidebars,
            )
            pointer_events_fixed += ifixes[0]
            controls_restored += ifixes[1]
            dst.write_text(new_ihtml, encoding="utf-8")

        nav_bound = sum(1 for n in navigations if n.get("target_slug") in valid_slugs)
        navigation[slug] = {
            "title": titles.get(slug, ""),
            "url": urls.get(slug, ""),
            "pages": page_links,
            "interactions": [
                {
                    "label": i["label"],
                    "type": i["type"],
                    "ui_id": i.get("ui_id", ""),
                    "has_ui": i.get("has_ui", False),
                    "fallback": i["path"],
                }
                for i in inter_manifest
            ],
        }
        print(
            f"[STITCH] {slug}: {len(page_links)} page links "
            f"({nav_bound} non-anchor), {accordions} accordions, "
            f"{sum(1 for i in inter_manifest if i['bound'])}/{len(inter_manifest)} interactions wired"
        )

    (stitched_dir / "navigation.json").write_text(
        json.dumps(navigation, indent=2), encoding="utf-8"
    )
    (stitched_dir / "404.html").write_text(FALLBACK_404, encoding="utf-8")

    entry_slug = _resolve_entry(navigation, valid_slugs)
    if entry_slug:
        _write_entry_redirect(stitched_dir, entry_slug)
        print(f"[STITCH] Entry page: {entry_slug}")

    print(
        f"[STITCH] Interaction fixes: {pointer_events_fixed} pointer-events:none removed, "
        f"{controls_restored} disabled controls restored"
    )
    print(f"[STITCH] Output: {stitched_dir.resolve()}")
    return {
        "pages": pages_done,
        "interactions_total": interactions_total,
        "interactions_bound": interactions_bound,
        "accordions": accordions_total,
        "pointer_events_fixed": pointer_events_fixed,
        "controls_restored": controls_restored,
        "entry": entry_slug,
        "output": str(stitched_dir),
    }
