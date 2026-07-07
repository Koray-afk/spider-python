"""Reconciliation phase — extract the UI a click introduced.

    crawl → reconcile → stitch → serve

For every interaction we diff the main page DOM against the interaction page DOM
and isolate ONLY the newly introduced UI (modal / dropdown / sidebar / drawer /
popover / tooltip / overlay / backdrop). The result is one file:

    interactions/<interaction>/reconciliation.json

It contains everything the stitcher needs (trigger info, type, insertion
location, and the actual UI/backdrop HTML strings). No delta directory, no
reports, no debug artifacts. Deterministic — pure BeautifulSoup tree diffing,
no LLM. The interaction `page.html` and `relationship.json` are left untouched.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from storage.storage_manager import get_crawl_dir, get_metadata_dir

# Attributes regenerated on every render (uuids, aria wiring). Ignored when
# matching nodes so the diff doesn't flag the whole page as "new".
_VOLATILE_ATTRS = {
    "id",
    "data-crawl-id",
    "for",
    "aria-controls",
    "aria-owns",
    "aria-describedby",
    "aria-labelledby",
    "aria-activedescendant",
}

# Class tokens that mark an element as a backdrop/scrim rather than real UI.
_BACKDROP_TOKENS = {
    "modal-backdrop",
    "offcanvas-backdrop",
    "drawer-backdrop",
    "backdrop",
    "cdk-overlay-backdrop",
    "overlay",
    "overlay-backdrop",
    "mask",
    "scrim",
    "dimmer",
}

# Class-token / role signatures for deterministic classification (ordered).
_TYPE_RULES = [
    ("modal", {"modal", "modal-dialog", "modal-content"}, {"dialog"}),
    ("drawer", {"offcanvas", "drawer", "slide-panel", "slide-in"}, set()),
    ("sidebar", {"sidebar", "side-panel", "sidebar-panel", "sidenav"}, set()),
    ("dropdown", {"dropdown-menu", "dropdown-content", "menu-list", "abstractdropdown", "popover"}, set()),
    ("popover", {"popover", "popup", "pop-over"}, set()),
    ("tooltip", {"tooltip", "tip"}, {"tooltip"}),
    ("overlay", {"overlay", "backdrop", "modal-backdrop", "cdk-overlay-pane", "mask"}, set()),
]


def _classes(el: Tag) -> set[str]:
    c = el.get("class")
    if not c:
        return set()
    return set(c if isinstance(c, list) else str(c).split())


def _signature(el: Tag) -> tuple:
    """Structural identity used for matching (ignores volatile attrs/text)."""
    return (el.name, tuple(sorted(_classes(el))), el.get("role") or "", el.get("type") or "")


def _stable_attrs(el: Tag) -> dict:
    out = {}
    for k, v in el.attrs.items():
        if k in _VOLATILE_ATTRS:
            continue
        if k == "class":
            out[k] = " ".join(sorted(_classes(el)))
        else:
            out[k] = " ".join(v) if isinstance(v, list) else v
    return out


def _child_tags(el: Tag) -> list[Tag]:
    return [c for c in el.children if isinstance(c, Tag)]


def _node_count(el: Tag) -> int:
    return len(el.find_all(True)) + 1


def _css_selector(el: Tag) -> str:
    parts: list[str] = []
    cur = el
    while isinstance(cur, Tag) and cur.name != "[document]":
        if cur.get("id"):
            parts.insert(0, f'#{cur["id"]}')
            break
        parent = cur.parent
        if not isinstance(parent, Tag):
            parts.insert(0, cur.name)
            break
        same = [c for c in parent.children if isinstance(c, Tag) and c.name == cur.name]
        idx = same.index(cur) + 1 if cur in same else 1
        parts.insert(0, f"{cur.name}:nth-of-type({idx})")
        cur = parent
    return " > ".join(parts)


def _xpath(el: Tag) -> str:
    parts: list[str] = []
    cur = el
    while isinstance(cur, Tag) and cur.name != "[document]":
        parent = cur.parent
        if not isinstance(parent, Tag):
            parts.insert(0, cur.name)
            break
        same = [c for c in parent.children if isinstance(c, Tag) and c.name == cur.name]
        idx = same.index(cur) + 1 if cur in same else 1
        parts.insert(0, f"{cur.name}[{idx}]")
        cur = parent
    return "/" + "/".join(parts)


def _diff(main_parent: Tag, inter_parent: Tag, added: list[Tag], modified: list[Tag]) -> None:
    """Greedy structural diff: match interaction children to main children by
    signature; unmatched interaction subtrees are additions; matched pairs with
    changed attributes are modifications, then recurse."""
    main_children = _child_tags(main_parent)
    inter_children = _child_tags(inter_parent)
    main_sigs = [_signature(c) for c in main_children]
    used = [False] * len(main_children)

    for ic in inter_children:
        sig = _signature(ic)
        match_idx = None
        for i, msig in enumerate(main_sigs):
            if not used[i] and msig == sig:
                match_idx = i
                break
        if match_idx is None:
            added.append(ic)
            continue
        used[match_idx] = True
        mc = main_children[match_idx]
        if _stable_attrs(mc) != _stable_attrs(ic):
            modified.append(ic)
        _diff(mc, ic, added, modified)


def _classify(fragment_roots: list[Tag]) -> str:
    tokens: set[str] = set()
    roles: set[str] = set()
    for root in fragment_roots:
        for el in [root, *root.find_all(True)]:
            tokens |= {t.lower() for t in _classes(el)}
            r = el.get("role")
            if r:
                roles.add(r.lower())
    for type_name, class_tokens, role_tokens in _TYPE_RULES:
        if tokens & class_tokens or roles & role_tokens:
            return type_name
    return "unknown"


def _is_backdrop(el: Tag) -> bool:
    """A backdrop is a thin scrim element: backdrop-ish class + little content."""
    if not (_classes(el) & _BACKDROP_TOKENS):
        return False
    return _node_count(el) <= 6


def _split_backdrop(roots: list[Tag]) -> tuple[list[Tag], list[Tag]]:
    ui_roots: list[Tag] = []
    backdrop_roots: list[Tag] = []
    for r in roots:
        (backdrop_roots if _is_backdrop(r) else ui_roots).append(r)
    return ui_roots, backdrop_roots


def _location(root: Tag | None) -> dict:
    if root is None:
        return {"parentSelector": "", "parentXPath": "", "insertMethod": "append"}
    parent = root.parent if isinstance(root.parent, Tag) else None
    siblings = _child_tags(parent) if parent else []
    pos = siblings.index(root) if root in siblings else -1
    is_last = pos == len(siblings) - 1
    return {
        "parentSelector": _css_selector(parent) if parent else "",
        "parentXPath": _xpath(parent) if parent else "",
        "insertMethod": "append" if is_last else "insert",
    }


def _trigger_from_relationship(inter_dir: Path) -> dict:
    """Build the trigger block from the interaction's relationship.json."""
    rel_path = inter_dir / "relationship.json"
    if not rel_path.exists():
        return {"label": "", "tagName": "", "id": "", "className": "", "selector": "", "outerHTML": ""}
    try:
        rel = json.loads(rel_path.read_text(encoding="utf-8"))
    except Exception:
        return {"label": "", "tagName": "", "id": "", "className": "", "selector": "", "outerHTML": ""}
    t = rel.get("trigger", {}) or {}
    label = rel.get("trigger_label") or t.get("aria_label") or t.get("text") or ""
    return {
        "label": label,
        "tagName": t.get("tag_name", ""),
        "id": t.get("id", ""),
        "className": t.get("class_name", ""),
        "selector": t.get("crawl_selector") or t.get("selector") or "",
        "outerHTML": t.get("outer_html", ""),
    }


