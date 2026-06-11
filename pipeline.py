"""Orchestration only — no business logic."""

import subprocess
import sys

from config.apps import get_app_config
from crawler.crawler_v2 import crawl_application
from stitcher.page_stitch import stitch_application
from analyzer.html_cleaner import clean_application
from analyzer.business_analyzer import analyze_application
from analyzer.app_catalog_analyzer import build_catalog_application
from analyzer.semantic_tree_analyzer import analyze_semantic_tree_application
from storage.storage_manager import (
    create_app_storage,
    get_app_catalog_dir,
    get_business_json_dir,
    get_cleaned_html_dir,
    get_metadata_dir,
    get_raw_html_dir,
    get_semantic_tree_dir,
    get_stitched_html_dir,
)
from pipeline_io import (
    assert_crawler_paths,
    load_sitemap,
    log_input,
    log_output,
    log_page_io_pairs,
    log_stage,
    pick_preview_slug,
    print_serve_instructions,
    save_pipeline_status,
    verify_no_double_stitch,
    verify_stitch_sources,
)

DEFAULT_PREVIEW_PORT = 8080


def run_crawl_pipeline(app_name: str, *, auto_stitch: bool = True) -> dict:
    """Crawl then stitch (experiments Phase 4) so offline pages are ready to view."""
    create_app_storage(app_name)
    raw_dir = get_raw_html_dir(app_name)
    stitched_dir = get_stitched_html_dir(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    assert_crawler_paths(raw_dir, stitched_dir, cleaned_dir)

    log_stage("CRAWL")
    log_output(raw_dir / "<slug>" / "index.html")

    cfg = get_app_config(app_name)
    crawl_result = crawl_application(
        app_name=app_name,
        pre_auth_home=cfg["pre_auth_home"],
        login_url=cfg["login_url"],
        post_auth_home=cfg["post_auth_home"],
        max_pages_pre_auth=cfg["max_pages_pre_auth"],
        max_pages_post_auth=cfg["max_pages_post_auth"],
    )

    sitemap = load_sitemap(get_metadata_dir(app_name))
    for item in sitemap:
        src = raw_dir / item["slug"] / "index.html"
        if src.exists():
            log_input(f"(browser) {item['url']}")
            log_output(src)

    metadata_dir = get_metadata_dir(app_name)
    save_pipeline_status(metadata_dir, crawl_completed=True)

    result = {"crawl": crawl_result}
    if auto_stitch:
        result["stitch"] = run_stitch_pipeline(app_name, from_crawl=True)
    else:
        print()
        print("  ⚠ View pre-auth pages from stitched_html after stitching.")
        print("    raw_html keeps live JS/tracking scripts and may show duplicate headers.")
    return result


def run_stitch_pipeline(app_name: str, *, from_crawl: bool = False) -> dict:
    """Read raw_html only; write stitched_html. Never modifies raw_html."""
    create_app_storage(app_name)
    raw_dir = get_raw_html_dir(app_name)
    stitched_dir = get_stitched_html_dir(app_name)
    metadata_dir = get_metadata_dir(app_name)

    if not from_crawl:
        log_stage("STITCH")

    log_input(raw_dir / "<slug>" / "index.html")
    log_output(stitched_dir / "<slug>" / "index.html")

    if not raw_dir.is_dir():
        raise FileNotFoundError(f"No raw HTML at {raw_dir}")

    stitch_result = stitch_application(app_name)
    log_page_io_pairs(raw_dir, stitched_dir)

    sitemap = load_sitemap(metadata_dir)
    verify_stitch_sources(raw_dir, stitched_dir, sitemap)
    verify_no_double_stitch(stitched_dir, sitemap)
    print_serve_instructions(app_name, metadata_dir, stitched_dir)

    save_pipeline_status(metadata_dir, stitch_completed=True)
    return stitch_result


def run_clean_pipeline(app_name: str) -> dict:
    """Read stitched_html only; write cleaned_html. Never touches raw or stitched."""
    create_app_storage(app_name)
    stitched_dir = get_stitched_html_dir(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)

    log_stage("CLEAN")
    log_input(stitched_dir / "<slug>" / "index.html")
    log_output(cleaned_dir / "<slug>.html")

    if not stitched_dir.is_dir() or not any(stitched_dir.glob("*/index.html")):
        raise FileNotFoundError(
            f"No stitched HTML at {stitched_dir} — run stitch before clean"
        )

    clean_result = clean_application(app_name)
    log_page_io_pairs(stitched_dir, cleaned_dir, layout="flat")
    save_pipeline_status(get_metadata_dir(app_name), clean_completed=True)
    return clean_result


def run_analyze_pipeline(app_name: str) -> dict:
    """Read cleaned_html only; write business_json. Requires GEMINI_API_KEY."""
    create_app_storage(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    business_dir = get_business_json_dir(app_name)

    log_stage("ANALYZE")
    log_input(cleaned_dir / "<slug>.html")
    log_output(business_dir / "<slug>.json")

    if not cleaned_dir.is_dir() or not any(cleaned_dir.glob("*.html")):
        raise FileNotFoundError(
            f"No cleaned HTML at {cleaned_dir} — run clean before analyze"
        )

    analyze_result = analyze_application(app_name)
    save_pipeline_status(get_metadata_dir(app_name), analyze_completed=True)
    return analyze_result


def run_semantic_tree_pipeline(app_name: str) -> dict:
    """Read cleaned_html + business_json; write semantic_tree. Requires GEMINI_API_KEY."""
    create_app_storage(app_name)
    cleaned_dir = get_cleaned_html_dir(app_name)
    business_dir = get_business_json_dir(app_name)
    semantic_tree_dir = get_semantic_tree_dir(app_name)

    log_stage("SEMANTIC_TREE")
    log_input(cleaned_dir / "<slug>.html")
    log_input(business_dir / "<slug>.json")
    log_output(semantic_tree_dir / "<slug>.json")

    if not cleaned_dir.is_dir() or not any(cleaned_dir.glob("*.html")):
        raise FileNotFoundError(
            f"No cleaned HTML at {cleaned_dir} — run clean before semantic_tree"
        )

    semantic_result = analyze_semantic_tree_application(app_name)
    save_pipeline_status(get_metadata_dir(app_name), semantic_tree_completed=True)
    return semantic_result


def run_catalog_pipeline(app_name: str) -> dict:
    """Read business_json + semantic_tree; write app_catalog/catalog.json."""
    create_app_storage(app_name)
    business_dir = get_business_json_dir(app_name)
    semantic_tree_dir = get_semantic_tree_dir(app_name)
    catalog_dir = get_app_catalog_dir(app_name)

    log_stage("CATALOG")
    log_input(business_dir / "<slug>.json")
    log_input(semantic_tree_dir / "<slug>.json")
    log_output(catalog_dir / "catalog.json")

    if not semantic_tree_dir.is_dir() or not any(semantic_tree_dir.glob("*.json")):
        raise FileNotFoundError(
            f"No semantic trees at {semantic_tree_dir} — run semantic_tree first"
        )

    catalog_result = build_catalog_application(app_name)
    save_pipeline_status(get_metadata_dir(app_name), catalog_completed=True)
    return catalog_result


def run_full_pipeline(app_name: str) -> dict:
    create_app_storage(app_name)
    result = {}

    print("[1/3] Crawling...")
    print("[2/3] Stitching... (auto after crawl, experiments Phase 4)")
    crawl_bundle = run_crawl_pipeline(app_name, auto_stitch=True)
    result["crawl"] = crawl_bundle["crawl"]
    result["stitch"] = crawl_bundle.get("stitch", {})

    print("[3/3] Cleaning...")
    result["clean"] = run_clean_pipeline(app_name)

    print()
    print(f"[✓] Crawled {result['crawl']['pages_crawled']} pages")
    print(f"[✓] Stitched {result['stitch']['pages_stitched']} pages")
    print(f"[✓] Cleaned {result['clean']['pages_cleaned']} pages")

    return result


def run_preview_pipeline(app_name: str, port: int = DEFAULT_PREVIEW_PORT) -> None:
    """Serve stitched HTML for one app from storage/apps/{app}/stitched_html."""
    create_app_storage(app_name)
    stitched_dir = get_stitched_html_dir(app_name)
    metadata_dir = get_metadata_dir(app_name)

    if not stitched_dir.is_dir() or not any(stitched_dir.glob("*/index.html")):
        raise FileNotFoundError(
            f"No stitched HTML at {stitched_dir}. "
            f"Run: python main.py stitch {app_name}"
        )

    entry = pick_preview_slug(metadata_dir)
    print(f"Previewing app: {app_name}")
    print()
    print("Serve:")
    print(stitched_dir.resolve())
    print()
    print(f"cd {stitched_dir.resolve()}")
    print(f"python3 -m http.server {port}")
    print()
    print("Open:")
    print(f"http://localhost:{port}/{entry}/index.html")
    print()
    print("(Ctrl+C to stop)")
    print()

    subprocess.run(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=stitched_dir,
        check=False,
    )
