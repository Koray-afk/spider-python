"""Wire crawled Zoho pages together — sidebar clicks load local HTML, no master index."""

import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

REPLICA_STYLE = """<style id="static-replica-ui-style">
  #static-replica-interaction-host {
    position: fixed;
    inset: 0;
    z-index: 99998;
    pointer-events: none;
  }
  #static-replica-interaction-host.active { pointer-events: auto; }
  .sr-int-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
  }
  .sr-int-modal-layer {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }
  .sr-int-modal-layer .sr-int-content {
    pointer-events: auto;
    max-width: 92vw;
    max-height: 92vh;
    overflow: auto;
  }
  .sr-int-panel-layer {
    position: fixed;
    inset: 0;
    pointer-events: none;
  }
  .sr-int-panel-layer .sr-int-content {
    pointer-events: auto;
    height: 100%;
    overflow: auto;
    background: #fff;
  }
  .sr-int-drawer-layer .sr-int-content { max-width: 480px; margin-left: auto; }
  .sr-int-sidebar-layer .sr-int-content { max-width: 360px; }
  .sr-int-floating {
    position: fixed;
    z-index: 99999;
    max-height: 70vh;
    overflow: auto;
  }
  .sr-int-hidden { display: none !important; }
  .main-nav-lhs .collapse,
  .main-nav-lhs ul.collapse,
  .main-nav-lhs .accordion-collapse {
    display: block !important;
    height: auto !important;
    visibility: visible !important;
    overflow: visible !important;
  }
  .main-nav-lhs ul[hidden],
  .main-nav-lhs [hidden].collapse {
    display: block !important;
  }
  .main-nav-lhs a[data-local-nav],
  .main-nav-lhs a[href*="index.html"] {
    pointer-events: auto !important;
    cursor: pointer !important;
  }
  a[href$="index.html"] { cursor: pointer; }
  a[href$="index.html"]:focus { outline: 2px solid #268ddd; outline-offset: 2px; }
</style>"""

