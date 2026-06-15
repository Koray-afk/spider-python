"""
Full pipeline: crawl → stitch → clean → catalog → JS generate → validate

Usage:
  python3 run_pipeline.py                    # all steps on existing pages/
  python3 run_pipeline.py --crawl            # re-crawl first
  python3 run_pipeline.py --slug contacts    # one page only
  python3 run_pipeline.py --skip-crawl --skip-catalog  # JS only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from html_cleaner import clean_all_pages, discover_page_html_files
from page_stitch import stitch_pages
from processors.catalog_page import catalog_all_pages, catalog_one_page


def _step(n: int, title: str) -> None:
    print(f"\n{'='*60}\nSTEP {n} — {title}\n{'='*60}")


def run(
    pages_dir: str = "pages",
    analysis_dir: str = "analysis",
    slug: str | None = None,
    crawl: bool = False,
    skip_stitch: bool = False,
    skip_clean: bool = False,
    skip_catalog: bool = False,
    skip_js: bool = False,
    gemini_catalog: bool = False,
) -> None:
    pages_path = Path(pages_dir)

    if crawl:
        _step(1, "Crawl + stitch (Playwright)")
        subprocess.run([sys.executable, "crawl_authenticated_pages.py"], check=True)
    elif not skip_stitch and (pages_path / "sitemap.json").exists():
        _step(1, "Re-stitch offline navigation")
        stitch_pages(pages_dir=pages_dir)
    else:
        _step(1, "Crawl")
        print("  ⏩ skipped (pages/ already populated)")

    _step(2, "Clean HTML for LLM")
    if not skip_clean:
        n = clean_all_pages(pages_dir=pages_dir, output_dir=f"{analysis_dir}/cleaned")
        print(f"  ✅ Cleaned {n} pages")
    else:
        print("  ⏩ skipped")

    _step(3, "Catalog elements + screenshots")
    if not skip_catalog:
        heuristic = not gemini_catalog
        mode = "heuristic (fast)" if heuristic else "Gemini per-element"
        print(f"  Mode: {mode}")
        if slug:
            match = next(
                (p for p in discover_page_html_files(pages_path) if p.stem == slug),
                None,
            )
            if not match:
                raise FileNotFoundError(f"No HTML for slug: {slug}")
            catalog_one_page(match, pages_path, Path(analysis_dir), heuristic=heuristic)
        else:
            catalog_all_pages(
                pages_dir=pages_dir,
                output_dir=analysis_dir,
                skip_existing=False,
                heuristic=heuristic,
            )
    else:
        print("  ⏩ skipped")

    _step(4, "Generate JS + validate state changes")
    if not skip_js:
        from agents.js_agent import run_all, run_js_agent

        if slug:
            result = run_js_agent(slug, pages_dir=pages_dir, analysis_dir=analysis_dir)
            print(f"  {slug}: passed={result.get('passed','?')}, failed={result.get('failed','?')}")
        else:
            run_all(pages_dir=pages_dir, analysis_dir=analysis_dir)
    else:
        print("  ⏩ skipped")

    print("\n🎉 Pipeline complete.")
    print(f"   Serve:  cd {pages_dir} && python3 -m http.server 8080")
    print(f"   Open:   http://localhost:8080/{slug or 'contacts'}.html")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Zoho Books offline clickable pipeline")
    p.add_argument("--slug", help="Run for one page only")
    p.add_argument("--crawl", action="store_true", help="Re-crawl live site first")
    p.add_argument("--skip-stitch", action="store_true")
    p.add_argument("--skip-clean", action="store_true")
    p.add_argument("--skip-catalog", action="store_true")
    p.add_argument("--skip-js", action="store_true")
    p.add_argument("--gemini-catalog", action="store_true", help="Slow: Gemini per-element catalog")
    p.add_argument("--pages-dir", default="pages")
    p.add_argument("--analysis-dir", default="analysis")
    args = p.parse_args()

    run(
        pages_dir=args.pages_dir,
        analysis_dir=args.analysis_dir,
        slug=args.slug,
        crawl=args.crawl,
        skip_stitch=args.skip_stitch,
        skip_clean=args.skip_clean,
        skip_catalog=args.skip_catalog,
        skip_js=args.skip_js,
        gemini_catalog=args.gemini_catalog,
    )
