"""Accessibility-tree assisted interaction discovery.

Complements DOM-heuristic discovery (DISCOVER_JS) by:
1. Walking the browser accessibility snapshot for interactive roles
2. Resolving unstamped elements via Playwright get_by_role
3. Enriching every candidate with accessible name, role, region, and states
"""

from __future__ import annotations

import re

INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "tab",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "checkbox",
        "radio",
        "combobox",
        "listbox",
        "option",
        "switch",
        "treeitem",
        "textbox",
    }
)

GRID_ROLES = frozenset(
    {
        "gridcell",
        "row",
        "cell",
        "columnheader",
        "rowheader",
    }
)

ENRICH_JS = """() => {
  function accName(el) {
    return (el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('title') || '')
      .trim()
      .slice(0, 120);
  }
  function region(el) {
    const landmarks = ['banner', 'navigation', 'main', 'complementary', 'contentinfo', 'form', 'search'];
    let cur = el;
    while (cur && cur !== document.body) {
      const role = (cur.getAttribute('role') || '').toLowerCase();
      if (landmarks.includes(role)) return role;
      if (cur.tagName === 'HEADER') return 'banner';
      if (cur.tagName === 'NAV') return 'navigation';
      if (cur.tagName === 'MAIN') return 'main';
      if (cur.tagName === 'FOOTER') return 'contentinfo';
      cur = cur.parentElement;
    }
    return '';
  }
  function states(el) {
    const s = [];
    const expanded = el.getAttribute('aria-expanded');
    if (expanded === 'true') s.push('expanded');
    if (expanded === 'false') s.push('collapsed');
    if (el.getAttribute('aria-haspopup')) s.push('haspopup');
    if (el.getAttribute('aria-selected') === 'true') s.push('selected');
    if (el.getAttribute('aria-disabled') === 'true' || el.disabled) s.push('disabled');
    if (el.getAttribute('aria-checked') === 'true') s.push('checked');
    return s;
  }
  const out = {};
  document.querySelectorAll('[data-crawl-id]').forEach(el => {
    const id = el.getAttribute('data-crawl-id');
    if (!id) return;
    out[id] = {
      ax_name: accName(el),
      ax_role: (el.getAttribute('role') || el.tagName.toLowerCase()),
      region: region(el),
      ax_states: states(el),
    };
  });
  return out;
}"""


def _crawl_id_from_selector(selector: str) -> str | None:
    match = re.search(r'data-crawl-id="(\d+)"', selector or "")
    return match.group(1) if match else None


def _next_crawl_id(page) -> int:
    return page.evaluate(
        """() => {
          let max = 0;
          for (const el of document.querySelectorAll('[data-crawl-id]')) {
            const n = parseInt(el.getAttribute('data-crawl-id'), 10);
            if (!isNaN(n) && n > max) max = n;
          }
          return max + 1;
        }"""
    )


def _flatten_interactive_nodes(
    node: dict | None,
    *,
    skip_grid_roles: bool,
    seen_keys: set[tuple[str, str]],
    out: list[dict],
) -> None:
    if not node:
        return

    role = (node.get("role") or "").lower()
    name = (node.get("name") or "").strip()

    if role in INTERACTIVE_ROLES and name:
        if not (skip_grid_roles and role in GRID_ROLES):
            key = (role, name)
            if key not in seen_keys:
                seen_keys.add(key)
                ax_states: list[str] = []
                for state_key in ("checked", "expanded", "selected", "pressed", "disabled"):
                    if node.get(state_key) is True:
                        ax_states.append(state_key)
                out.append({"role": role, "name": name, "ax_states": ax_states})

    for child in node.get("children") or []:
        _flatten_interactive_nodes(
            child,
            skip_grid_roles=skip_grid_roles,
            seen_keys=seen_keys,
            out=out,
        )