UNIFIED_CORE_SCRIPT = """<script id="static-replica-core">
(function() {
  var ROUTES = __ROUTES_JSON__;
  var CURRENT = __CURRENT_SLUG__;
  var INTERACTIONS = __INTERACTIONS_JSON__;
  var host = null;
  var openItem = null;
  var openTrigger = null;

  function ensureHost() {
    if (!host) {
      host = document.createElement('div');
      host.id = 'static-replica-interaction-host';
      host.className = 'sr-int-host sr-int-hidden';
      document.body.appendChild(host);
    }
    return host;
  }

  function findCloseBtn(root) {
    return root.querySelector(
      '[data-dismiss="modal"], [data-bs-dismiss="modal"], [data-bs-dismiss="offcanvas"], ' +
      '[data-dismiss], .modal-close, .close, [aria-label="Close"], .btn-close'
    );
  }

  function closeOverlay() {
    if (!host) return;
    host.classList.remove('active');
    host.innerHTML = '';
    host.classList.add('sr-int-hidden');
    document.body.style.overflow = '';
    openItem = null;
    openTrigger = null;
  }

  function positionFloating(contentEl, triggerEl) {
    var r = triggerEl.getBoundingClientRect();
    contentEl.style.top = Math.min(r.bottom + 4, window.innerHeight - 40) + 'px';
    contentEl.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 320)) + 'px';
    contentEl.style.minWidth = Math.max(r.width, 160) + 'px';
  }

  function mountInteraction(item, triggerEl) {
    var tpl = document.getElementById(item.templateId);
    if (!tpl) return;

    var h = ensureHost();
    h.classList.remove('sr-int-hidden');
    var type = item.interactionType || 'modal';

    if (type === 'dropdown' || type === 'popover') {
      var floating = document.createElement('div');
      floating.className = 'sr-int-floating sr-int-' + type;
      floating.innerHTML = tpl.innerHTML;
      h.appendChild(floating);
      positionFloating(floating, triggerEl);
    } else if (type === 'drawer') {
      var drawer = document.createElement('div');
      drawer.className = 'sr-int-panel-layer sr-int-drawer-layer sr-int-' + type;
      var drawerBackdrop = document.createElement('div');
      drawerBackdrop.className = 'sr-int-backdrop';
      drawerBackdrop.addEventListener('click', closeOverlay);
      drawer.appendChild(drawerBackdrop);
      var drawerContent = document.createElement('div');
      drawerContent.className = 'sr-int-content';
      drawerContent.innerHTML = tpl.innerHTML;
      drawer.appendChild(drawerContent);
      h.appendChild(drawer);
      var drawerClose = findCloseBtn(drawerContent);
      if (drawerClose) drawerClose.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        closeOverlay();
      });
      document.body.style.overflow = 'hidden';
    } else if (type === 'sidebar') {
      var sidebar = document.createElement('div');
      sidebar.className = 'sr-int-panel-layer sr-int-sidebar-layer sr-int-' + type;
      var sbBackdrop = document.createElement('div');
      sbBackdrop.className = 'sr-int-backdrop';
      sbBackdrop.addEventListener('click', closeOverlay);
      sidebar.appendChild(sbBackdrop);
      var sbContent = document.createElement('div');
      sbContent.className = 'sr-int-content';
      sbContent.innerHTML = tpl.innerHTML;
      sidebar.appendChild(sbContent);
      h.appendChild(sidebar);
      var sbClose = findCloseBtn(sbContent);
      if (sbClose) sbClose.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        closeOverlay();
      });
      document.body.style.overflow = 'hidden';
    } else {
      var modal = document.createElement('div');
      modal.className = 'sr-int-modal-layer sr-int-' + type;
      var mdBackdrop = document.createElement('div');
      mdBackdrop.className = 'sr-int-backdrop';
      mdBackdrop.addEventListener('click', closeOverlay);
      modal.appendChild(mdBackdrop);
      var mdContent = document.createElement('div');
      mdContent.className = 'sr-int-content';
      mdContent.innerHTML = tpl.innerHTML;
      modal.appendChild(mdContent);
      h.appendChild(modal);
      var mdClose = findCloseBtn(mdContent);
      if (mdClose) mdClose.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        closeOverlay();
      });
      document.body.style.overflow = 'hidden';
    }

    h.classList.add('active');
    openItem = item;
    openTrigger = triggerEl;
  }

  function toggleInteraction(item, triggerEl) {
    if (openItem && openItem.templateId === item.templateId) {
      closeOverlay();
    } else {
      closeOverlay();
      mountInteraction(item, triggerEl);
    }
  }

  function navigateLocal(href) {
    if (!href) return;
    window.location.assign(href);
  }

  function isDismissClick(target) {
    return !!target.closest(
      '[data-dismiss="modal"], [data-bs-dismiss="modal"], [data-bs-dismiss="offcanvas"], ' +
      '[data-dismiss], .modal-close, .close, .btn-close, .sr-int-backdrop'
    );
  }

  document.addEventListener('click', function(e) {
    // 1. Dismissal / closing
    if (openItem) {
      if (isDismissClick(e.target)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        closeOverlay();
        return;
      }
      var inHost = e.target.closest('#static-replica-interaction-host');
      var onTrigger = openTrigger && (openTrigger === e.target || openTrigger.contains(e.target));
      if (openItem.interactionType === 'dropdown' || openItem.interactionType === 'popover') {
        if (!inHost && !onTrigger) {
          closeOverlay();
          return;
        }
      }
    }

    // Sidebar accordion (local layout, not Ember)
    var accordionBtn = e.target.closest('.accordion-button, .accordion-title');
    if (accordionBtn && !e.target.closest('a[data-local-nav]')) {
      e.preventDefault();
      e.stopPropagation();
      var expanded = accordionBtn.getAttribute('aria-expanded') === 'true';
      accordionBtn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      accordionBtn.classList.toggle('collapsed', expanded);
      var panelId = accordionBtn.getAttribute('aria-controls');
      if (panelId) {
        var panel = document.getElementById(panelId);
        if (panel) {
          panel.hidden = expanded;
          panel.classList.toggle('show', !expanded);
        }
      }
      return;
    }

    // 2. Interaction mounting (token-stamped triggers)
    for (var i = 0; i < INTERACTIONS.length; i++) {
      var item = INTERACTIONS[i];
      try {
        var trigger = document.querySelector(item.triggerSelector);
        if (!trigger || !(trigger === e.target || trigger.contains(e.target))) continue;
        e.preventDefault();
        e.stopImmediatePropagation();
        if (item.interactionType === 'dropdown' || item.interactionType === 'popover') {
          toggleInteraction(item, trigger);
        } else {
          if (openItem && openItem.templateId === item.templateId) {
            closeOverlay();
          } else {
            closeOverlay();
            mountInteraction(item, trigger);
          }
        }
        return;
      } catch (err) {}
    }

    // 3. Local SPA route forwarding
    var anchor = e.target.closest('a[href]');
    if (!anchor) return;
    var href = anchor.getAttribute('href');
    if (!href) return;

    if (anchor.getAttribute('data-local-nav') === '1' || href.indexOf('index.html') >= 0) {
      e.preventDefault();
      e.stopImmediatePropagation();
      navigateLocal(href);
      return;
    }

    if (href.indexOf('#/') === 0) {
      var route = '#/' + href.slice(2).split('?')[0].replace(/^\\/+|\\/+$/g, '');
      var target = ROUTES[route];
      if (!target) {
        var parts = route.slice(2).split('/');
        for (var j = parts.length; j > 0; j--) {
          var candidate = '#/' + parts.slice(0, j).join('/');
          if (ROUTES[candidate]) { target = ROUTES[candidate]; break; }
        }
      }
      if (target) {
        e.preventDefault();
        e.stopImmediatePropagation();
        navigateLocal(target);
      }
    }
  }, true);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && openItem && openItem.interactionType === 'modal') {
      closeOverlay();
    }
  });

  document.querySelectorAll('a[data-local-nav]').forEach(function(a) {
    var href = a.getAttribute('href') || '';
    if (href.indexOf(CURRENT) >= 0) a.classList.add('active');
  });
})();
</script>"""

