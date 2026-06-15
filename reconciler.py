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
    ("dropdown", {"dropdown-menu", "dropdown-content", "menu-list"}, {"menu", "listbox"}),
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
    return {
        "trigger": trigger,
        "interaction_type": _classify(added) if added else "unknown",
        "location": _location(added[0] if added else None),
        "ui_html": "\n".join(str(r) for r in ui_roots),
        "backdrop_html": "\n".join(str(r) for r in backdrop_roots),
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
                f"| ui={len(recon['ui_html'])}B backdrop={len(recon['backdrop_html'])}B"
            )

    return {"interactions": total, "type_counts": type_counts}
