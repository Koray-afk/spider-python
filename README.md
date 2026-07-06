# Spider Python

**What is this?**

Imagine you have a website (like Zoho Books or another app). Spider Python visits that website, takes pictures of every page, saves what everything looks like, and then builds a **copy you can open on your computer** — even when you're offline.

Think of it like making a **photo album of a whole app** that you can click through at home.

---

## The 4 steps (in order)

Do these one at a time, like levels in a game:

| Step | Command | What it does (simple) |
|------|---------|------------------------|
| 1. **Crawl** | `python main.py crawl zoho` | Go to the website and save pages + screenshots |
| 2. **Reconcile** | `python main.py reconcile zoho` | Figure out what changed when you clicked a button |
| 3. **Stitch** | `python main.py stitch zoho` | Glue everything together so links and buttons work |
| 4. **Serve** | `python main.py serve zoho` | Open the copy in your browser at `http://localhost:8000` |

Replace `zoho` with your app name (the name you set in `config.py`).

**The full recipe:**

```bash
python main.py crawl zoho
python main.py reconcile zoho
python main.py stitch zoho
python main.py serve zoho
```

---

## What gets saved?

Each page becomes a folder with files inside:

```
page_slug/
  page.html          ← what the page looks like (saved as HTML)
  screenshot.png     ← a picture of the whole page
  metadata.json      ← info: URL, title, when it was saved
  interactions/      ← stuff that happens when you click buttons
    discovered.json
    interactions.json
    not_scraped.json
    001-new-item/
      page.html
      screenshot.png
      metadata.json
      relationship.json
```

**Important:** The saved pages **look** like the real website (colors, fonts, pictures) but they **don't talk to the real server**. No live data, no "can't connect" errors — just a frozen snapshot you can browse.

---

## Getting started

### Step 1: Make a virtual environment

This keeps this project's tools separate from other Python projects.

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install what you need

```bash
pip install -r requirements.txt
playwright install chrome
```

### Step 3: Install Chrome

Spider uses Google Chrome to visit websites.

- **Mac:** Install Chrome at `/Applications/Google Chrome.app`
- **Linux:** Run `playwright install-deps chrome`

### Step 4: (Optional) Add a Gemini API key

Some extra steps use AI (Google Gemini). If you want those, create a file named `.env` in the project folder:

```
GEMINI_API_KEY=your_api_key_here
```

Without this key, crawling and stitching still work. You just skip the AI analysis steps.

### Step 5: First run

```bash
python main.py crawl zoho
python main.py reconcile zoho
python main.py stitch zoho
python main.py serve zoho
```

**First time logging in:** Chrome will open. Log in to the app yourself, then go back to the terminal and press **Enter**. Your login is saved so you don't have to do it every time.

---

## All commands

Every command needs an app name (like `zoho`), except `api`.

| Command | What it does |
|---------|--------------|
| `python main.py crawl <app>` | Save public pages + logged-in pages |
| `python main.py crawl-preauth <app>` | Save only public pages (no login) |
| `python main.py crawl-postauth <app>` | Save only logged-in pages |
| `python main.py reconcile <app>` | Find what each click added to the page |
| `python main.py stitch <app>` | Build the clickable offline copy |
| `python main.py serve <app>` | Start a local website to view the copy |
| `python main.py status <app>` | Show how many pages were saved |
| `python main.py coverage <app>` | Find broken links and dead buttons |
| `python main.py clean <app>` | Delete saved data and start fresh |
| `python main.py preview <app>` | View an older style of stitched pages |
| `python main.py api` | Start a web API on port 8000 |

**Extra AI commands** (need `GEMINI_API_KEY` in `.env`):

| Command | What it does |
|---------|--------------|
| `python main.py html-clean <app>` | Clean up HTML for the AI to read |
| `python main.py analyze <app>` | AI describes what each page is for |
| `python main.py semantic_tree <app>` | AI builds a tree of UI parts |
| `python main.py component_tree <app>` | AI maps React-style components |
| `python main.py catalog <app>` | AI makes a catalog of the whole app |
| `python main.py workflows <app>` | AI finds business workflows |
| `python main.py modules <app>` | AI groups pages into modules |

**Examples:**

```bash
python main.py crawl zoho
python main.py serve zoho                  # opens http://localhost:8000
python main.py serve zoho --port 9000      # use a different port
python main.py serve zoho --watch          # auto-refresh when files change
python main.py status zoho
python main.py coverage zoho
python main.py clean zoho
python main.py html-clean zoho
python main.py analyze zoho
python main.py semantic_tree zoho
python main.py component_tree zoho
python main.py catalog zoho
python main.py workflows zoho
python main.py modules zoho
python main.py preview zoho
python main.py capture-interactions likwid --url https://likwidai.com/home/v2/
python main.py api
```

**Need help?**

```bash
python main.py --help
```

---

## How crawling works (simple version)

1. Spider opens Chrome and goes to the app.
2. It walks through the **sidebar menu** first (top to bottom), like reading a table of contents.
3. On each page it saves HTML, a screenshot, and info about the page.
4. It finds **clickable things** (buttons, tabs, menus) and clicks them to see what pops up.
5. It saves those pop-ups too (modals, dropdowns, drawers, etc.).
6. If you stop it, you can run crawl again — it picks up where it left off.

