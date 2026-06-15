# Spider Python

A Playwright crawler that captures SaaS application pages for design reference and analysis.

The crawler **only collects data** — HTML, screenshots, metadata, and UI interaction captures. It does not rewrite HTML, build offline replicas, or run a replay backend.

---

## What it captures

Every page is saved as a **static UI snapshot**. Before writing `page.html` the
crawler runs three steps:

1. `make_assets_absolute()` — relative CSS/image/font URLs become absolute CDN URLs
2. `remove_base_tag()` — drops `<base>` so absolute asset URLs resolve correctly
3. `strip_scripts()` — removes all `<script>`, module/script preloads, and inline
   `on*` event handlers

The result _looks_ like production (styling, fonts, images, layout, and any
captured modal/dropdown all render) but does **not** behave like production —
no JavaScript runs, so there are no API calls, websocket connections, or
"can't connect to server" errors. CSS, images, fonts, and SVG are always kept.

```
page_slug/
  page.html          DOM snapshot; asset URLs absolutized to original CDN
  screenshot.png     Full-page screenshot
  metadata.json      URL, title, timestamp, page type
  interactions/
    discovered.json  All clickable elements found on the page
    interactions.json Registry of saved interaction captures
    001-new-item/
      page.html
      screenshot.png
      metadata.json
      relationship.json
```

---

## Setup

### 1. Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chrome
```

### 3. Chrome

Playwright uses the system Chrome channel on macOS. Install Google Chrome at:

```
/Applications/Google Chrome.app
```

On Linux:

```bash
playwright install-deps chrome
```

---

## Commands

Every command requires an app name (configured in `config.py`).

| Command                               | Description                                                           |
| ------------------------------------- | --------------------------------------------------------------------- |
| `python main.py crawl <app>`          | Pre-auth + post-auth crawl                                            |
| `python main.py crawl-preauth <app>`  | Marketing / public pages only                                         |
| `python main.py crawl-postauth <app>` | Authenticated app pages only                                          |
| `python main.py stitch <app>`         | Build a navigable static clone from crawl output                      |
| `python main.py serve <app>`          | Serve the stitched clone locally (`--port N`, `--watch`, `--no-open`) |
| `python main.py status <app>`         | Pages crawled, interactions, storage size                             |
| `python main.py clean <app>`          | Delete all crawl output for the app                                   |

### Examples

```bash
python main.py crawl zoho
python main.py crawl-preauth zoho
python main.py crawl-postauth zoho
python main.py reconcile zoho
python main.py stitch zoho
python main.py serve zoho                # http://localhost:8000
python main.py serve zoho --port 9000 --watch
python main.py status zoho
python main.py clean zoho
```

End-to-end: **`crawl` → `reconcile` → `stitch` → `serve`**.

Help:

```bash
python main.py --help
```

---

## Crawl flow

```
queue = [start_page]

while queue and pages < max:
    visit page
    save page.html + screenshot.png + metadata.json
    discover same-origin links → add to queue (BFS)
    discover interactions → click each → save if DOM changed
```

- **BFS owns pages** — same-origin `a[href]` links drive page discovery and the queue
- **Interactions own UI states** — discovery is limited to non-anchor triggers (`button`, `[aria-haspopup]`, `[role="button"]`, `input[type="submit"]`, `input[type="button"]`). Anchors are never clicked here; they're already handled by BFS, so there's no duplicate crawling.
- Interaction triggers are ranked by priority (button → aria-haspopup → role=button → submit/button inputs) and capped at `max_interactions_per_page` (default `10`)
- **Interaction captures** are saved as child folders; they never enter the BFS queue

### Network policy

During crawl, **all network traffic is allowed** — HTML, CSS, JS, images, fonts, fetch, xhr, and websocket — so the page loads and behaves exactly as users see it while being captured. JavaScript is stripped only from the **saved** `page.html` (via `strip_scripts()`), turning each capture into a static snapshot. The live page is fully scripted during the crawl; the saved file is not.

### Interaction types

Each interaction capture is a **UI state** (no page navigation) classified as one of:

`modal` · `drawer` · `sidebar` · `dropdown` · `popover` · `tooltip` · `overlay` · `unknown`

An interaction is saved **only if** the URL did not change **and** the DOM changed. If a click navigates to a new URL, no interaction is saved — instead the edge is recorded in the page's `navigations.json` (so non-anchor triggers become clickable in the clone) and the destination is queued for BFS to crawl.

---

## Storage layout

```
storage/apps/
└── zoho/
    ├── metadata/
    │   ├── auth.json
    │   └── sitemap.json
    └── crawl/
        ├── in-books/
        │   ├── page.html
        │   ├── screenshot.png
        │   ├── metadata.json
        │   ├── navigations.json          non-anchor nav edges (div/li/role=menuitem → page)
        │   └── interactions/
        │       ├── discovered.json
        │       ├── interactions.json
        │       └── 001-pricing/
        │           ├── page.html
        │           ├── screenshot.png
        │           ├── metadata.json
        │           ├── relationship.json
        │           └── reconciliation.json   (added by `reconcile`: trigger + ui_html + backdrop_html)
        └── app-home-dashboard/
            ├── page.html
            ├── screenshot.png
            └── metadata.json
