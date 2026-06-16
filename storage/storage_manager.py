"""Storage paths — unified under storage/apps/<app>/."""

import shutil
from pathlib import Path

APPS_ROOT = Path("storage") / "apps"

SUBDIRS = (
    "raw_html",
    "screenshots",
    "assets",
    "stitched_html",
    "cleaned_html",
    "business_json",
    "semantic_tree",
    "component_tree",
    "app_catalog",
    "metadata",
    "logs",
    "crawl",
    "stitched",
)


def get_app_root(app_name: str) -> Path:
    return APPS_ROOT / app_name


def create_app_storage(app_name: str) -> Path:
    root = get_app_root(app_name)
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def get_raw_html_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "raw_html"


def get_screenshots_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "screenshots"


def get_assets_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "assets"


def get_stitched_html_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "stitched_html"


def get_cleaned_html_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "cleaned_html"


def get_business_json_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "business_json"


def get_semantic_tree_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "semantic_tree"


def get_component_tree_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "component_tree"


def get_app_catalog_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "app_catalog"


def get_workflows_path(app_name: str) -> Path:
    return get_app_catalog_dir(app_name) / "workflows.json"


def get_modules_path(app_name: str) -> Path:
    return get_app_catalog_dir(app_name) / "modules.json"


def get_metadata_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "metadata"


def get_crawl_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "crawl"


def get_stitched_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "stitched"


def clean_stitched(app_name: str) -> None:
    path = get_stitched_dir(app_name)
    if path.exists():
        shutil.rmtree(path)


def get_auth_file(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "auth.json"


def get_session_file(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "session.json"


def get_sitemap_path(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "sitemap.json"


def ensure_app_dirs(app_name: str) -> Path:
    get_metadata_dir(app_name).mkdir(parents=True, exist_ok=True)
    crawl_dir = get_crawl_dir(app_name)
    crawl_dir.mkdir(parents=True, exist_ok=True)
    return crawl_dir


def clean_crawl(app_name: str) -> None:
    path = get_crawl_dir(app_name)
    if path.exists():
        shutil.rmtree(path)
    ensure_app_dirs(app_name)


def crawl_stats(app_name: str) -> dict:
    root = get_crawl_dir(app_name)
    if not root.is_dir():
        return {"pages": 0, "interactions": 0, "bytes": 0}

    pages = sum(1 for p in root.iterdir() if p.is_dir() and (p / "page.html").exists())
    interactions = sum(
        1 for p in root.rglob("interactions/*") if p.is_dir() and (p / "page.html").exists()
    )
    total_bytes = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())

    return {"pages": pages, "interactions": interactions, "bytes": total_bytes}