def _aria_attr_from_html(outer_html: str, attr: str) -> str | None:
    """Return an ARIA wiring attribute from a trigger's outerHTML, or None."""
    if not outer_html or attr not in outer_html:
        return None
    soup = BeautifulSoup(outer_html, "html.parser")
    el = soup.find(True)
    return el.get(attr) or None if el else None


def _aria_controls_from_html(outer_html: str) -> str | None:
    """Return the aria-controls attribute value from an element's outerHTML, or None."""
    return _aria_attr_from_html(outer_html, "aria-controls")


def _extract_style_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return "\n".join(tag.get_text() for tag in soup.find_all("style"))


def _classes_in_html(html: str) -> set[str]:
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    out: set[str] = set()
    for el in soup.find_all(True):
        out |= _classes(el)
    return out


_CSS_RULE_RE = re.compile(r"([^{}@][^{]*)\{([^{}]*)\}")


def _extract_css_rules(css: str) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    for match in _CSS_RULE_RE.finditer(css or ""):
        selector = match.group(1).strip()
        body = match.group(2).strip()
        if selector and body:
            rules.append((selector, body))
    return rules


def _selector_uses_classes(selector: str, classes: set[str]) -> bool:
    tokens = set(re.findall(r"\.([a-zA-Z_][\w-]*)", selector))
    return bool(tokens & classes)