```

---

## Reconciliation (`reconcile`)

`python main.py reconcile <app>` diffs each main page DOM against its
interaction page DOM and extracts **only the UI the click introduced** (modal /
dropdown / sidebar / drawer / popover / tooltip / overlay / backdrop). It is
deterministic — pure BeautifulSoup tree diffing, **no LLM**.

It writes exactly **one file per interaction** — no delta directory, no reports,
no debug artifacts:

```
interactions/002-show-dropdown-menu/reconciliation.json
```

That single file contains everything the stitcher needs:

```json
{
  "trigger": {
    "label": "Show dropdown menu",
    "tagName": "button",
    "id": "",
    "className": "dropdown-toggle no-caret",
    "selector": "[data-crawl-id=\"2\"]",
    "outerHTML": "<button …>…</button>"
  },
  "interaction_type": "dropdown",
  "location": {
    "parentSelector": "#tooltip-popover-wrapper",
    "parentXPath": "/html[1]/body[1]/div[6]/div[1]",
    "insertMethod": "append"
  },
  "ui_html": "<div class=\"dropdown-menu show\">…</div>",
  "backdrop_html": ""
}
```

- **`trigger`** — the element that was clicked, taken from `relationship.json`:
  `label`, `tagName`, `id`, `className`, `selector`, and the **full `outerHTML`**.
- **`interaction_type`** — `modal` / `dropdown` / `sidebar` / `drawer` /
  `popover` / `tooltip` / `overlay` / `unknown`, inferred from the added DOM's
  class tokens and roles.
- **`location`** — where to inject: parent CSS `parentSelector`, `parentXPath`,
  and `insertMethod` (`append` or `insert`).
- **`ui_html`** — the newly introduced panel/menu/dialog, classes and attributes
  preserved exactly.
- **`backdrop_html`** — any scrim/overlay sibling, separated out from the UI.

**How the diff works** — both DOMs are matched child-by-child using a
_structural signature_ (tag + classes + role + type) that ignores volatile
attributes (regenerated `id`s, `aria-controls`, etc.). Unmatched interaction
subtrees are the additions; the added roots are split into `ui_html` and
`backdrop_html`. This compares real DOM structure, not text.

The stitcher can operate using **only** `page.html`, `relationship.json`, and
`reconciliation.json` — nothing else.

---

## Stitcher (`stitch`)

`python main.py stitch <app>` turns the raw crawl output into a **navigable
static clone** under `storage/apps/<app>/stitched/`. It does these things and
nothing else — no DOM diffing, no reconciliation, no overlay reconstruction:

1. **Page navigation** — every `<a href="#/route">` (including ones hidden
   inside collapsed sidebar menus) is rewritten to the local page it maps to
   (`../<slug>/page.html`). Routes are resolved from each crawled page's own
   `metadata.json` url (the sitemap is merged in as aliases), so any crawled
   page is linkable even if the sitemap is incomplete. Routes that were never
   crawled, and any absolute production URL, are neutralized to `#` so
   navigation can never escape the clone. Asset links keep their CDN URLs.
2. **Sidebar accordions** — collapsible in-page menus (Bootstrap-style
   `accordion-button` / `accordion-title`, or any element whose `aria-controls`
   / `aria-expanded` toggles an in-page panel) are wired with
   `data-stitch-accordion`. The runtime expands/collapses the panel client-side
   (toggles `aria-expanded`, the `hidden` attribute, the `show`/`collapsed`
   classes). These are **never** treated as interactions and **never** load a
   snapshot — the submenu already lives in the same page. With
   `--expand-sidebars` (the default) every menu is expanded at stitch time so
   all nested links are immediately visible; pass `--no-expand-sidebars` to keep
   them collapsed and rely on the runtime toggle.
