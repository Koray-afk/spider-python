# Spider Python

Spider Python is a web-crawling and page-analysis project built with Python, Playwright, and Gemini. It crawls websites, captures page artifacts, analyzes structure and intent with an LLM, and can generate visual HTML replicas from screenshots.

## What it does

The full pipeline:

1. Crawls a target website with Playwright (multi-page BFS crawl).
2. Saves HTML, visible text, and full-page screenshots for each page.
3. Analyzes pages with Gemini using text + screenshots (structured JSON output).
4. Generates self-contained HTML replicas that visually match the screenshots.

## Features

- Multi-page browser crawling with Playwright (configurable `max_pages`).
- HTML, text, and full-page screenshot capture.
- Gemini-powered page analysis (text + image, structured via Pydantic).
- Visual HTML replica generation from screenshots.
- Local file storage for raw page data, analysis, and replicas.
- Skip logic — re-running analysis or replica generation skips already-processed pages.

## Project Structure

- `crawler.py` — Crawls pages and saves artifacts to `pages/`.
- `processors/analyse_all_pages.py` — Analyzes all saved pages (text + screenshot) via LangChain; writes JSON to `analysis/`.
- `processors/analyze_page.py` — Alternative screenshot-only analyzer via `gemini_service`.
- `replica_generator.py` — Generates visual HTML replicas from screenshots into `replicas/`.
- `services/gemini_service.py` — Gemini client for screenshot analysis and HTML replica generation.
- `models/page_analysis.py` — Pydantic schema for structured analysis output.
- `pages/` — Saved page artifacts (HTML, text, screenshots).
- `analysis/` — Saved analysis JSON files.
- `replicas/` — Generated HTML replica files.

## Requirements

- Python 3.10 or newer.
- A valid `GEMINI_API_KEY` in your environment or `.env` file.
- Playwright browser binaries installed locally.

## Installation

Clone the repository and create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install the dependencies:

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

Or export it in your shell:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

## How to Run

Run these in order from the project root (with your venv activated):

### 1. Crawl pages

Visits the configured start URL in `crawler.py` (default: `https://www.hubspot.com/`), follows discovered links, and saves up to `max_pages` pages into `pages/`.

```bash
python crawler.py
```

### 2. Analyze all crawled pages

Reads every `pages/page-*.txt` file, sends text + screenshot to Gemini, and writes structured JSON to `analysis/`.

```bash
python -m processors.analyse_all_pages
```

### 3. Generate HTML replicas

Reads every `pages/page-*.png` screenshot, sends it to Gemini, and writes a visual HTML replica to `replicas/`. Skips pages that already have a replica file.

```bash
python replica_generator.py
```

> **Note:** Replica generation calls Gemini once per page and can take several minutes per screenshot (especially for large full-page captures). The script prints progress but stays silent while waiting on each API response.

### Alternative: screenshot-only analysis

If you prefer analysis from screenshots only (without LangChain):

```bash
python processors/analyze_page.py
```

## Output Files

After a full run you should see files like:

**`pages/`**
- `page-1.html` — raw page HTML
- `page-1.txt` — visible text content
- `page-1.png` — full-page screenshot

**`analysis/`**
- `page-1.json` — structured Gemini analysis

**`replicas/`**
- `page-1.html` — generated visual replica

## Environment Variables

| Variable | Description |
| --- | --- |
| `GEMINI_API_KEY` | API key used to authenticate with Gemini. |

## Configuration

Edit these directly in the scripts:

| Setting | File | Default |
| --- | --- | --- |
| Start URL | `crawler.py` | `https://www.hubspot.com/` |
| Max pages to crawl | `crawler.py` | `5` |
| Gemini model | `services/gemini_service.py`, `processors/analyse_all_pages.py` | `gemini-2.5-flash` |

## Example Analysis Schema

The structured Gemini output follows the `PageAnalysis` model:

- `pageType`
- `purpose`
- `mainCTA`
- `importantSections`
- `summary`
- `visualLayout` (optional)
- `colorScheme` (optional)

## License

No license file is currently included in this repository.
