"""End-to-end pipeline: clean → catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from html_cleaner import clean_all_pages, discover_page_html_files
from processors.catalog_page import catalog_all_pages, catalog_one_page


def run_pipeline(
    pages_dir: str = "pages",
    analysis_dir: str = "analysis",
    skip_catalog: bool = False,
    skip_clean: bool = False,
    slug: str | None = None,
) -> None:
    print("=" * 60)
    print("STEP 1 — Clean HTML (preserve icons)")
    print("=" * 60)
    if not skip_clean:
        clean_all_pages(pages_dir=pages_dir, output_dir=f"{analysis_dir}/cleaned")
    else:
        print("  ⏩ Skipped")

    print("\n" + "=" * 60)
    print("STEP 2 — Catalog elements (Agent 1)")
    print("=" * 60)
    if not skip_catalog:
        if slug:
            pages_path = Path(pages_dir)
            html_files = discover_page_html_files(pages_path)
            match = next(
                (p for p in html_files if p.stem == slug or p.parent.name == slug),
                None,
            )
            if not match:
                raise FileNotFoundError(f"No HTML for slug {slug}")
            catalog_one_page(match, pages_path, Path(analysis_dir))
        else:
            catalog_all_pages(pages_dir=pages_dir, output_dir=analysis_dir)
    else:
        print("  ⏩ Skipped")

    print("\n🎉 Pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run clean → catalog pipeline")
    parser.add_argument("--pages-dir", default="pages")
    parser.add_argument("--analysis-dir", default="analysis")
    parser.add_argument("--slug", help="Run for one page only")
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-catalog", action="store_true")
    args = parser.parse_args()

    run_pipeline(
        pages_dir=args.pages_dir,
        analysis_dir=args.analysis_dir,
        skip_catalog=args.skip_catalog,
        skip_clean=args.skip_clean,
        slug=args.slug,
    )