3. **Interaction UI injection** — each trigger is matched (by stable attributes
   from `relationship.json`) and tagged with `data-stitch-ui-id`. Clicking it
   **injects the reconciled `ui_html`** (from `reconciliation.json`) into the
   current page — **no reload** — at `location.parentSelector` using
   `insertMethod` (`append` → `beforeend`, `insert`/`prepend` → `afterbegin`,
   `replace` → `innerHTML`). The injected content is wrapped in
   `.stitch-injected-ui` and the captured snapshot is used only as a **fallback**
   (see below). See "Interaction injection" for the manifest and close behavior.
4. **Non-anchor navigation** — modern SaaS apps navigate from `div` / `li` /
   `span` / `[role=menuitem]` / `button` / custom components, not just `<a>`.
   During the crawl, any click that changes the URL is recorded as a navigation
   edge in `navigations.json` (label + full trigger metadata + target slug) and
   its destination is fed back into BFS. The stitcher matches those triggers
   (same attribute scoring) and tags them with `data-stitch-go` → the local
   target page, so they become clickable even though they aren't anchors. This
   is generic — it works for any app, driven entirely by crawl data.
5. **Interaction-state cleanup** — pages are often crawled mid-load while the
   app is temporarily frozen (e.g. `<nav id="main-nav-tab" style="pointer-events:none">`),
   which would leave sidebar links and accordion buttons permanently dead in the
   clone. A final pass over the whole document strips `pointer-events:none` /
   `user-select:none` from inline styles, removes `disabled` and
   `aria-disabled="true"` from `a`/`button`/`input`/`select`/`textarea`, and
   injects a `<style id="stitch-interaction-fixes">` override forcing
   `pointer-events:auto` on the nav containers. The stitch log reports how many
   `pointer-events:none` declarations and disabled controls were restored.

**Accordion vs. interaction** is decided generically, with no app-specific
selectors: a toggle whose `aria-controls` target (or sibling panel) exists *in
the same page* is an accordion (toggle in-place); a trigger whose content is
created on click — dropdown, modal, popover, drawer overlay — has no in-page
target, so it keeps its captured snapshot.

A tiny `runtime.js` is injected into every page to toggle accordions, inject
interaction UI, handle non-anchor navigation, and block any leftover production
link. A `navigation.json` manifest maps each page to its local page links and
interaction states.

```
storage/apps/zoho/stitched/
├── runtime.js
├── navigation.json
├── app-60073668069-home/
│   ├── page.html                 anchors localized, triggers tagged, runtime + config injected
│   └── interactions/
│       └── 002-show-dropdown-menu/
│           └── page.html         full interaction snapshot (fallback only)
└── app-60073668069-inventory-product-index/
    └── page.html
```

### Interaction injection

Instead of navigating to a snapshot, each page embeds an interaction manifest:

```html
<script>window.__STITCH_INTERACTIONS__ = {
  "interaction_15": {
    "type": "overlay",
    "parentSelector": "#flyout-with-topbar",
    "parentXPath": "/html[1]/body[1]/div[6]/div[5]",
    "insertMethod": "append",
    "uiHtml": "<div class=\"slide-sidebar-left\">…</div>",
    "backdropHtml": "",
    "fallback": "interactions/024-testing/page.html"
  }
};</script>
```

On click, the runtime looks up the trigger's `data-stitch-ui-id`, finds
`parentSelector`, injects `backdropHtml` then `uiHtml` inside a
`.stitch-injected-ui` wrapper, and leaves the current page loaded. A second
click on the same trigger closes it (toggle).

**Generic close behavior** (no app-specific code):
- **click outside** the injected UI (and not on the trigger) removes it;
- **ESC** removes it;
- close affordances inside the UI are auto-bound: `.close`, `.sidebar-close`,
  `.modal-close`, `[data-dismiss]`, `[data-bs-dismiss]`, `[aria-label*=close]`,
  and any backdrop/overlay-mask element.

**Fallback** — if `uiHtml` is empty, `parentSelector` isn't found, or injection
throws, the runtime navigates to the captured snapshot
(`interactions/NNN-.../page.html`) instead. Those snapshot pages are still
stitched and copied for exactly this purpose.

