# Spider Python

Spider Python is a small web-crawling and page-analysis project built with Python, Playwright, and Gemini. It visits a webpage, captures its content, and then analyzes the page structure and intent using an LLM.

## What it does

The project currently focuses on a single-page crawl flow:

1. Opens a target website with Playwright.
2. Collects the page HTML, visible text, and a screenshot.
3. Saves the captured content locally.
4. Sends the extracted text to Gemini for structured page analysis.
5. Stores the analysis as JSON.

## Features

- Browser automation with Playwright.
- HTML, text, and screenshot capture for webpages.
- Gemini-powered page analysis.
- Structured output through a Pydantic model.
- Local file storage for raw page data and analysis results.
- Simple service layer for text analysis reuse.

## Project Structure

- `crawler.py` - Crawls a webpage and saves page artifacts.
- `processors/analyze_page.py` - Analyzes saved page text and writes structured JSON output.
- `services/gemini_service.py` - Helper service for sending prompts to Gemini.
- `models/page_analysis.py` - Schema for the structured analysis response.
- `pages/` - Saved page artifacts such as HTML, text, and screenshots.
- `analysis/` - Saved analysis JSON files.

## Requirements

- Python 3.10 or newer.
- A valid `GEMINI_API_KEY` in your environment.
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

Set your Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

If you want this to persist between sessions, add it to your shell profile or place it in a `.env` file.

## How to Run

### 1. Crawl a webpage

This script visits the configured URL in `crawler.py` and saves the results into `pages/`.

```bash
python crawler.py
```

### 2. Analyze the saved page text

This script reads `pages/page-1.txt`, sends it to Gemini, and writes the structured result to `analysis/page-1.json`.

```bash
python processors/analyze_page.py
```

### 3. Test the Gemini service

This script sends a sample prompt through the Gemini helper service.

```bash
python test_gemini.py
```

## Output Files

After running the crawler and analyzer, you should see files like these:

- `pages/page-1.html`
- `pages/page-1.txt`
- `pages/page-1.png`
- `analysis/page-1.json`

## Environment Variables

| Variable | Description |
| --- | --- |
| `GEMINI_API_KEY` | API key used to authenticate with Gemini. |

## Notes

- The crawler currently targets `https://google.com` in `crawler.py`.
- The analyzer currently reads from `pages/page-1.txt` and saves the result to `analysis/page-1.json`.
- You can change the target URL and output file names directly in the scripts.

## Example Analysis Schema

The structured Gemini output follows the `PageAnalysis` model:

- `pageType`
- `purpose`
- `mainCTA`
- `importantSections`
- `summary`

## License

No license file is currently included in this repository.