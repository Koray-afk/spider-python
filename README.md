# SaaS Crawler

Simple Playwright crawler for authenticated SaaS apps. Saves high-fidelity HTML snapshots using local SingleFile Core (`engine/`) or static HTML capture.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Build SingleFile bundles (one-time)

SingleFile Core is ES-module source. Bundle it for browser injection:

```bash
bash scripts/build_singlefile.sh
```

This creates:

- `engine/dist/hook.bundle.js` — iframe hooks
- `engine/dist/singlefile.bundle.js` — main capture library

Requires Node.js (uses `npx esbuild`).

## Usage

```bash
python main.py --app-name hubspot
python stitch.py --app-name hubspot
open site/hubspot/index.html
python3 serve.py --app-name zoho
rm -rf ~/.saas_crawler_chrome_profile
```

Optional headed crawl:

```bash
python main.py --app-name hubspot --headed
```

## Manual login flow

Login uses a **real Chrome process** started via `subprocess` — Playwright never
launches the browser for authentication. Playwright attaches over CDP only after
Chrome is running.

1. Chrome starts with profile at `~/.saas_crawler_chrome_profile` (the real auth source).
2. Playwright attaches via `connect_over_cdp`.
3. Crawler opens `post_auth_home` and validates the session (login redirect, password field, etc.).
4. If invalid: deletes `auth/<app>.json` backup (if present) and prompts manual login.
5. After login, session lives in the Chrome profile; `auth/<app>.json` is saved as optional backup only.
6. Crawling reuses the same profile via CDP — never `storage_state`.

Requires Google Chrome at `CHROME_MAC_PATH` in `config.py`.

## Output folder structure

```
storage/
└── hubspot/
    └── crawl/
        └── dashboard/
            ├── page.html
            ├── screenshot.png
            ├── metadata.json
            └── accessibility-tree.json

site/
└── hubspot/
    ├── index.html
    └── pages/
        └── dashboard/
            └── index.html
```

## How capture works

URL-only BFS from `post_auth_home`:

1. Visit URL
2. Wait for `domcontentloaded`, then an extra 2 seconds
3. Capture `page.html`, `screenshot.png`, `metadata.json`, `accessibility-tree.json` (each node includes optional `_debug` DOM metadata when mappable)
4. Discover same-host `a[href]` links
5. Normalize URLs, dedupe, enqueue unseen URLs

No button clicks. No interaction states. No DOM mutation exploration.

HTML capture strategy per app config:

- `use_singlefile=True` → `capture_html()`
- `use_singlefile=False` → `static_snapshot_html()`

## Stitching and offline server

```bash
python stitch.py --app-name zoho
python serve.py --app-name zoho
open http://127.0.0.1:8765/
```

`serve.py` will:

1. Stitch captured pages into `site/<app>/`
2. Copy API mocks into `site/<app>/_mocks/`
3. Inject a mock bridge into each page (maps captured API calls for that page)
4. Serve pages + mock API responses on one local port

Each crawled page stores `api-manifest.json` listing the API responses captured during that visit. The global `storage/apps/<app>/mock_registry.json` maps endpoints to mock files and page slugs.

During crawl, mocks are saved to:

```
storage/apps/zoho/mock_api/
storage/zoho/crawl/<page-slug>/api-manifest.json
storage/zoho/crawl/<page-slug>/api/
```

## Configuration

Edit `config.py` to add or change apps:

```python
APPS = {
    "hubspot": {
        "login_url": "https://app.hubspot.com/login",
        "post_auth_home": "https://app.hubspot.com/contacts",
    },
}
```

## Notes

- **Auth source**: `USER_DATA_DIR` Chrome profile (cookies, localStorage, IndexedDB, OAuth state).
- **auth/*.json**: optional backup export only — not used for crawling.
- **Crawl**: same Chrome profile via CDP (headless with `--headless=new` by default; use `--headed` if a site rejects headless sessions).
- Skips URLs containing: logout, signout, privacy, terms, support, help, documentation, docs.
