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

### 5. Set Gemini API key

Create `.env` in the project root:

```
GEMINI_API_KEY=your_key_here
```

Required for the analyze step (`python main.py analyze <app>`).

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
| `python main.py pipeline <app>` | Full pipeline: crawl → stitch → clean → analyze |
| `python main.py crawl <app>` | Crawl only → `raw_html/` |
| `python main.py stitch <app>` | Stitch only → `stitched_html/` |
| `python main.py clean <app>` | Clean only → `cleaned_html/` |
| `python main.py analyze <app>` | Analyze only → `business_json/` |
| `python main.py preview <app>` | Serve `stitched_html/` locally |
| `python main.py serve` | Start FastAPI API on port 8000 |

### Examples

```bash
python main.py pipeline zoho
python main.py crawl zoho
python main.py stitch zoho
python main.py clean zoho
python main.py analyze zoho
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
│   ├── business_json/     # Page-level business JSON from Agent 1
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
| `business_json/` | Analyzer (Agent 1) | Evidence-backed business JSON per page |
| `metadata/` | Crawler / pipeline | Sitemap, auth, pipeline status |

---

## Business analysis (Agent 1)

Reads `cleaned_html/`, writes one JSON per page to `business_json/`:

```bash
python main.py analyze zoho
```

Example:

```
cleaned_html/inventory.html  →  business_json/inventory.json
```

Flow per page:

1. **Deterministic extraction** — title, headings, buttons, links, forms, tables (PageFacts)
2. **Gemini 2.5 Pro** — receives PageFacts + truncated HTML snippet (not full HTML blindly)
3. **Validation** — compares extracted vs reported element counts; retries once on mismatch
4. **Save** — structured JSON with evidence on every conclusion

Requires `GEMINI_API_KEY` in `.env`.

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
[1/4] Crawl    → storage/apps/{app}/raw_html/
[2/4] Stitch   → storage/apps/{app}/stitched_html/   (auto after crawl in pipeline)
[3/4] Clean    → storage/apps/{app}/cleaned_html/
[4/4] Analyze  → storage/apps/{app}/business_json/
```

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

`experiments/` contains the original prototype. Do not modify it. Production code lives in `crawler/`, `stitcher/`, `analyzer/`, and `pipeline.py`.
