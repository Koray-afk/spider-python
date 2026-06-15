"""
JS agent — generates interaction JS from catalog specs and validates state changes.

Flow per page
-------------
1. Load stitched HTML (with data-agent-id) in Playwright via local HTTP server.
2. Record DOM state before/after each click (MutationObserver + snapshot).
3. Generate JS via Gemini from cleaned HTML + interactive element spec.
4. Inject JS, re-test every interactive element.
5. If failures remain, send failure report back to Gemini (max 2 fix rounds).
6. Save final JS to analysis/js/{slug}.js and inject into pages/{slug}.html.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from offline_interactions import DEFAULT_INTERACTION_JS
from services.gemini_service import generate_interaction_js

INTERACTIVE_ACTIONS = {"navigate", "toggle", "open_modal", "submit"}
MAX_TEST_ELEMENTS = 20
SERVER_PORT = 8765

_MUTATION_OBSERVER = """
(function() {
  if (window.__zbObserver) return;
  window.__zbMutations = [];
  window.__zbObserver = new MutationObserver(function(records) {
    records.forEach(function(r) {
      if (r.type === 'attributes') {
        window.__zbMutations.push({
          type: 'attr', attr: r.attributeName,
          id: r.target.id || (r.target.dataset && r.target.dataset.agentId) || '',
          now: r.target.getAttribute(r.attributeName),
        });
      } else if (r.type === 'childList') {
        r.addedNodes.forEach(function(n) {
          if (n.nodeType === 1) window.__zbMutations.push({type:'added', tag:n.tagName, id:n.id});
        });
      }
    });
  });
  window.__zbObserver.observe(document.body, {subtree:true, childList:true, attributes:true});
  window.__zbClearMutations = function() { window.__zbMutations = []; };
})();
"""

_STATE_SNAPSHOT = """
(function() {
  return JSON.stringify({
    url: location.href,
    modal: !!document.getElementById('_offline_modal') || !!document.getElementById('_zb_modal'),
    openDropdowns: document.querySelectorAll('.dropdown.show').length,
    activeTabs: Array.from(document.querySelectorAll('[role=tab][aria-selected=true]')).map(function(t){
      return t.textContent.trim().slice(0,30);
    }),
  });
})()
"""

_FLUSH_MUTATIONS = """
(function() {
  var m = JSON.stringify(window.__zbMutations || []);
  window.__zbMutations = [];
  return m;
})()
"""


def _clean_js(raw: str) -> str:
    js = raw.strip()
    if "```" in js:
        parts = js.split("```")
        js = parts[1] if len(parts) > 1 else js
        js = re.sub(r"^(javascript|js)\s*\n", "", js.strip())
    js = js.strip()
    if not re.match(r"^\s*\(function", js):
        js = f"(function() {{\n{js}\n}})();"
    # Safety fixes
    js = re.sub(r"(addEventListener\s*\([^)]+),\s*true\s*\)", r"\1)", js)
    js = js.replace("\\u201c", '"').replace("\\u201d", '"')
    return js


def _inject_js(html: str, js: str) -> str:
    tag = f'<script data-agent-interaction-js="1">\n{js}\n</script>'
    html = re.sub(
        r'<script[^>]*data-agent-interaction-js[^>]*>[\s\S]*?</script>\s*',
        "",
        html,
    )
    html = re.sub(
        r'<script[^>]*data-offline-ui[^>]*>[\s\S]*?</script>\s*',
        "",
        html,
    )
    # String concat — avoid re.sub(repl=js) which breaks on backslashes in JS
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html[:idx] + tag + "\n" + html[idx:]
    return html + tag


class PageSession:
    def __init__(self, slug: str, pages_dir: Path, analysis_dir: Path, base_url: str):
        self.slug = slug
        self.pages_dir = pages_dir
        self.analysis_dir = analysis_dir
        self.page_path = pages_dir / f"{slug}.html"
        self.js_path = analysis_dir / "js" / f"{slug}.js"
        self.js_path.parent.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self.page = self._browser.new_page(viewport={"width": 1440, "height": 900})

    def close(self):
        self._browser.close()
        self._pw.stop()

    def load(self):
        url = f"{self.base_url}/{self.slug}.html"
        self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
        self.page.wait_for_timeout(800)
        self.page.evaluate(_MUTATION_OBSERVER)

    def write_js(self, js: str):
        js = _clean_js(js)
        html = _inject_js(self.page_path.read_text(encoding="utf-8"), js)
        self.page_path.write_text(html, encoding="utf-8")
        self.js_path.write_text(js, encoding="utf-8")
        self.load()

    def _click_element(self, eid: str) -> dict[str, Any]:
        self.load()
        self.page.evaluate("window.__zbClearMutations && window.__zbClearMutations()")
        state_before = json.loads(self.page.evaluate(_STATE_SNAPSHOT))
        url_before = self.page.url

        loc = self.page.locator(f'[data-agent-id="{eid}"]')
        if loc.count() == 0:
            return {"ok": False, "note": "element not in DOM"}

        is_nav = self.page.evaluate(f"""() => {{
            var el = document.querySelector('[data-agent-id="{eid}"]');
            var a = el && el.closest('a[href$=".html"]');
            return !!(a && a.href);
        }}""")

        try:
            loc.first.scroll_into_view_if_needed(timeout=2000)
            if is_nav:
                loc.first.click(timeout=4000)
            else:
                loc.first.click(timeout=4000, force=True)
            self.page.wait_for_timeout(700)
        except Exception as ex:
            return {"ok": False, "note": str(ex)[:120]}

        mutations = json.loads(self.page.evaluate(_FLUSH_MUTATIONS))
        state_after = json.loads(self.page.evaluate(_STATE_SNAPSHOT))
        url_after = self.page.url

        return {
            "ok": True,
            "url_before": url_before,
            "url_after": url_after,
            "navigated": url_before != url_after,
            "mutations": mutations[:30],
            "state_before": state_before,
            "state_after": state_after,
            "is_nav_link": is_nav,
        }

    def validate(self, spec: dict) -> dict:
        elements = [
            e for e in spec.get("elements", [])
            if e.get("expected_action") in INTERACTIVE_ACTIONS
        ][:MAX_TEST_ELEMENTS]

        results = []
        for elem in elements:
            eid = elem["id"]
            action = elem.get("expected_action", "")
            target = elem.get("expected_target") or elem.get("href") or ""

            click = self._click_element(eid)
            if not click.get("ok"):
                results.append({"id": eid, "action": action, "ok": False, "note": click.get("note")})
                continue

            ok = False
            note = ""

            if action == "navigate":
                if target.endswith(".html"):
                    ok = click["navigated"] and click["url_after"].endswith(target)
                    note = f"nav → {click['url_after'].split('/')[-1]}"
                elif target.startswith("#/"):
                    ok = len(click["mutations"]) > 0 or click["state_after"].get("modal")
                    note = "hash route toast/modal"
                else:
                    ok = click["navigated"] or len(click["mutations"]) > 0
                    note = "navigation effect"

            elif action in ("toggle", "open_modal", "submit"):
                mutated = len(click["mutations"]) > 0
                state_changed = click["state_before"] != click["state_after"]
                modal = click["state_after"].get("modal")
                ok = mutated or state_changed or modal or click["navigated"]
                note = f"{len(click['mutations'])} mutations, state_changed={state_changed}"

            results.append({
                "id": eid,
                "action": action,
                "ok": ok,
                "note": note,
                "text": elem.get("text", "")[:40],
            })

        passed = sum(1 for r in results if r["ok"])
        return {"passed": passed, "failed": len(results) - passed, "results": results}


def _start_server(pages_dir: Path) -> subprocess.Popen:
    return subprocess.Popen(
        ["python3", "-m", "http.server", str(SERVER_PORT)],
        cwd=str(pages_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_js_agent(
    slug: str,
    pages_dir: str = "pages",
    analysis_dir: str = "analysis",
    max_rounds: int = 2,
) -> dict:
    pages_path = Path(pages_dir).resolve()
    analysis_path = Path(analysis_dir).resolve()
    spec_path = analysis_path / "specs" / f"{slug}.json"
    cleaned_path = analysis_path / "cleaned" / f"{slug}.cleaned.html"
    png_path = pages_path / f"{slug}.png"

    if not spec_path.exists():
        return {"error": f"spec not found: {spec_path}"}

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    cleaned = cleaned_path.read_text(encoding="utf-8") if cleaned_path.exists() else ""

    interactive = [
        e for e in spec.get("elements", [])
        if e.get("expected_action") in INTERACTIVE_ACTIONS
    ][:40]

    server = _start_server(pages_path)
    time.sleep(1)
    base_url = f"http://localhost:{SERVER_PORT}"

    last_result: dict = {}
    failures: list[dict] = []

    try:
        session = PageSession(slug, pages_path, analysis_path, base_url)

        for round_num in range(1, max_rounds + 1):
            print(f"  [{slug}] generate JS (round {round_num})…", flush=True)
            try:
                raw_js = generate_interaction_js(
                    page_slug=slug,
                    cleaned_html=cleaned,
                    interactive_elements=interactive,
                    png_path=str(png_path) if png_path.exists() else None,
                    failures=failures if failures else None,
                )
            except Exception as exc:
                print(f"  [{slug}] Gemini skipped ({exc}) — using built-in JS", flush=True)
                raw_js = DEFAULT_INTERACTION_JS
            session.write_js(raw_js)

            print(f"  [{slug}] validate clicks…", flush=True)
            last_result = session.validate(spec)
            passed = last_result.get("passed", 0)
            failed = last_result.get("failed", 0)
            print(f"  [{slug}] → passed={passed}, failed={failed}", flush=True)

            if failed == 0:
                break

            failures = [r for r in last_result.get("results", []) if not r.get("ok")]

        # Save validation report
        report_dir = analysis_path / "validation"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{slug}.json").write_text(json.dumps(last_result, indent=2), encoding="utf-8")

        session.close()
    finally:
        server.terminate()
        server.wait(timeout=5)

    return last_result


def run_all(pages_dir: str = "pages", analysis_dir: str = "analysis") -> None:
    specs_dir = Path(analysis_dir) / "specs"
    if not specs_dir.exists():
        print("No specs found — run catalog step first.")
        return

    for spec_file in sorted(specs_dir.glob("*.json")):
        slug = spec_file.stem
        print(f"\n{'='*50}\nJS Agent: {slug}\n{'='*50}")
        result = run_js_agent(slug, pages_dir=pages_dir, analysis_dir=analysis_dir)
        print(f"  Final: passed={result.get('passed','?')}, failed={result.get('failed','?')}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--slug")
    p.add_argument("--pages-dir", default="pages")
    p.add_argument("--analysis-dir", default="analysis")
    args = p.parse_args()
    if args.slug:
        run_js_agent(args.slug, pages_dir=args.pages_dir, analysis_dir=args.analysis_dir)
    else:
        run_all(pages_dir=args.pages_dir, analysis_dir=args.analysis_dir)