def _build_candidate_from_locator(locator, crawl_id: int, *, ax_role: str, ax_name: str) -> dict | None:
    try:
        if locator.count() == 0 or not locator.is_visible():
            return None
        meta = locator.evaluate(
            """(el) => ({
              label: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '')
                .trim()
                .slice(0, 120),
              id: el.id || '',
              className: typeof el.className === 'string' ? el.className : '',
              elementType: el.tagName.toLowerCase(),
            })"""
        )
    except Exception:
        return None

    tag = (meta.get("elementType") or "").lower()
    if tag == "a":
        return None

    try:
        locator.evaluate(
            "(el, id) => el.setAttribute('data-crawl-id', String(id))",
            crawl_id,
        )
    except Exception:
        return None

    label = (meta.get("label") or "").strip() or ax_name or tag
    return {
        "label": label,
        "id": meta.get("id") or "",
        "className": meta.get("className") or "",
        "selector": f'[data-crawl-id="{crawl_id}"]',
        "elementType": tag,
        "source": "accessibility",
        "ax_role": ax_role,
        "ax_name": ax_name or label,
    }


def _add_ax_candidates(page, dom_candidates: list[dict], ax_nodes: list[dict]) -> list[dict]:
    stamped_ids = {
        cid
        for c in dom_candidates
        if (cid := _crawl_id_from_selector(c.get("selector", "")))
    }
    added: list[dict] = []

    for node in ax_nodes:
        role = node["role"]
        name = node["name"]
        try:
            locator = page.get_by_role(role, name=name).first
        except Exception:
            continue

        try:
            if locator.count() == 0 or not locator.is_visible():
                continue
            existing = locator.evaluate("(el) => el.getAttribute('data-crawl-id')")
            if existing:
                continue
            if locator.evaluate(
                "(el) => el.getAttribute('aria-disabled') === 'true' || !!el.disabled"
            ):
                continue
        except Exception:
            continue

        crawl_id = _next_crawl_id(page)
        candidate = _build_candidate_from_locator(
            locator,
            crawl_id,
            ax_role=role,
            ax_name=name,
        )
        if not candidate:
            continue
        if str(crawl_id) in stamped_ids:
            continue
        stamped_ids.add(str(crawl_id))
        if node.get("ax_states"):
            candidate["ax_states"] = node["ax_states"]
        added.append(candidate)

    return added


def _apply_enrichment(candidates: list[dict], enrich_map: dict) -> None:
    for candidate in candidates:
        crawl_id = _crawl_id_from_selector(candidate.get("selector", ""))
        if not crawl_id:
            continue
        info = enrich_map.get(crawl_id) or enrich_map.get(str(crawl_id))
        if not info:
            continue
        if info.get("ax_name"):
            candidate["ax_name"] = info["ax_name"]
        if info.get("ax_role"):
            candidate["ax_role"] = info["ax_role"]
        if info.get("region"):
            candidate["region"] = info["region"]
        if info.get("ax_states"):
            candidate["ax_states"] = info["ax_states"]


def enhance_candidates_with_accessibility(
    page,
    candidates: list[dict],
    *,
    max_candidates: int = 200,
    skip_grid_roles: bool = True,
) -> list[dict]:
    """Merge AX-discovered triggers into DOM candidates and enrich all entries."""
    dom_candidates = list(candidates)

    try:
        snapshot = page.accessibility.snapshot(interesting_only=True)
    except Exception as exc:
        print(f"[AX] Snapshot failed ({exc}) — DOM-only discovery")
        return dom_candidates

    if not snapshot:
        print("[AX] Empty accessibility snapshot — DOM-only discovery")
        return dom_candidates

    ax_nodes: list[dict] = []
    _flatten_interactive_nodes(
        snapshot,
        skip_grid_roles=skip_grid_roles,
        seen_keys=set(),
        out=ax_nodes,
    )

    added = _add_ax_candidates(page, dom_candidates, ax_nodes)
    merged = dom_candidates + added

    try:
        enrich_map = page.evaluate(ENRICH_JS) or {}
    except Exception as exc:
        print(f"[AX] Enrichment failed ({exc})")
        enrich_map = {}

    _apply_enrichment(merged, enrich_map)

    if len(merged) > max_candidates:
        trimmed = merged[:max_candidates]
        print(
            f"[AX] Capped candidates at {max_candidates} "
            f"(DOM={len(dom_candidates)} AX-added={len(added)} raw={len(merged)})"
        )
        merged = trimmed
    else:
        print(f"[AX] DOM={len(dom_candidates)} AX-added={len(added)} total={len(merged)}")

    return merged