def _css_delta_for_ui(
    main_html: str,
    inter_html: str,
    ui_html: str,
    backdrop_html: str = "",
) -> str:
    """Return CSS rules present on the interaction page but missing from main.

    HubSpot styled-components inject rules when overlays mount. The interaction
    page was captured with the overlay open, so its baked <style> blocks contain
    rules for classes in ui_html that the main page never received.
    """
    if not ui_html:
        return ""
    classes = _classes_in_html(ui_html + (backdrop_html or ""))
    if not classes:
        return ""
    main_rules = dict(_extract_css_rules(_extract_style_text(main_html)))
    delta_parts: list[str] = []
    seen: set[tuple[str, str]] = set()
    for selector, body in _extract_css_rules(_extract_style_text(inter_html)):
        if not _selector_uses_classes(selector, classes):
            continue
        key = (selector, body)
        if key in seen:
            continue
        seen.add(key)
        if main_rules.get(selector) == body:
            continue
        delta_parts.append(f"{selector} {{ {body} }}")
    css = "\n".join(delta_parts)
    # Drop orphan closing braces left by partial @-rule parsing in flat extraction.
    return "\n".join(line for line in css.splitlines() if line.strip() != "}")


def _panel_id_on_page(inter_soup: BeautifulSoup, panel_id: str) -> bool:
    return bool(panel_id and inter_soup.find(id=panel_id))


def _resolve_panel_id(inter_soup: BeautifulSoup, trigger: dict) -> str | None:
    """Best-effort panel id for dropdown / menu triggers."""
    outer = trigger.get("outerHTML") or trigger.get("outer_html") or ""
    for attr in ("aria-controls", "aria-owns"):
        panel_id = _aria_attr_from_html(outer, attr)
        if panel_id and _panel_id_on_page(inter_soup, panel_id):
            return panel_id

    tid = (trigger.get("id") or "").strip()
    if tid:
        el = inter_soup.find(id=tid)
        if isinstance(el, Tag):
            for attr in ("aria-controls", "aria-owns"):
                val = el.get(attr) or ""
                if val and _panel_id_on_page(inter_soup, val):
                    return val

    # HubSpot floating-ui dropdowns often wire aria-owns on a data-test-id trigger.
    test_id = ""
    if outer:
        m = re.search(r'data-test-id=["\']([^"\']+)["\']', outer)
        if m:
            test_id = m.group(1)
    if test_id:
        el = inter_soup.find(attrs={"data-test-id": test_id})
        if isinstance(el, Tag):
            for attr in ("aria-controls", "aria-owns"):
                val = el.get(attr) or ""
                if val and _panel_id_on_page(inter_soup, val):
                    return val

    menu = inter_soup.find(id="nav-object-create-menu")
    if isinstance(menu, Tag):
        return "nav-object-create-menu"
    return None


def _is_dropdown_panel(el: Tag) -> bool:
    cls = " ".join(_classes(el)).lower()
    role = (el.get("role") or "").lower()
    if role in ("menu", "listbox"):
        return True
    if role == "presentation" and (
        "abstractdropdown" in cls or el.find(attrs={"data-dropdown-menu": True})
    ):
        return True
    if "dropdown-menu" in cls or "abstractdropdown" in cls or "popover" in cls:
        return True
    if el.find(attrs={"data-dropdown-menu": True}):
        return True
    eid = (el.get("id") or "").lower()
    return bool(eid and ("menu" in eid or "dropdown" in eid))


def _dropdown_ui_html(panel_el: Tag) -> str:
    """Prefer the smallest popover wrapper that still carries dropdown styling."""
    popover = panel_el.find_parent(attrs={"data-component-name": "UIPopover"})
    if isinstance(popover, Tag):
        return str(popover)
    portal = panel_el.find_parent(attrs={"data-floating-ui-portal": True})
    if isinstance(portal, Tag):
        return str(portal)
    return str(panel_el)


def _trigger_has_tab_role(trigger: dict) -> bool:
    """Return True when the trigger element has role="tab".

    Checked against (in order): the 'role' key directly on the trigger dict,
    and then the stored outerHTML string so older relationship.json files that
    don't have a separate 'role' key are handled correctly.
    """
    role = (trigger.get("role") or "").strip().lower()
    if role == "tab":
        return True
    outer = trigger.get("outer_html") or trigger.get("outerHTML") or ""
    if outer:
        m = re.search(r'\brole=["\']([^"\']+)["\']', outer)
        if m and m.group(1).strip().lower() == "tab":
            return True
    return False


