"""Multi-app storage paths under storage/apps/{app_name}/."""

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


def get_metadata_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "metadata"


def get_auth_file(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "auth.json"


def get_session_file(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "session.json"


def get_pipeline_status_path(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "pipeline_status.json"


def get_logs_dir(app_name: str) -> Path:
    return get_app_root(app_name) / "logs"


def get_sitemap_path(app_name: str) -> Path:
    return get_metadata_dir(app_name) / "sitemap.json"
