# Building with Cursor

This note records how **Cursor** was used to extend and debug **Spider Python** — especially the Ink N Dyes (`inkndye`) crawl → reconcile → stitch → serve path.

It is not product docs for Spider itself (see [README.md](README.md)). It is a working log of agent-assisted development patterns that worked on this repo.

---

## What we were building

Spider visits a real app (Playwright + Chrome), saves HTML/screenshots/interactions, reconciles click-induced UI, stitches a static clone, and serves it at `localhost:8000`.

For **inkndyes.com**, the generic BFS crawler was not enough:

- Categories live under `/category?name=…`
- Product detail is a **stateful SPA route** (`/productDetails`) that only has real content after clicking **VIEW COLORS** from a category page
- Cold loads of `/productDetails` show “No product details available”

That forced a dedicated session crawler and several stitch/runtime fixes — largely written with Cursor in the loop.

---

## How Cursor was used day to day

### 1. Start from the broken UI (screenshots)

Typical flow:

1. Serve the clone (`python main.py serve inkndye`)
2. Click around; take a screenshot of what fails
3. Paste the screenshot into Cursor with a short question (“why doesn’t back / accordion / colour catalogue work?”)

Cursor inspected crawl folders (`storage/apps/inkndye/crawl/…`), stitched HTML, `runtime.js`, and stitch logs — then explained **root cause** before writing code.

Examples of failures diagnosed this way:

| Symptom | Root cause found with Cursor |
|--------|------------------------------|
| Sidebar categories / VIEW COLORS dead in clone | Fake selectors, empty triggers, query params stripped in route index |
| Purple Cotton hero missing | Inline `background-image: url(...)` never localized |
| Product detail interactions missing | Session crawler saved snapshots only; no `crawl_interactions` on product pages |
| Accordion / colour drawer empty | Collapsed DOM snapshot; drawer only toggles `translate-x-full` → `translate-x-0` |

### 2. Ask mode → Agent mode

A useful split:

- **Ask mode** — explore `crawler_v2.py`, `stitcher_v1.py`, `config.py`, crawl artifacts; get a diagnosis and a plan **without** editing files
- **Agent mode** — implement the agreed fix (often after: “please implement”)

That kept large architectural choices (e.g. “session crawler vs hardcoded `runtime.js`”) explicit before code landed.

### 3. Point at terminal output

When a crawl finished with `0 interactions saved`, pasting the terminal selection was enough for Cursor to find:

```text
_prepare() takes 0 positional arguments but 1 was given
```

Fix: `prepare_page_fn` must accept `(ipage)`; clear failed partial captures so retries work.

### 4. Paste live DOM when capture isn’t enough

For the colour catalogue drawer, the real site only flips CSS classes (`translate-x-full` ↔ `translate-x-0`). Interaction capture / reconciliation struggle with that. Cursor was given **before/after HTML** and asked to add a **manual** handler in `storage/apps/inkndye/stitched/runtime.js` (open on catalogue click; close on × / CANCEL / Esc) outside the main pipeline.

### 5. Keep changes in the real files the pipeline owns

Most work went into:

| File | Role |
|------|------|
| `config.py` | App settings, mandatory interaction labels, query params |
| `crawler_v2.py` | `crawl_inkndye()`, product interaction pass, session replay |
| `crawler_scripts.json` | Discover / fingerprint / classify JS |
| `reconciler.py` | Slide-panel fallback when DOM length barely changes |
| `stitcher_v1.py` | Wiring + `RUNTIME_JS` template (survives re-stitch) |
| `asset_localizer.py` | Inline `style="…url(…)…"` rewriting |
| `storage/apps/inkndye/stitched/runtime.js` | Live clone behaviour (sometimes patched by hand) |

---

## Ink N Dyes arc (Cursor-assisted)

Rough sequence that Cursor helped design and implement:

1. **Session crawler** — one tab; sidebar category clicks; **VIEW COLORS** → unique product slugs (`productDetails-Cotton-2-80-Compact`); checkpoint resume
2. **Stitch wiring** — real `trigger` snapshots; query-aware routes; sidebar `<li>` label wiring
3. **Assets** — localize inline background images (hero banner)
4. **Product interactions** — after save, run discovery + `crawl_interactions` with `prepare_page_fn` replaying category → VIEW COLORS (SPA context)
5. **Iterate from bugs** — `_prepare` signature, empty `interactions.json` as “done”, ranker marking accordions as `tab_switch`
6. **Manual runtime** — colour drawer open/close when class-toggle UIs don’t reconcile cleanly

Commands used while iterating:

```bash
python main.py crawl-postauth inkndye
python main.py crawl-interactions inkndye
python main.py reconcile inkndye
python main.py stitch inkndye
python main.py serve inkndye
```

---

## Prompts that worked well

- **Problem + constraint:** “Don’t open a new browser per link; keep one tab and real clicks; write a separate crawler only for inkndye in `crawler_v2.py`.”
- **Screenshot + question:** “Why weren’t back, accordion, and colour catalogue captured?”
- **Architecture preference:** “Capture via interaction pipeline without hardcoding inkndye in `runtime.js`” — then later: “For this drawer, manually add listeners in stitched `runtime.js`.”
- **Error paste:** Terminal lines with `[BFS] Interaction not scraped` / `Done: 0 interactions saved`
- **HTML before/after:** Closed vs open drawer markup for class-toggle behaviour

---

## Lessons for using Cursor on this codebase

1. **Serve the clone and show Cursor what you see** — screenshots beat abstract “stitch is broken.”
2. **Ask for diagnosis first on SPA/stateful bugs** — product detail and class-toggle drawers need understanding before patches.
3. **Prefer pipeline fixes when possible** (crawl / reconcile / stitch); use **manual `runtime.js`** only for UI that never appears as new DOM.
4. **After crawler changes, re-run interactions → reconcile → stitch** — editing only stitched HTML is temporary until the next stitch.
5. **Patch both `stitcher_v1.py`’s `RUNTIME_JS` and `stitched/runtime.js`** if you need the fix to survive a re-stitch *and* work immediately under `serve`.
6. **Treat empty `interactions.json` as failure** — don’t mark a page “done” just because `discovered.json` exists.

---

## Related reading

- [README.md](README.md) — crawl / reconcile / stitch / serve pipeline
- `config.py` → `"inkndye"` — seeds, mandatory labels, session navigator flags
- `crawler_v2.py` → `crawl_inkndye`, `_inkndye_capture_product_interactions`
