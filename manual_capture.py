"""Interactive manual interaction capture — separate from automated crawl.

Click in the browser to record a trigger; type ``capture`` to save HTML + screenshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from crawler_v2 import (
    CLASSIFY_JS,
    _goto_clean,
    ensure_auth,
    normalize_url,
    page_slug,
    prepare_context,
    save_interaction_capture,
    slugify_label,
    USER_AGENT,
)
from storage.storage_manager import get_crawl_dir

_SCRIPTS = json.loads(
    Path(__file__).with_name("crawler_scripts.json").read_text(encoding="utf-8")
)
_EXTRACT_ELEMENT = _SCRIPTS["extract_element"]

# Installed in every frame (main + iframes). Capture phase so we run before SPA handlers.
FRAME_CLICK_LISTENER = f"""() => {{
  if (window.__SPIDER_MANUAL_CLICK__) return;
  window.__SPIDER_MANUAL_CLICK__ = true;
  const extractElement = {_EXTRACT_ELEMENT};
  const pick = (raw) => {{
    let el = raw;
    if (!el || el.nodeType !== 1) return null;
    if (el.closest) {{
      const clickable = el.closest(
        'button, a, [role="button"], [role="menuitem"], [role="tab"], '
        + '[aria-haspopup], input[type="submit"], input[type="button"], '
        + '.btn, .menu-link, [data-bs-toggle], [data-kt-menu-trigger]'
      );
      if (clickable) el = clickable;
    }}
    return el;
  }};
  const record = (raw) => {{
    const el = pick(raw);
    if (!el) return;
    try {{
      window.__SPIDER_LAST_CLICK__ = extractElement(el);
    }} catch (_) {{
      window.__SPIDER_LAST_CLICK__ = {{
        tag_name: el.tagName ? el.tagName.toLowerCase() : '',
        text: (el.innerText || el.textContent || '').trim().slice(0, 300),
        id: el.id || '',
        class_name: typeof el.className === 'string' ? el.className : '',
        outer_html: el.outerHTML || ''
      }};
    }}
    window.__SPIDER_CLICK_URL__ = location.href;
    window.__SPIDER_CLICK_TITLE__ = document.title;
  }};
  document.addEventListener('click', (e) => record(e.target), true);
  document.addEventListener('pointerdown', (e) => record(e.target), true);
}}"""

READ_LAST_CLICK = """() => ({
  element: window.__SPIDER_LAST_CLICK__ || null,
  clickUrl: window.__SPIDER_CLICK_URL__ || '',
  clickTitle: window.__SPIDER_CLICK_TITLE__ || ''
})"""


def _install_click_listeners(page) -> None:
    for frame in page.frames:
        try:
            frame.evaluate(FRAME_CLICK_LISTENER)
        except Exception:
            pass


def _read_last_click(page) -> dict:
    for frame in reversed(page.frames):
        try:
            data = frame.evaluate(READ_LAST_CLICK) or {}
            if data.get("element"):
                return data
        except Exception:
            continue
    return {}


def _click_label(element: dict) -> str:
    return (
        (element.get("text") or element.get("aria_label") or "").strip()
        or element.get("tag_name")
        or "element"
    )


def _build_url_index(crawl_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not crawl_root.is_dir():
        return index
    for page_dir in crawl_root.iterdir():
        if not page_dir.is_dir() or not (page_dir / "page.html").is_file():
            continue
        meta_path = page_dir / "metadata.json"
        if meta_path.is_file():
            try:
                url = json.loads(meta_path.read_text(encoding="utf-8")).get("url", "")
                if url:
                    index[normalize_url(url)] = page_dir
            except Exception:
                pass
    return index


def _resolve_page_dir(crawl_root: Path, url: str, url_index: dict[str, Path]) -> Path | None:
    norm = normalize_url(url)
    if norm in url_index:
        return url_index[norm]
    slug_dir = crawl_root / page_slug(url)
    if (slug_dir / "page.html").is_file():
        return slug_dir
    return None


def _next_manual_folder(interactions_dir: Path, label: str) -> Path:
    interactions_dir.mkdir(parents=True, exist_ok=True)
    max_n = 0
    for sub in interactions_dir.iterdir():
        if sub.is_dir() and len(sub.name) >= 4 and sub.name.startswith("M"):
            try:
                max_n = max(max_n, int(sub.name[1:4]))
            except ValueError:
                pass
    folder_name = f"M{max_n + 1:03d}-{slugify_label(label)}"
    return interactions_dir / folder_name


def _append_registry(interactions_dir: Path, folder_name: str, label: str) -> None:
    reg_path = interactions_dir / "interactions.json"
    registry: list[dict] = []
    if reg_path.is_file():
        try:
            registry = json.loads(reg_path.read_text(encoding="utf-8")) or []
        except Exception:
            registry = []
    rel_path = f"interactions/{folder_name}"
    registry.append(
        {
            "label": label,
            "selector": "",
            "interaction_path": rel_path,
            "relationship_file": f"{rel_path}/relationship.json",
            "capture_mode": "manual",
        }
    )
    reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def _mark_manual(folder: Path) -> None:
    for name in ("relationship.json", "metadata.json"):
        path = folder / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["capture_mode"] = "manual"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _print_status(page, crawl_root: Path, url_index: dict[str, Path]) -> None:
    data = _read_last_click(page)
    element = data.get("element") or {}
    click_url = data.get("clickUrl") or ""
    label = _click_label(element)
    page_dir = _resolve_page_dir(crawl_root, click_url, url_index) if click_url else None
    print(f"  Browser URL: {page.url}")
    print(f"  Frames:      {len(page.frames)}")
    if element:
        print(f"  Last click:  {label} ({element.get('tag_name', '')})")
        print(f"  Click URL:   {click_url}")
        if page_dir:
            print(f"  Parent page: {page_dir.name}")
        else:
            print("  Parent page: (not found — page must be crawled first)")
    else:
        print("  Last click:  (none — click in the Playwright Chrome window, then try status)")


def _do_capture(page, crawl_root: Path, url_index: dict[str, Path], *, skip_screenshots: bool) -> bool:
    data = _read_last_click(page)
    element = data.get("element")
    if not element:
        print("[MANUAL] No click recorded.")
        print("[MANUAL] Click a button in the Playwright Chrome window (not another browser), then capture.")
        return False

    before_url = data.get("clickUrl") or page.url
    before_title = data.get("clickTitle") or page.title()
    page_dir = _resolve_page_dir(crawl_root, before_url, url_index)
    if page_dir is None:
        print(f"[MANUAL] No crawled page for click URL: {before_url}")
        print("[MANUAL] Crawl this page first, then try again.")
        return False

    if normalize_url(page.url) != normalize_url(before_url):
        print(f"[MANUAL] Note: URL changed since click ({before_url} → {page.url})")

    meta_path = page_dir / "metadata.json"
    source_url = before_url
    if meta_path.is_file():
        try:
            source_url = json.loads(meta_path.read_text(encoding="utf-8")).get("url") or before_url
        except Exception:
            pass

    label = _click_label(element)[:120]
    item = {
        "label": label,
        "id": element.get("id", ""),
        "className": element.get("class_name", ""),
        "elementType": element.get("tag_name", ""),
    }

    interactions_dir = page_dir / "interactions"
    folder = _next_manual_folder(interactions_dir, label)
    folder_name = folder.name

    try:
        itype = page.evaluate(CLASSIFY_JS)
    except Exception:
        itype = "unknown"

    save_interaction_capture(
        folder,
        page,
        source_slug=page_dir.name,
        source_url=source_url,
        before_url=before_url,
        before_title=before_title,
        item=item,
        selector="",
        itype=itype,
        crawl_root=crawl_root,
        element=element,
        skip_screenshots=skip_screenshots,
    )
    _mark_manual(folder)
    _append_registry(interactions_dir, folder_name, label)

    print(f"[MANUAL] Saved → {page_dir.name}/interactions/{folder_name}")
    print("[MANUAL] Next: python main.py reconcile <app> && python main.py stitch <app>")
    return True


def run_manual_capture(app_name: str, cfg: dict, args: list[str]) -> None:
    crawl_root = get_crawl_dir(app_name)
    if not crawl_root.is_dir():
        print(f"[MANUAL] No crawl output at {crawl_root} — run crawl first.")
        sys.exit(1)

    start_url = cfg.get("post_auth_home") or cfg.get("pre_auth_home", "")
    if "--url" in args:
        i = args.index("--url")
        try:
            start_url = args[i + 1]
        except IndexError:
            print("Error: --url requires a URL")
            sys.exit(1)

    skip_screenshots = bool(cfg.get("crawl_skip_screenshots"))
    wait_ms = int(cfg.get("crawl_wait_after_load_ms", 2000))
    use_networkidle = bool(cfg.get("crawl_use_networkidle", True))
    wait_for_stripe = bool(cfg.get("crawl_wait_for_stripe_content", False))
    url_index = _build_url_index(crawl_root)

    print("[MANUAL] Interactive capture session")
    print("[MANUAL] Use the Chrome window Playwright opens (not a separate browser tab).")
    print("[MANUAL] Click to record trigger — you'll see 'Recorded click: ...' in this terminal.")
    print("[MANUAL] Type 'capture' to save HTML + screenshot.")
    print("[MANUAL] Commands: capture | status | goto <url> | quit")
    print()

    with sync_playwright() as p:
        auth_file = ensure_auth(p, cfg["login_url"], app_name)
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            storage_state=auth_file,
        )
        prepare_context(context)
        page = context.new_page()

        def _on_click(_click) -> None:
            page.wait_for_timeout(50)
            _install_click_listeners(page)
            data = _read_last_click(page)
            element = data.get("element")
            if element:
                print(f"[MANUAL] Recorded click: {_click_label(element)[:80]}")

        page.on("click", _on_click)
        page.on("load", lambda _=None: _install_click_listeners(page))
        page.on("framenavigated", lambda _=None: _install_click_listeners(page))

        if start_url:
            print(f"[MANUAL] Opening {start_url}")
            _goto_clean(
                page,
                start_url,
                use_networkidle=use_networkidle,
                wait_ms=wait_ms,
                wait_for_stripe_content=wait_for_stripe,
            )
            _install_click_listeners(page)

        try:
            while True:
                try:
                    line = input("manual> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not line:
                    continue

                cmd = line.split()[0].lower()
                rest = line[len(cmd) :].strip()

                if cmd in ("quit", "q", "exit"):
                    break
                if cmd in ("capture", "c"):
                    _do_capture(page, crawl_root, url_index, skip_screenshots=skip_screenshots)
                elif cmd in ("status", "s"):
                    _print_status(page, crawl_root, url_index)
                elif cmd == "goto" and rest:
                    print(f"[MANUAL] Navigating to {rest}")
                    _goto_clean(
                        page,
                        rest,
                        use_networkidle=use_networkidle,
                        wait_ms=wait_ms,
                        wait_for_stripe_content=wait_for_stripe,
                    )
                    _install_click_listeners(page)
                elif cmd == "goto":
                    print("[MANUAL] Usage: goto <url>")
                else:
                    print("[MANUAL] Unknown command. Use: capture | status | goto <url> | quit")

        finally:
            context.close()
            browser.close()

    print("[MANUAL] Done.")