VALID_INTERACTION_TYPES = frozenset(
    {"modal", "dropdown", "popover", "sidebar", "drawer", "wizard", "page"}
)

LEGACY_INTERACTION_TYPE_MAP = {
    "button": "page",
    "role_button": "page",
    "aria_haspopup": "dropdown",
    "dropdown_trigger": "dropdown",
    "menu_trigger": "dropdown",
}

TYPE_FRAGMENT_SELECTORS: dict[str, list[str]] = {
    "modal": [".modal.show", ".modal.in", '[role="dialog"]', ".modal"],
    "drawer": [".offcanvas.show", ".drawer.open", ".drawer.show", ".offcanvas", ".drawer"],
    "sidebar": [".sidebar.open", ".side-panel.open", "aside.sidebar-panel", ".side-panel"],
    "dropdown": [
        ".recent-activity-menu",
        ".dropdown-menu.show",
        ".dropdown-menu.open",
        '[role="menu"]',
        '[role="listbox"]',
        ".dropdown-menu-list",
        ".dropdown-menu",
    ],
    "popover": [".popover.show", ".popover.in", '[role="tooltip"]', ".popover"],
    "wizard": [".wizard-step.active", ".step-wizard .step.active", '[class*="wizard"] .active'],
    "page": [],
}

ZOHO_ROOT_WRAPPERS = ["#overlay-wrapper", "#modal-wrapper"]

FLOATING_OVERLAY_SELECTORS = [
    ".recent-activity-menu",
    ".dropdown-menu.show",
    ".dropdown-menu.open",
    ".dropdown-menu-list",
    ".dropdown-menu",
    ".modal.show",
    ".modal.in",
    ".modal",
    '[role="dialog"]',
    '[role="menu"]',
    '[role="listbox"]',
    ".popover.show",
    ".popover",
    ".offcanvas.show",
    ".drawer.open",
    ".drawer",
    ".sidebar.open",
    ".side-panel.open",
]