def reconcile_interaction(main_html: str, inter_html: str, trigger: dict) -> dict:
    """Diff main vs interaction DOM and return the full reconciliation record."""
    main_soup = BeautifulSoup(main_html, "html.parser")
    inter_soup = BeautifulSoup(inter_html, "html.parser")
    main_root = main_soup.body or main_soup
    inter_root = inter_soup.body or inter_soup

    added: list[Tag] = []
    modified: list[Tag] = []
    _diff(main_root, inter_root, added, modified)

    ui_roots, backdrop_roots = _split_backdrop(added)
    interaction_type = _classify(added) if added else "unknown"
    location = _location(added[0] if added else None)
    ui_html = "\n".join(str(r) for r in ui_roots)
    backdrop_html = "\n".join(str(r) for r in backdrop_roots)

    # Detect tab-switch from the trigger's own role attribute — _classify()
    # never produces "tab-switch" because _TYPE_RULES has no tab category.
    # Elevate to tab-switch early so the panel extraction below runs.
    if _trigger_has_tab_role(trigger):
        interaction_type = "tab-switch"

    # For dropdowns: extract ONLY the controlled panel from the interaction page.
    # The DOM diff often picks up the trigger wrapper and unrelated siblings.
    panel_id = _resolve_panel_id(inter_soup, trigger)
    tab_content_html = ""
    tab_content_selector = ""

    if panel_id:
        panel_el = inter_soup.find(id=panel_id)
        if isinstance(panel_el, Tag):
            # Dropdown branch — only when the trigger is NOT a tab.
            if interaction_type != "tab-switch" and (
                interaction_type == "dropdown" or _is_dropdown_panel(panel_el)
            ):
                ui_html = _dropdown_ui_html(panel_el)
                backdrop_html = ""
                interaction_type = "dropdown"
                # Inject at body level so popper/fixed positioning can work cleanly.
                location = {
                    "parentSelector": "",
                    "parentXPath": "",
                    "insertMethod": "append",
                }

            # Tab-switch: capture the panel's innerHTML for in-place content swap.
            # Previously gated on interaction_type containing "tab", which _classify()
            # could never produce — now correctly triggered by the role detection above.
            if interaction_type == "tab-switch":
                tab_content_html = panel_el.decode_contents()
                tab_content_selector = f"#{panel_id}"

    ui_css = _css_delta_for_ui(main_html, inter_html, ui_html, backdrop_html)

    return {
        "trigger": trigger,
        "interaction_type": interaction_type,
        "location": location,
        "ui_html": ui_html,
        "ui_css": ui_css,
        "backdrop_html": backdrop_html,
        "tab_content_html": tab_content_html,
        "tab_content_selector": tab_content_selector,
    }


def _interaction_dirs(page_dir: Path) -> list[Path]:
    inter_root = page_dir / "interactions"
    if not inter_root.is_dir():
        return []
    return [d for d in sorted(inter_root.iterdir()) if d.is_dir() and (d / "page.html").exists()]


def _remove_legacy_artifacts(app_name: str, crawl_dir: Path) -> None:
    """Delete previously generated debug artifacts (delta/ dirs + report files)."""
    import shutil

    for delta in crawl_dir.rglob("delta"):
        if delta.is_dir():
            shutil.rmtree(delta, ignore_errors=True)
    meta = get_metadata_dir(app_name)
    for name in (
        "reconciliation_report.json",
        "reconciliation_report.csv",
        "reconciliation_report.html",
    ):
        f = meta / name
        if f.exists():
            f.unlink()


def reconcile_app(app_name: str) -> dict:
    crawl_dir = get_crawl_dir(app_name)
    if not crawl_dir.is_dir():
        raise FileNotFoundError(f"No crawl output for '{app_name}' at {crawl_dir}")

    _remove_legacy_artifacts(app_name, crawl_dir)

    page_dirs = [d for d in sorted(crawl_dir.iterdir()) if d.is_dir() and (d / "page.html").exists()]

    total = 0
    type_counts: dict[str, int] = {}
    for page_dir in page_dirs:
        main_html = (page_dir / "page.html").read_text(encoding="utf-8")
        for inter_dir in _interaction_dirs(page_dir):
            total += 1
            inter_html = (inter_dir / "page.html").read_text(encoding="utf-8")
            trigger = _trigger_from_relationship(inter_dir)
            try:
                recon = reconcile_interaction(main_html, inter_html, trigger)
            except Exception as exc:
                print(f"[RECON] {page_dir.name}/{inter_dir.name}: FAILED ({exc})")
                continue

            (inter_dir / "reconciliation.json").write_text(
                json.dumps(recon, indent=2), encoding="utf-8"
            )
            itype = recon["interaction_type"]
            type_counts[itype] = type_counts.get(itype, 0) + 1
            print(
                f"[RECON] {page_dir.name}/{inter_dir.name}: {itype} "
                f"| ui={len(recon['ui_html'])}B css={len(recon.get('ui_css', ''))}B "
                f"backdrop={len(recon['backdrop_html'])}B"
            )

    return {"interactions": total, "type_counts": type_counts}
