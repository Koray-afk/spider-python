# Spider Python

Offline, high-fidelity static replicas of SaaS applications for design reference. Crawl pages with Playwright, stitch navigation between local HTML files, clean HTML for LLM analysis.

Each application is isolated under `storage/apps/{app_name}/`.

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install chrome
```

### 4. Install Chrome (if not already present)

Playwright uses the system Chrome channel on macOS. Ensure Google Chrome is installed at:

```
/Applications/Google Chrome.app
```

On Linux, install Chromium/Chrome dependencies:

```bash
playwright install-deps chrome
```

### 5. (Optional) Gemini API key for analysis stages

Create a `.env` file at the project root if you want to run `analyze`, `semantic_tree`, `component_tree`, `catalog`, or `workflows`:

```
GEMINI_API_KEY=your_api_key_here
```

### 6. First run

```bash
python main.py pipeline zoho
```

Post-auth crawl opens Chrome for manual login on the first run. Press Enter in the terminal after logging in.

---

## Commands

Every command requires an app name (`zoho`, `hubspot`, etc.).

| Command | Description |
|---------|-------------|
| `python main.py pipeline <app>` | Full pipeline: crawl → stitch → clean |
| `python main.py crawl <app>` | Crawl only → `raw_html/` |
| `python main.py stitch <app>` | Stitch only → `stitched_html/` |
| `python main.py clean <app>` | Clean only → `cleaned_html/` |
| `python main.py analyze <app>` | Analyze only → `business_json/` (requires `GEMINI_API_KEY`) |
| `python main.py semantic_tree <app>` | Semantic UI tree → `semantic_tree/` (requires `GEMINI_API_KEY`) |
| `python main.py component_tree <app>` | React component tree → `component_tree/` (requires `GEMINI_API_KEY`) |
| `python main.py catalog <app>` | Application catalog → `app_catalog/catalog.json` (requires `GEMINI_API_KEY`) |
| `python main.py workflows <app>` | Business workflows → `app_catalog/workflows.json` (requires `GEMINI_API_KEY`) |
| `python main.py preview <app>` | Serve `stitched_html/` locally |
| `python main.py serve` | Start FastAPI API on port 8000 |

### Examples

```bash
python main.py pipeline zoho
python main.py crawl zoho
python main.py stitch zoho
python main.py clean zoho
python main.py analyze zoho
python main.py semantic_tree zoho
python main.py component_tree zoho
python main.py catalog zoho
python main.py workflows zoho
python main.py preview zoho
```

Future apps:

```bash
python main.py pipeline hubspot
python main.py preview hubspot
```

---

## Preview

After stitching, preview the offline replica:

```bash
python main.py preview zoho
```

This serves **only** that app's stitched HTML:

```
storage/apps/zoho/stitched_html
```

Open (post-auth dashboard example):

```
http://localhost:8080/app-60073668069-home-dashboard/index.html
```

Pre-auth marketing example:

```
http://localhost:8080/in-books/index.html
```

**Manual equivalent:**

```bash
cd storage/apps/zoho/stitched_html
python3 -m http.server 8080
```

Then open `http://localhost:8080/<slug>/index.html`.

> Do not open `file://` URLs. Always use a local HTTP server.  
> Do not preview from `raw_html/` — use `stitched_html/` only.

Each app's preview is independent. Previewing `hubspot` does not affect `zoho`.

---

## Storage structure

```
storage/apps/
├── zoho/
│   ├── raw_html/          # Crawled HTML (with live JS on pre-auth pages)
│   ├── screenshots/       # Full-page PNG per slug
│   ├── assets/            # Downloaded assets (reserved)
│   ├── stitched_html/     # Offline-viewable stitched pages ← preview here
│   ├── cleaned_html/      # Flat simplified HTML for LLM analysis
│   ├── business_json/     # Gemini business analysis JSON per page
│   ├── semantic_tree/     # Semantic UI component tree JSON per page
│   ├── component_tree/    # High-level React component tree JSON per page
│   ├── app_catalog/       # Global application map (single catalog.json)
│   └── metadata/
│       ├── sitemap.json
│       ├── auth.json
│       ├── session.json
│       └── pipeline_status.json
├── hubspot/
└── salesforce/
```

| Directory | Written by | Purpose |
|-----------|------------|---------|
| `raw_html/` | Crawler | Original captured HTML |
| `stitched_html/` | Stitcher | Sidebar nav wired, JS stripped (post-auth) |
| `cleaned_html/` | Cleaner | Token-efficient HTML for LLMs |
| `business_json/` | Analyzer | Per-page business analysis JSON from Gemini |
| `semantic_tree/` | Semantic tree analyzer | Hierarchical UI component tree with semantic IDs |
| `component_tree/` | Component tree analyzer | Compressed React-oriented component tree per page |
| `app_catalog/` | Catalog analyzer | Global app map: pages, modules, workflows, relationships |
| `metadata/` | Crawler / pipeline | Sitemap, auth, pipeline status |