OVERLAY_FALLBACK_SELECTORS = FLOATING_OVERLAY_SELECTORS


def _normalize_interaction_type(raw_type: str) -> str:
    if raw_type in VALID_INTERACTION_TYPES:
        return raw_type
    return LEGACY_INTERACTION_TYPE_MAP.get(raw_type, "page")


def normalize_interaction_entry(entry: dict, page_slug: str, index: int) -> dict:
    html_file = entry.get("htmlFile") or entry.get("htmlPath") or ""
    if html_file.endswith("/index.html"):
        html_file = html_file.replace("/index.html", "/fragment.html")
    elif html_file and not html_file.endswith(".html"):
        html_file = f"{html_file.rstrip('/')}/fragment.html"

    trigger_token = entry.get("triggerToken", "")
    trigger_selector = entry.get("triggerSelector", "")
    if trigger_token and not trigger_selector.startswith("[data-sr-trigger"):
        trigger_selector = f'[data-sr-trigger="{trigger_token}"]'

    return {
        "triggerText": entry.get("triggerText", ""),
        "triggerSelector": trigger_selector,
        "triggerToken": trigger_token,
        "interactionType": _normalize_interaction_type(entry.get("interactionType", "page")),
        "sourcePage": entry.get("sourcePage") or page_slug,
        "htmlFile": html_file,
        "templateId": entry.get("templateId") or f"sr-int-{index}",
    }


def _prepare_overlay_element(el: Tag, interaction_type: str) -> None:
    el.attrs.pop("hidden", None)
    el.attrs.pop("aria-hidden", None)
    style = el.get("style", "")
    if style:
        el["style"] = re.sub(r"display\s*:\s*none", "display:block", style, flags=re.IGNORECASE)

    classes = el.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    classes = [c for c in classes if c not in {"hidden", "collapse"}]
    if interaction_type == "modal" and "modal" in classes and "show" not in classes:
        classes.append("show")
    if interaction_type == "dropdown" and "dropdown-menu" in " ".join(classes) and "show" not in classes:
        classes.append("show")
    if classes:
        el["class"] = classes


