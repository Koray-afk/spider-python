"""Pipeline stage I/O logging and path guards — orchestration only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def log_stage(stage: str) -> None:
    print(f"\n=== {stage} ===")


def log_input(path: Path | str) -> None:
    print(f"INPUT FILE: {path}")


def log_output(path: Path | str) -> None:
    print(f"OUTPUT FILE: {path}")


def log_skip(path: Path | str, reason: str) -> None:
    print(f"SKIP FILE: {path} ({reason})")


def is_pre_auth_url(url: str) -> bool:
    return "books.zoho" not in url and "zoho.com" in url


def load_sitemap(metadata_dir: Path) -> list[dict]:
    path = metadata_dir / "sitemap.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_pipeline_status(metadata_dir: Path) -> dict:
    path = metadata_dir / "pipeline_status.json"
    if not path.exists():
        return {
            "crawl_completed": False,
            "stitch_completed": False,
            "clean_completed": False,
            "last_run": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_pipeline_status(metadata_dir: Path, **updates) -> Path:
    path = metadata_dir / "pipeline_status.json"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    status = load_pipeline_status(metadata_dir)
    status.update(updates)
    status["last_run"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    log_output(path)
    return path


def assert_crawler_paths(raw_dir: Path, stitched_dir: Path, cleaned_dir: Path) -> None:
    """Crawler must only write raw_html; never stitched or cleaned."""
    if raw_dir.resolve() == stitched_dir.resolve():
        raise RuntimeError("raw_html and stitched_html must be different directories")
    if raw_dir.resolve() == cleaned_dir.resolve():
        raise RuntimeError("raw_html and cleaned_html must be different directories")


def verify_stitch_sources(raw_dir: Path, stitched_dir: Path, sitemap: list[dict]) -> None:
    """Stitched HTML must be generated from raw_html only."""
    for item in sitemap:
        slug = item["slug"]
        src = raw_dir / slug / "index.html"
        dest = stitched_dir / slug / "index.html"
        if dest.exists() and not src.exists():
            raise RuntimeError(
                f"stitched_html/{slug}/index.html exists without raw_html source"
            )
        if src.exists() and dest.exists():
            if src.stat().st_mtime > dest.stat().st_mtime:
                print(f"  note: raw_html/{slug} is newer than stitched_html/{slug}")


def verify_no_double_stitch(stitched_dir: Path, sitemap: list[dict]) -> None:
    """Detect accidental second-pass stitch markers stacked in output."""
    for item in sitemap:
        dest = stitched_dir / item["slug"] / "index.html"
        if not dest.exists():
            continue
        html = dest.read_text(encoding="utf-8")
        if html.count('id="static-replica-sidebar"') > 1:
            raise RuntimeError(
                f"stitched_html/{item['slug']} has duplicate static-replica-sidebar "
                "(stitcher may have run twice)"
            )
        if html.count('id="static-replica-ui"') > 1:
            raise RuntimeError(
                f"stitched_html/{item['slug']} has duplicate static-replica-ui "
                "(stitcher may have run twice)"
            )


def log_page_io_pairs(
    input_dir: Path,
    output_dir: Path,
    *,
    layout: str = "folder",
) -> int:
    """Log INPUT/OUTPUT for each page processed."""
    count = 0
    for src in sorted(input_dir.glob("*/index.html")):
        slug = src.parent.name
        log_input(src)
        if layout == "folder":
            dest = output_dir / slug / "index.html"
        else:
            import re

            flat_slug = re.sub(r"^app-\d+-", "", slug)
            dest = output_dir / f"{flat_slug}.html"
        if dest.exists():
            log_output(dest)
        else:
            log_skip(dest, "not written")
        count += 1
    return count


def pick_preview_slug(metadata_dir: Path) -> str:
    from stitcher.page_stitch import pick_entry_slug

    sitemap = load_sitemap(metadata_dir)
    if not sitemap:
        return "<slug>"
    return pick_entry_slug(sitemap) or sitemap[0]["slug"]


def print_serve_instructions(
    app_name: str,
    metadata_dir: Path,
    stitched_dir: Path,
    *,
    port: int = 8080,
) -> None:
    """Print app-specific preview instructions after stitching."""
    entry = pick_preview_slug(metadata_dir)

    print()
    print("✅ Stitch complete")
    print()
    print("Preview:")
    print(f"python main.py preview {app_name}")
    print()
    print("Or manually:")
    print()
    print(f"cd {stitched_dir.resolve()}")
    print(f"python3 -m http.server {port}")
    print()
    print("Open:")
    print(f"http://localhost:{port}/{entry}/index.html")
    print()
    print("(do not open file:// directly)")