---

## Authentication

Auth state is stored per app under `metadata/`:

```
storage/apps/zoho/metadata/auth.json
storage/apps/zoho/metadata/session.json
```

### How login works

1. First post-auth crawl with no cached auth opens Chrome for manual login.
2. After you log in and press Enter, Playwright saves `auth.json`.
3. Future runs reuse `auth.json` automatically — login is skipped.

### Reset auth (force re-login)

```bash
rm storage/apps/zoho/metadata/auth.json
```

Then run crawl or pipeline again.

Each app has its own auth files. Deleting Zoho's auth does not affect HubSpot.

---

## Adding a new app

Edit `config/apps.py`:

```python
APPS = {
    "zoho": { ... },
    "hubspot": {
        "pre_auth_home": "https://www.hubspot.com/",
        "login_url": "https://app.hubspot.com/login",
        "post_auth_home": "https://app.hubspot.com",
        "max_pages_pre_auth": 5,
        "max_pages_post_auth": 20,
    },
}
```

Then run:

```bash
python main.py pipeline hubspot
python main.py preview hubspot
```

Storage is created automatically at `storage/apps/hubspot/`.

---

## Pipeline stages

```
[1/3] Crawl    → storage/apps/{app}/raw_html/
[2/3] Stitch   → storage/apps/{app}/stitched_html/   (auto after crawl in pipeline)
[3/3] Clean    → storage/apps/{app}/cleaned_html/
[4/7] Analyze        → storage/apps/{app}/business_json/        (optional, run separately)
[5/7] Semantic tree  → storage/apps/{app}/semantic_tree/        (optional, run separately)
[6/7] Component tree → storage/apps/{app}/component_tree/       (optional, run separately)
[7/8] Catalog        → storage/apps/{app}/app_catalog/          (optional, run separately)
[8/8] Workflows      → storage/apps/{app}/app_catalog/          (optional, run separately)
```

Run analyze after clean:

```bash
python main.py analyze zoho
```

Output example:

```
storage/apps/zoho/business_json/contacts.json
storage/apps/zoho/business_json/invoices.json
```

Each JSON file includes `businessPurpose`, `mainActions`, `businessEntities`, `userRoles`, and `shortSummary`. Already-analyzed pages are skipped on re-run.

Run semantic tree after clean (and optionally after analyze for better context):

```bash
python main.py semantic_tree zoho
```

Output example:

```
storage/apps/zoho/semantic_tree/contacts.json
storage/apps/zoho/semantic_tree/creditnotes.json
```

Each JSON file is a hierarchical component tree with `pageId`, `type`, `id`, `label`, and `children`. Pages without `business_json` still run (empty context). Already-built trees are skipped on re-run.

Run component tree after semantic tree:

```bash
python main.py component_tree zoho
```

Output example:

```
storage/apps/zoho/component_tree/quotes.json
storage/apps/zoho/component_tree/invoices.json
```

Each JSON file compresses the detailed semantic tree into tens of high-level React components with `pageId`, `components[].id`, `type`, `purpose`, and `children`. Requires `semantic_tree/`. Already-built trees are skipped on re-run. Can run before or after `catalog`.

Run catalog after semantic tree (and optionally after analyze for richer page context):

```bash
python main.py catalog zoho
```

Output:

```
storage/apps/zoho/app_catalog/catalog.json
```

The catalog is a single JSON file with `pages`, `modules`, `relationships`, `sharedEntities`, and `workflows` — an application-level map for browser and React generator agents. Requires `semantic_tree/`; `business_json/` is optional per page. Re-run skips if `catalog.json` already exists.

Run workflows after catalog:

```bash
python main.py workflows zoho
```

Output:

```
storage/apps/zoho/app_catalog/workflows.json
```

A JSON array of rich ERP business workflows — each with `id`, `name`, `purpose`, `entities`, `entryPage`, `exitPage`, and ordered `steps` (page + action + nextPage). Requires `catalog.json`; `business_json/` is optional. Re-run skips if `workflows.json` already exists.

Check progress:

```
storage/apps/{app}/metadata/pipeline_status.json
```

---

## API (optional)

```bash
python main.py serve
```

FastAPI runs on `http://localhost:8000`. See `api/routes.py` for endpoints.

---

## Experiments folder

`experiments/` contains the original prototype (crawler, page analysis, HTML replica generation). Do not modify it. Production code lives in `crawler/`, `stitcher/`, `analyzer/`, and `pipeline.py`.
