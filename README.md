# Spider Python

Spider Python is a web-crawling and page-analysis project built with Python, Playwright, and Gemini. It targets **Zoho Books** — an authenticated, Ember.js single-page application — crawls its internal pages, stitches them into a navigable offline site, analyzes page structure with an LLM, and generates visual HTML replicas from screenshots.

## What it does

The full pipeline:

1. Authenticates with Zoho Books using a saved browser session (`auth.json`).
2. Crawls up to `MAX_PAGES` internal SPA routes using sidebar navigation and hash routing.
3. Saves HTML, visible text, full-page screenshots, and localized assets for each page.
4. Stitches all crawled pages into a navigable offline site with working sidebar links.
5. Analyzes pages with Gemini using screenshots (structured JSON output).
6. Generates self-contained HTML replicas that visually match the screenshots.

## Features

- Authenticated Playwright crawl of a Zoho Books workspace (no credentials stored — manual login on first run).
- SPA-aware navigation: handles hash-based routes (`#/disputes`, `#/customers`, etc.), sidebar accordion expansion, and Ember routing fallbacks.
- Full-page screenshot, raw HTML, visible text, and `.meta` URL capture per page.
- Asset localization: saves content images to `assets/images/`, CSS to `assets/css/`, and Zoho JS to `assets/js/`.
- `page_stitch.py`: post-processes all pages — strips live scripts, rewrites routes to local `.html` files, expands sidebar nav, and injects a static accordion toggle for offline use. Generates `pages/index.html` as a landing page.
- Gemini-powered page analysis (screenshot → structured JSON via Pydantic).
- Visual HTML replica generation from screenshots (Tailwind CDN, inline CSS).
- Skip logic — re-running analysis or replica generation skips already-processed pages.

## Project Structure

- `crawl_authenticated_pages.py` — **Primary crawler.** SPA-aware, handles Zoho Books authentication, hash routing, and sidebar navigation. Calls `page_stitch.py` automatically on completion.
- `crawler.py` — Simpler BFS crawler (used for non-SPA or general crawling).
- `page_stitch.py` — Post-processes crawled HTML into a navigable offline site. Strips scripts, rewrites internal links, expands sidebar, and generates `pages/index.html`.
- `replica_generator.py` — Generates visual HTML replicas from screenshots into `replicas/`.
- `processors/analyze_page.py` — Screenshot-only page analyzer via `gemini_service`.
- `processors/analyse_all_pages.py` — Analyzes all saved pages (text + screenshot) via LangChain; writes JSON to `analysis/`.
- `services/gemini_service.py` — Gemini client for screenshot analysis and HTML replica generation.
- `models/page_analysis.py` — Pydantic schema for structured analysis output.
- `pages/` — Saved page artifacts (HTML, text, screenshots, `.meta` URL files, `sitemap.json`).
- `assets/` — Localized images (`assets/images/`), CSS (`assets/css/`), and JS (`assets/js/`).
- `analysis/` — Saved analysis JSON files.
- `replicas/` — Generated HTML replica files.
- `auth.json` — Playwright browser storage state (created on first run, gitignored).

## Requirements

- Python 3.10 or newer.
- A valid `GEMINI_API_KEY` in your environment or `.env` file.
- Playwright browser binaries installed locally.
- Google Chrome installed at `/Applications/Google Chrome.app` (macOS) — required for the first-run login flow.
- An active Zoho Books account.

## Installation

Clone the repository and create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the Playwright browser runtime:

```bash
playwright install
```

Set your Gemini API key in a `.env` file at the project root:

```
GEMINI_API_KEY=your_api_key_here
```

## How to Run

Run these in order from the project root with your venv activated.

### 1. Crawl Zoho Books

On the **first run**, if no `auth.json` is present, Chrome will open for you to log in manually. Once you press Enter, the session is saved to `auth.json` and reused for all future runs.

```bash
python crawl_authenticated_pages.py
```

This crawls up to `MAX_PAGES` (default: 10) Zoho Books routes, saves artifacts to `pages/` and assets to `assets/`, then automatically runs `page_stitch.py` to produce a navigable offline site.

> **Preview offline:** `python3 -m http.server 8080` → open `http://localhost:8080/pages/home.html`

### 2. (Optional) Re-stitch pages

If you want to re-run the stitching step independently (e.g. after editing `page_stitch.py`):

```bash
python page_stitch.py
```

Requires `pages/sitemap.json` to exist — run the crawler first.

### 3. Analyze crawled pages

**Screenshot-only (Gemini direct):**

```bash
python processors/analyze_page.py
```

**Text + screenshot (LangChain):**

```bash
python -m processors.analyse_all_pages
```

Both write structured JSON to `analysis/`. Already-analyzed pages are skipped.

### 4. Generate HTML replicas

Reads every `pages/*.png` screenshot, sends it to Gemini, and writes a self-contained visual replica to `replicas/`. Pages that already have a replica are skipped.

```bash
python replica_generator.py
```

> Replica generation calls Gemini once per page and can take several minutes for large screenshots.

## Output Files

After a full run you will see:

**`pages/`**
- `disputes.html`, `customers.html`, etc. — stitched offline HTML (slug-named by URL fragment)
- `disputes.png` — full-page screenshot
- `disputes.txt` — visible body text
- `disputes.meta` — original Zoho Books URL
- `disputes.images.json` — index of captured content images
- `sitemap.json` — ordered list of all crawled pages
- `index.html` — offline navigation index

**`assets/`**
- `images/` — localized content images
- `css/` — localized stylesheets
- `js/` — localized Zoho/ZohoStatic scripts

**`analysis/`**
- `disputes.json` — structured Gemini analysis

**`replicas/`**
- `disputes.html` — generated visual replica

## Authentication

On the first run, `crawl_authenticated_pages.py` launches a real Chrome window with remote debugging enabled and navigates to the Zoho Books login page. Log in manually, wait for the dashboard to load, then press Enter in the terminal. The session is saved to `auth.json` and reused automatically on all subsequent runs.

To force a fresh login, delete `auth.json` and run the crawler again.

## Environment Variables

| Variable | Description |
| --- | --- |
| `GEMINI_API_KEY` | API key used to authenticate with Gemini. |

## Configuration

Edit these directly in the scripts:

| Setting | File | Default |
| --- | --- | --- |
| Start URL | `crawl_authenticated_pages.py` | `https://books.zoho.in` |
| Max pages to crawl | `crawl_authenticated_pages.py` | `10` |
| Gemini model | `services/gemini_service.py` | `gemini-2.5-flash` |
| Chrome path | `crawl_authenticated_pages.py` | `/Applications/Google Chrome.app/...` |
| Auth file name | `crawl_authenticated_pages.py` | `auth.json` |

## Example Analysis Schema

The structured Gemini output follows the `PageAnalysis` model:

- `pageType`
- `purpose`
- `mainCTA`
- `importantSections`
- `summary`

## License

No license file is currently included in this repository.