**What counts as an "interaction"?**

When you click something and **stay on the same page** but **something new appears** (a menu, a popup, a side panel) — that's an interaction.

When you click and **go to a new page** — that's normal navigation, not an interaction.

**Types of interactions:** modal, drawer, sidebar, dropdown, popover, tooltip, overlay, tab-switch

---

## Where files live

Everything goes under `storage/apps/`:

```
storage/apps/
└── zoho/                          ← your app name
    ├── metadata/                  ← login info, sitemap, progress
    ├── crawl/                     ← raw saved pages (from crawl)
    ├── stitched/                  ← the clickable copy (from stitch)
    ├── cleaned_html/              ← cleaned pages (for AI)
    ├── business_json/             ← AI analysis results
    └── app_catalog/               ← AI app map
```

| Folder | Who writes it | What's inside |
|--------|---------------|---------------|
| `crawl/` | Crawler | Raw page saves |
| `stitched/` | Stitcher | The offline app you can click through |
| `metadata/` | Crawler | Login, sitemap, checkpoints |
| `cleaned_html/` | html-clean | Simpler HTML for AI |
| `business_json/` | analyze | AI descriptions per page |

---

## What "reconcile" does

When you click "Show menu", the page changes a little. **Reconcile** compares:

- the page **before** the click
- the page **after** the click

…and saves **only the new part** (the menu, popup, etc.) in one file:

```
interactions/002-show-dropdown-menu/reconciliation.json
```

No AI needed — it's just comparing two saved pages.

---

## What "stitch" does

Stitch takes all the saved pages and makes them work together like a mini website:

1. **Links** — clicking a menu item opens the right saved page on your computer
2. **Sidebar menus** — expand and collapse when you click them
3. **Tabs** — switch tab content without reloading
4. **Buttons** — popups and dropdowns appear when you click (using the reconciled HTML)
5. **Fixes** — turns off "disabled" buttons that were frozen during the crawl

After stitching, open `storage/apps/zoho/stitched/` or run `serve` to browse it.

---

## What "serve" does

`serve` starts a tiny web server on your computer so you can open the copy in Chrome like a real website:

```bash
python main.py serve zoho                 # → http://localhost:8000
python main.py serve zoho --port 9000     # different port
python main.py serve zoho --watch         # reload when files change
python main.py serve zoho --no-open       # don't open browser automatically
```

- `/` goes to the dashboard (or the first page)
- Missing pages show a nice 404 page
- Everything stays on your computer — no calls to the real app

---

## Coverage check

If buttons don't work or pages are missing, run:

```bash
python main.py coverage zoho
```

It tells you:
- How many pages were saved vs how many routes exist
- Which links are broken
- Which buttons weren't wired up

To fix gaps, crawl more pages (maybe raise `max_pages_post_auth` in `config.py`), then reconcile and stitch again.

---

## Logging in

Login info is saved here:

```
storage/apps/zoho/metadata/auth.json
```

**First time:**
1. No auth file → Chrome opens
2. You log in
3. Press Enter in the terminal
4. Done — saved for next time

**Force a new login:**

```bash
rm storage/apps/zoho/metadata/auth.json
python main.py crawl-postauth zoho
```

---

## Adding a new app

Edit `config.py` and add your app to `APPS`:

```python
APPS = {
    "myapp": {
        "pre_auth_home": "https://example.com/",
        "login_url": "https://example.com/login",
        "post_auth_home": "https://app.example.com",
        "max_pages_pre_auth": 5,
        "max_pages_post_auth": 120,
        "max_interactions_per_page": 15,
        # ... more settings (see zoho example in config.py)
    },
}
```

Then run:

```bash
python main.py crawl myapp
python main.py reconcile myapp
python main.py stitch myapp
python main.py serve myapp
```

---

## Optional: AI analysis pipeline

After crawl + stitch, you can ask AI to describe the app:

```bash
python main.py html-clean zoho
python main.py analyze zoho
python main.py semantic_tree zoho
python main.py component_tree zoho
python main.py catalog zoho
python main.py workflows zoho
python main.py modules zoho
```

You need `GEMINI_API_KEY` in `.env`. Progress is in `storage/apps/{app}/metadata/pipeline_status.json`.

---

## Project files (what's what)

```
spider-python/
├── main.py                 ← run commands from here
├── crawler_v2.py           ← visits websites and saves pages
├── reconciler.py           ← finds what clicks added
├── stitcher_v1.py          ← builds the offline copy
├── coverage.py             ← finds missing/broken stuff
├── config.py               ← settings for each app
├── pipeline.py             ← runs AI analysis steps
├── analyzer/               ← AI tools
├── api/routes.py           ← web API
└── src/runtime/server.py   ← local server for serve command
```

---

## Experiments folder

The `experiments/` folder is an old prototype. **Don't change it.** All real code lives in the root folder and `analyzer/`.

To start the API: `python main.py api` → `http://localhost:8000`