The runtime also logs `[STITCH] Accordion Toggle <panelId>` and `[STITCH]
Sidebar Link <href>` (and flags unresolved sidebar routes) to help diagnose
navigation that doesn't resolve to a crawled page.

Open `stitched/<slug>/page.html` and click around: links load other local
pages, sidebar accordions expand/collapse in place, and interaction triggers
inject their reconciled UI on top of the current page. Everything runs locally
with no production navigation, APIs, or JavaScript execution.

> V1 scope: navigation + in-page accordions + reconciled UI injection with
> generic close behaviour (outside click, ESC, close buttons, backdrop). Browser
> history for injected overlays is intentionally not handled yet.

---

## Local server (`serve`)

`python main.py serve <app>` serves the stitched clone over HTTP so the whole
thing behaves like a real local app — no `file://` URLs, no manual opening of
HTML files. Implemented with the stdlib `http.server` (no extra deps) in
`src/runtime/server.py`.

```bash
python main.py serve zoho                 # → http://localhost:8000
python main.py serve zoho --port 9000     # custom port
python main.py serve zoho --watch         # auto-reload tabs on file changes
python main.py serve zoho --no-open       # don't auto-open the browser
```

- **Routing** — `/` redirects to the entry page (the page whose title contains
  "Dashboard", else the first crawled page). All other paths are served as
  static files from `storage/apps/<app>/stitched/`.
- **404** — a missing page returns the styled `404.html` ("Missing stitched
  page") with a real 404 status, never a raw browser error.
- **No caching** — responses are sent `no-store` so edits show immediately.
- **`--watch`** — injects a 1s live-reload poller into served HTML and exposes
  `/__stitch_version`; when any stitched file changes, open tabs reload.

Everything stays on `localhost`: anchors load other local pages, interaction
triggers load their captured UI-state snapshots, and the injected `runtime.js`
blocks any leftover production link. No Zoho navigation, no production APIs.

### Page metadata

```json
{
  "url": "https://books.zoho.in/app/...#/home/dashboard",
  "title": "Dashboard | Zoho Books",
  "captured_at": "2026-06-10T12:00:00+00:00",
  "page_type": "post_auth"
}
```

`page_type` is `pre_auth` or `post_auth`.

### Interaction metadata

Each interaction folder includes `metadata.json` and `relationship.json`:

```json
{
  "source_page": "app-home-dashboard",
  "source_url": "https://books.zoho.in/...",
  "trigger_label": "New Item",
  "trigger_id": "",
  "trigger_class": "btn btn-primary",
  "target_url": "https://books.zoho.in/...",
  "target_slug": "app-items-new",
  "target_title": "New Item | Zoho Books",
  "interaction_type": "modal"
}
```

Each page also has `interactions/interactions.json` — a registry of all saved interaction captures for stitching.

---

## Authentication

Auth is stored per app:

```
storage/apps/zoho/metadata/auth.json
```

### First post-auth crawl

1. No `auth.json` exists → Chrome opens for manual login
2. Log in in the browser window
3. Press **Enter** in the terminal
4. Session is saved to `auth.json`

### Subsequent runs

Auth is reused automatically — login is skipped.

### Force re-login

```bash
rm storage/apps/zoho/metadata/auth.json
python main.py crawl-postauth zoho
```

---

## Adding a new app

Edit `config.py`:

```python
APPS = {
    "zoho": {
        "pre_auth_home": "https://www.zoho.com/in/books/",
        "login_url": "https://accounts.zoho.com/signin?...",
        "post_auth_home": "https://books.zoho.in",
        "max_pages_pre_auth": 5,
        "max_pages_post_auth": 20,
    },
    "hubspot": {
        "pre_auth_home": "https://www.hubspot.com/",
        "login_url": "https://app.hubspot.com/login",
        "post_auth_home": "https://app.hubspot.com",
        "max_pages_pre_auth": 5,
        "max_pages_post_auth": 20,
    },
}
```

Then crawl:

```bash
python main.py crawl hubspot
```

Output is written to `storage/apps/hubspot/crawl/`.

---

## Project structure

```
spider-python/
├── main.py                 CLI entrypoint
├── crawler_v2.py           BFS crawler + interaction capture
├── crawler_scripts.json    Browser-side discovery/classification scripts
├── config.py               Per-app crawl settings
├── storage/
│   └── storage_manager.py  Path helpers
└── requirements.txt
```

---

## Experiments

`experiments/` contains the original prototype. Do not modify it.
