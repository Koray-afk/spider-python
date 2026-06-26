import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from urllib.parse import urlparse

from config import ROOT_DIR, STORAGE_DIR
from urls import normalize_crawl_url

MAX_SLUG_LENGTH = 120
SLUG_HASH_LENGTH = 8


def get_app_storage_root(app_name: str) -> Path:
    root = STORAGE_DIR / app_name
    for subdir in ("crawl", "screenshots", "metadata", "logs"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def url_to_slug(url: str) -> str:
    normalized = normalize_crawl_url(url)
    parsed = urlparse(normalized)
    route = parsed.path.strip("/")
    if not route:
        return "home"

    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", route).strip("-").lower()
    if not slug:
        return "home"

    if len(slug) > MAX_SLUG_LENGTH:
        digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:SLUG_HASH_LENGTH]
        keep = MAX_SLUG_LENGTH - SLUG_HASH_LENGTH - 1
        slug = f"{slug[:keep].rstrip('-')}-{digest}"

    return slug


def unique_page_dir(crawl_dir: Path, url: str, slug: str) -> Path:
    normalized = normalize_crawl_url(url)
    candidate = crawl_dir / slug
    if not candidate.exists():
        return candidate

    metadata_path = candidate / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("normalized_url") == normalized:
                return candidate
        except (json.JSONDecodeError, OSError):
            pass

    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:SLUG_HASH_LENGTH]
    return crawl_dir / f"{slug}-{digest}"


def save_page(
    app_name: str,
    url: str,
    title: str,
    html: str,
    screenshot_bytes: bytes,
    accessibility_tree: dict,
) -> Path:
    app_root = get_app_storage_root(app_name)
    crawl_dir = app_root / "crawl"

    normalized_url = normalize_crawl_url(url)
    slug = url_to_slug(url)
    page_dir = unique_page_dir(crawl_dir, url, slug)
    page_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "url": url,
        "normalized_url": normalized_url,
        "title": title,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "slug": page_dir.name,
    }

    (page_dir / "page.html").write_text(html, encoding="utf-8")
    (page_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (page_dir / "screenshot.png").write_bytes(screenshot_bytes)
    (page_dir / "accessibility-tree.json").write_text(
        json.dumps(accessibility_tree, indent=2),
        encoding="utf-8",
    )

    try:
        dir_label = page_dir.relative_to(ROOT_DIR)
    except ValueError:
        dir_label = page_dir

    print("[CAPTURE]")
    print(f"URL: {url}")
    print(f"NORMALIZED: {normalized_url}")
    print(f"SLUG: {page_dir.name}")
    print(f"DIR: {dir_label}")

    return page_dir