def extract_interaction_fragment(html: str, interaction_type: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []
    seen: set[int] = set()

    for wrapper_sel in ZOHO_ROOT_WRAPPERS:
        wrapper = soup.select_one(wrapper_sel)
        if not wrapper:
            continue
        for child in wrapper.find_all(recursive=False):
            if id(child) in seen:
                continue
            classes = " ".join(child.get("class") or [])
            if "backdrop" in classes:
                continue
            seen.add(id(child))
            _prepare_overlay_element(child, interaction_type)
            parts.append(str(child))
        if parts:
            return "\n".join(parts)

    selectors = TYPE_FRAGMENT_SELECTORS.get(interaction_type, [])
    if interaction_type == "page":
        selectors = OVERLAY_FALLBACK_SELECTORS

    for sel in selectors:
        for el in soup.select(sel):
            if id(el) in seen:
                continue
            classes = " ".join(el.get("class") or [])
            if interaction_type in ("modal", "drawer", "sidebar") and "backdrop" in classes:
                continue
            seen.add(id(el))
            _prepare_overlay_element(el, interaction_type)
            parts.append(str(el))

    if not parts:
        for sel in OVERLAY_FALLBACK_SELECTORS:
            for el in soup.select(sel):
                if id(el) in seen or el.get("hidden") is not None:
                    continue
                seen.add(id(el))
                _prepare_overlay_element(el, interaction_type)
                parts.append(str(el))

    if parts:
        return "\n".join(parts)
    return ""


def _fragment_key(fragment: str) -> str | None:
    if not fragment:
        return None
    clean = fragment.split("?")[0].strip("/")
    return f"#/{clean}" if clean else "#/home"


def hash_route_from_href(href: str) -> str | None:
    """#/quotes?filter_by=All → #/quotes"""
    if not href.startswith("#/"):
        return None
    route = href[2:].split("?")[0].strip("/")
    return f"#/{route}" if route else "#/home"


def normalize_spa_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    frag = parsed.fragment.split("?")[0] if parsed.fragment else ""
    if frag:
        return f"{parsed.scheme}://{parsed.netloc}{path}#{frag}"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def detect_layout(pages_dir: Path) -> str:
    if any(pages_dir.glob("*/index.html")):
        return "folder"
    if any(pages_dir.glob("*.html")):
        return "flat"
    return "folder"


def discover_html_files(pages_dir: Path) -> list[Path]:
    folder_pages = sorted(pages_dir.glob("*/index.html"))
    if folder_pages:
        return folder_pages
    return sorted(p for p in pages_dir.glob("*.html") if p.name != "index.html")


def discover_meta_files(pages_dir: Path) -> list[Path]:
    folder_meta = list(pages_dir.glob("*/index.meta"))
    if folder_meta:
        return folder_meta
    return list(pages_dir.glob("*.meta"))


def slug_from_html_path(html_path: Path, layout: str) -> str:
    if layout == "folder":
        return html_path.parent.name
    return html_path.stem


def local_href(from_slug: str, to_slug: str, layout: str) -> str:
    if layout == "flat":
        return f"{to_slug}.html"
    if from_slug == to_slug:
        return "index.html"
    return f"../{to_slug}/index.html"


def resolve_route_slug(href: str, slug_route_map: dict[str, str]) -> str | None:
    """Resolve a sidebar href to a crawled page slug."""
    if href in slug_route_map:
        return slug_route_map[href]

    route = hash_route_from_href(href)
    if route and route in slug_route_map:
        return slug_route_map[route]

    if route:
        trimmed = route.rstrip("/")
        if trimmed in slug_route_map:
            return slug_route_map[trimmed]
        parts = route[2:].split("/")
        for i in range(len(parts), 0, -1):
            candidate = "#/" + "/".join(parts[:i])
            if candidate in slug_route_map:
                return slug_route_map[candidate]

    if "://" in href:
        parsed = urlparse(href)
        norm = normalize_spa_url(href)
        if norm in slug_route_map:
            return slug_route_map[norm]
        key = _fragment_key(parsed.fragment)
        if key and key in slug_route_map:
            return slug_route_map[key]

    return None


def build_slug_route_map(sitemap: list, pages_dir: Path) -> dict[str, str]:
    route_map: dict[str, str] = {}

    def register(url: str, slug: str) -> None:
        parsed = urlparse(url)
        route_map[url] = slug
        route_map[normalize_spa_url(url)] = slug
        key = _fragment_key(parsed.fragment)
        if key:
            route_map[key] = slug
            route_map[key.rstrip("/")] = slug
        elif "books.zoho" in url:
            route_map["#/home"] = slug
            route_map["#/home/dashboard"] = slug

    # Only wire post-auth Zoho Books app routes — ignore marketing pages
    books_items = [i for i in sitemap if "books.zoho" in i.get("url", "")]
    for item in books_items:
        register(item["url"], item["slug"])

    for meta_path in discover_meta_files(pages_dir):
        slug = meta_path.parent.name if meta_path.name == "index.meta" else meta_path.stem
        url = meta_path.read_text(encoding="utf-8").strip()
        if url and "books.zoho" in url:
            register(url, slug)

    return route_map


def build_page_routes(from_slug: str, slug_route_map: dict[str, str], layout: str) -> dict[str, str]:
    """#/route → relative local path from this page."""
    routes: dict[str, str] = {}
    for key, slug in slug_route_map.items():
        if key.startswith("#/"):
            target = local_href(from_slug, slug, layout)
            routes[key] = target
            routes[key.rstrip("/")] = target
    return routes


def rewrite_route_links(
    html: str,
    slug_route_map: dict[str, str],
    from_slug: str,
    layout: str,
) -> str:
    def replace_href(match):
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith(("data:", "javascript:", "mailto:", "tel:")):
            return match.group(0)
        if layout == "flat" and url.endswith(".html"):
            return match.group(0)
        if layout == "folder" and ("../" in url or url.endswith("/index.html") or url == "index.html"):
            return match.group(0)

        slug = resolve_route_slug(url, slug_route_map)
        if slug:
            target = local_href(from_slug, slug, layout)
            return f'{attr}={quote}{target}{quote} data-local-nav="1"'
        return match.group(0)

    return re.sub(r'(href)=(["\'])([^"\']+)\2', replace_href, html)


def remove_base_tag(html: str) -> str:
    """Zoho sets <base href=https://books.zoho.in/...> which breaks local ../ links."""
    return re.sub(r"<base\b[^>]*>", "", html, flags=re.IGNORECASE)


def strip_scripts(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*\bas="script"[^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<link\b[^>]*rel=["\']modulepreload["\'][^>]*/?>', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+=([\"']).*?\1", "", html, flags=re.IGNORECASE)
    return html


def purge_application_environment(html: str) -> str:
    """Remove Ember/Zoho boot config so offline pages cannot re-hydrate the SPA."""
    html = re.sub(
        r'<meta\b[^>]*name=["\']zb/config/environment["\'][^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<meta\b[^>]*name=["\'][^"\']+/config/environment["\'][^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    return html


def expand_sidebar(html: str) -> str:
    html = re.sub(
        r'(<ul[^>]*class="[^"]*collapse[^"]*"[^>]*)\s+hidden(?:="[^"]*")?',
        r'\1',
        html,
    )
    html = re.sub(
        r'(<div[^>]*class="[^"]*accordion-collapse[^"]*"[^>]*)\s+hidden(?:="[^"]*")?',
        r'\1',
        html,
    )
    html = html.replace("accordion-button collapsed", "accordion-button")
    html = html.replace("accordion-title collapsed", "accordion-title")
    html = re.sub(
        r'class="([^"]*\bcollapse\b[^"]*)"',
        lambda m: f'class="{m.group(1)} show"' if "show" not in m.group(1) else m.group(0),
        html,
    )
    html = re.sub(r'aria-expanded="false"', 'aria-expanded="true"', html)
    return html


def inject_replica_style(html: str) -> str:
    if 'id="static-replica-ui-style"' in html:
        return html
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        return re.sub(r"(<head[^>]*>)", rf"\1\n{REPLICA_STYLE}", html, count=1, flags=re.IGNORECASE)
    return REPLICA_STYLE + html


def load_interaction_map(page_dir: Path, page_slug: str) -> list:
    map_path = page_dir / "interactions" / "interaction_map.json"
    if not map_path.exists():
        return []
    raw = json.loads(map_path.read_text(encoding="utf-8"))
    return [normalize_interaction_entry(entry, page_slug, idx) for idx, entry in enumerate(raw)]


def prepare_page_interactions(
    src_page_dir: Path,
    dest_page_dir: Path,
    page_slug: str,
) -> tuple[list[dict], int]:
    """Copy captures, extract overlay fragments, return runtime-ready interactions."""
    interactions_src = src_page_dir / "interactions"
    if not interactions_src.is_dir():
        return [], 0

    interactions_dest = dest_page_dir / "interactions"
    interactions_dest.mkdir(parents=True, exist_ok=True)

    raw_map: list[dict] = []
    map_path = interactions_src / "interaction_map.json"
    if map_path.exists():
        raw_map = json.loads(map_path.read_text(encoding="utf-8"))

    folder_entries: dict[str, dict] = {}
    for entry in raw_map:
        html_path = entry.get("htmlFile") or entry.get("htmlPath", "")
        folder = Path(html_path).parent.name if html_path else ""
        if folder:
            folder_entries[folder] = entry

    prepared: list[dict] = []
    count = 0

    for sub in sorted(interactions_src.iterdir()):
        if not sub.is_dir():
            continue

        folder_name = sub.name
        fragment_path = sub / "fragment.html"
        src_html = sub / "index.html"
        if not fragment_path.exists() and not src_html.exists():
            continue

        entry = folder_entries.get(folder_name, {})
        normalized = normalize_interaction_entry(
            {
                **entry,
                "htmlFile": f"interactions/{folder_name}/fragment.html",
            },
            page_slug,
            len(prepared),
        )

        out_dir = interactions_dest / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        if fragment_path.exists():
            fragment = fragment_path.read_text(encoding="utf-8")
        elif src_html.exists():
            html = strip_scripts(src_html.read_text(encoding="utf-8"))
            html = remove_base_tag(html)
            fragment = extract_interaction_fragment(html, normalized["interactionType"])
            if not fragment:
                fragment = extract_interaction_fragment(html, "page")
        else:
            continue

        (out_dir / "fragment.html").write_text(fragment, encoding="utf-8")
        if src_html.exists():
            html = strip_scripts(src_html.read_text(encoding="utf-8"))
            html = remove_base_tag(html)
            (out_dir / "index.html").write_text(html, encoding="utf-8")

        src_png = sub / "index.png"
        if src_png.exists():
            shutil.copy2(src_png, out_dir / "index.png")
        src_meta = sub / "index.meta"
        if src_meta.exists():
            shutil.copy2(src_meta, out_dir / "index.meta")

        normalized["_fragment_html"] = fragment
        prepared.append(normalized)
        count += 1

    if prepared:
        stitched_map = [
            {key: value for key, value in item.items() if key != "_fragment_html"}
            for item in prepared
        ]
        (interactions_dest / "interaction_map.json").write_text(
            json.dumps(stitched_map, indent=2),
            encoding="utf-8",
        )

    return prepared, count


def build_unified_core_script(
    from_slug: str,
    slug_route_map: dict[str, str],
    layout: str,
    interactions: list,
) -> str:
    routes = build_page_routes(from_slug, slug_route_map, layout)
    runtime = [
        {
            "triggerText": item["triggerText"],
            "triggerSelector": item["triggerSelector"],
            "triggerToken": item.get("triggerToken", ""),
            "interactionType": item["interactionType"],
            "sourcePage": item["sourcePage"],
            "htmlFile": item["htmlFile"],
            "templateId": item["templateId"],
        }
        for item in interactions
    ]
    return (
        UNIFIED_CORE_SCRIPT.replace("__ROUTES_JSON__", json.dumps(routes))
        .replace("__CURRENT_SLUG__", json.dumps(from_slug))
        .replace("__INTERACTIONS_JSON__", json.dumps(runtime))
    )


def _inject_before_body(html: str, snippet: str) -> str:
    """Insert snippet before </body> without re.sub (avoids escape issues in JS)."""
    match = re.search(r"</body>", html, flags=re.IGNORECASE)
    if not match:
        return html + snippet
    idx = match.start()
    return html[:idx] + snippet + "\n" + html[idx:]


def inject_replica_runtime(
    html: str,
    from_slug: str,
    slug_route_map: dict[str, str],
    layout: str,
    interactions: list,
) -> str:
    templates = []
    for item in interactions:
        fragment = item.get("_fragment_html", "")
        if not fragment:
            continue
        templates.append(f'<template id="{item["templateId"]}">{fragment}</template>')

    if templates:
        html = _inject_before_body(html, "\n".join(templates))

    script = build_unified_core_script(from_slug, slug_route_map, layout, interactions)
    return _inject_before_body(html, script)


def finalize_html(
    html: str,
    slug_route_map: dict[str, str],
    from_slug: str,
    layout: str,
    interactions: list | None = None,
) -> str:
    html = strip_scripts(html)
    html = purge_application_environment(html)
    html = remove_base_tag(html)
    html = expand_sidebar(html)
    html = inject_replica_style(html)
    html = rewrite_route_links(html, slug_route_map, from_slug, layout)
    return inject_replica_runtime(html, from_slug, slug_route_map, layout, interactions or [])


def rebuild_sitemap_from_disk(pages_dir: Path) -> list:
    sitemap = []
    for meta in sorted(pages_dir.glob("*/index.meta")):
        slug = meta.parent.name
        url = meta.read_text(encoding="utf-8").strip()
        if (meta.parent / "index.html").exists() and url:
            sitemap.append({"slug": slug, "url": url, "title": slug})
    return sitemap


def remove_stale_master_index(pages_dir: Path) -> None:
    """Remove old pages/index.html directory listing if present."""
    master = pages_dir / "index.html"
    if not master.is_file():
        return
    try:
        text = master.read_text(encoding="utf-8")
    except OSError:
        return
    if "Zoho Books — Offline" in text and "<ul>" in text:
        master.unlink()
        print("  removed stale pages/index.html master listing")


def pick_entry_slug(sitemap: list) -> str | None:
    for item in sitemap:
        url = item.get("url", "")
        if "books.zoho" in url and ("dashboard" in url or "dashboard" in item["slug"]):
            return item["slug"]
    for item in sitemap:
        if "books.zoho" in item.get("url", ""):
            return item["slug"]
    return sitemap[0]["slug"] if sitemap else None


def stitch_pages(pages_dir: str, output_dir: str | None = None) -> int:
    pages_path = Path(pages_dir)
    out_path = Path(output_dir) if output_dir else pages_path
    sitemap_path = pages_path / "sitemap.json"
    if not sitemap_path.exists():
        meta_sitemap = pages_path.parent / "metadata" / "sitemap.json"
        if meta_sitemap.exists():
            sitemap_path = meta_sitemap

    if sitemap_path.exists():
        sitemap = json.loads(sitemap_path.read_text(encoding="utf-8"))
    else:
        sitemap = []

    if not sitemap:
        sitemap = rebuild_sitemap_from_disk(pages_path)
        if sitemap:
            dest = out_path / "sitemap.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(sitemap, indent=2), encoding="utf-8")
            print(f"  rebuilt sitemap from {len(sitemap)} index.meta files")

    if not sitemap:
        raise FileNotFoundError(
            f"Missing {sitemap_path} and no pages/*/index.meta found — run the crawler first."
        )

    if not output_dir:
        remove_stale_master_index(pages_path)
    else:
        out_path.mkdir(parents=True, exist_ok=True)

    layout = detect_layout(pages_path)
    html_files = discover_html_files(pages_path)
    if not html_files:
        raise FileNotFoundError(
            f"No page HTML found under {pages_path}. "
            f"Expected pages/<slug>/index.html."
        )

    slug_route_map = build_slug_route_map(sitemap, pages_path)
    count = 0
    interaction_pages = 0

    for html_file in html_files:
        from_slug = slug_from_html_path(html_file, layout)
        html = html_file.read_text(encoding="utf-8")
        dest_dir = out_path / from_slug if layout == "folder" else out_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        interactions, ic = prepare_page_interactions(html_file.parent, dest_dir, from_slug)
        stitched = finalize_html(html, slug_route_map, from_slug, layout, interactions)
        dest = dest_dir / "index.html" if layout == "folder" else dest_dir / f"{from_slug}.html"
        dest.write_text(stitched, encoding="utf-8")
        meta = html_file.parent / "index.meta"
        if layout == "folder" and meta.exists():
            (dest_dir / "index.meta").write_text(meta.read_text(encoding="utf-8"), encoding="utf-8")
        if ic:
            interaction_pages += 1
        count += 1
        suffix = f" (+{ic} interactions)" if ic else ""
        print(f"  stitched {from_slug}{suffix}")

    if output_dir:
        (out_path / "sitemap.json").write_text(json.dumps(sitemap, indent=2), encoding="utf-8")

    print(f"  {count} pages → {out_path}")
    if interaction_pages:
        print(f"  {interaction_pages} pages with wired interactions")
    return count


def stitch_application(app_name: str) -> dict:
    from storage.storage_manager import (
        create_app_storage,
        get_raw_html_dir,
        get_stitched_html_dir,
    )

    create_app_storage(app_name)
    raw_dir = get_raw_html_dir(app_name)
    stitched_dir = get_stitched_html_dir(app_name)

    if not raw_dir.is_dir():
        raise FileNotFoundError(f"No raw HTML at {raw_dir}")

    count = stitch_pages(str(raw_dir), str(stitched_dir))
    return {"pages_stitched": count, "stitched_dir": str(stitched_dir)}
