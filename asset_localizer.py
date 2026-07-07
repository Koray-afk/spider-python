"""Download page assets (CSS, fonts, images) and rewrite HTML/CSS to local paths."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif"}
CSS_EXTS = {".css"}
FONT_EXTS = {".woff", ".woff2", ".ttf", ".eot", ".otf"}
MEDIA_EXTS = {".mp4", ".webm", ".mp3", ".pdf"}
DOWNLOAD_EXTS = IMAGE_EXTS | CSS_EXTS | FONT_EXTS | MEDIA_EXTS | {".json", ".map"}

_SKIP_SCHEMES = ("data:", "blob:", "javascript:", "mailto:", "tel:")
_ATTR_URL_RE = re.compile(
    r'\b(src|href|poster|data-src|xlink:href)=(["\'])((?:https?://|(?:\.\./)+assets/)[^"\']+)\2',
    re.IGNORECASE,
)
_STYLE_URL_RE = re.compile(
    r"url\(\s*(['\"]?)(?!data:)([^)\'\"]+)\1\s*\)",
    re.IGNORECASE,
)
_CSS_IMPORT_RE = re.compile(
    r"@import\s+(?:url\(\s*)?(['\"]?)(https?://[^)\'\"]+)\1\s*\)?",
    re.IGNORECASE,
)
_LOCAL_ASSET_RE = re.compile(r"(?:\.\./)+assets/([^)\'\"'\s]+)")
_MANIFEST_NAME = "_manifest.json"


def resolve_assets_dir(page_dir: Path) -> Path:
    """Return storage/apps/<app>/assets for a path under .../crawl/..."""
    for ancestor in page_dir.parents:
        if ancestor.name == "crawl":
            assets = ancestor.parent / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            return assets
    raise ValueError(f"Could not resolve assets dir from {page_dir}")


def assets_url_prefix(page_dir: Path, assets_dir: Path) -> str:
    rel = os.path.relpath(assets_dir, page_dir)
    return Path(rel).as_posix().replace("\\", "/") + "/"


def _maybe_gunzip(data: bytes) -> bytes:
    if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
        return gzip.decompress(data)
    return data


def _urlopen_asset(req: urllib.request.Request, timeout: int = 25):
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except ssl.SSLError:
        return urllib.request.urlopen(
            req, timeout=timeout, context=ssl._create_unverified_context()
        )


def _write_downloaded_asset(dest: Path, resp) -> None:
    raw = resp.read()
    encoding = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in encoding:
        raw = gzip.decompress(raw)
    else:
        raw = _maybe_gunzip(raw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)


def _load_manifest(assets_dir: Path) -> dict[str, str]:
    path = assets_dir / _MANIFEST_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_manifest(assets_dir: Path, manifest: dict[str, str]) -> None:
    (assets_dir / _MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def _url_key(url: str) -> str:
    """Manifest key (strip fragment only)."""
    return url.split("#", 1)[0]


def _ext_from_url(url: str) -> str:
    key = _url_key(url)
    path = urlparse(key).path
    ext = Path(path).suffix.lower()
    if ext:
        return ext
    if path.rstrip("/").endswith("/css") or "fonts.googleapis.com" in key:
        return ".css"
    return ""


def _bucket_for_ext(ext: str) -> str:
    if ext in CSS_EXTS:
        return "css"
    if ext in FONT_EXTS:
        return "fonts"
    if ext in IMAGE_EXTS:
        return "images"
    return "other"


def _local_path_for_url(url: str, manifest: dict[str, str]) -> str | None:
    base = url.split("#")[0].split("?")[0]
    return manifest.get(base) or manifest.get(url)


def _make_local_name(url: str) -> tuple[str, str]:
    key = _url_key(url)
    ext = _ext_from_url(key) or ".bin"
    bucket = _bucket_for_ext(ext)
    path_part = urlparse(key).path.lstrip("/")
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", path_part.replace("/", "_"))[:72] or "asset"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return bucket, f"{stem}_{digest}{ext}"


def _download_url(url: str, assets_dir: Path, manifest: dict[str, str]) -> str | None:
    key = _url_key(url)
    if not key.startswith(("http://", "https://")):
        return None
    if any(key.startswith(s) for s in _SKIP_SCHEMES):
        return None

    existing = manifest.get(key)
    if existing:
        dest = assets_dir / existing
        if dest.is_file():
            return existing

    bucket, local_name = _make_local_name(key)
    rel_path = f"{bucket}/{local_name}"
    dest = assets_dir / rel_path

    if dest.is_file():
        manifest[key] = rel_path
        return rel_path

    try:
        req = urllib.request.Request(
            key,
            headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"},
        )
        with _urlopen_asset(req) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            _write_downloaded_asset(dest, resp)
        if bucket == "css" or key.endswith(".css") or "text/css" in content_type:
            _localize_css_file(dest, assets_dir, manifest, referer=key)
        manifest[key] = rel_path
        print(f"[ASSETS] Downloaded {rel_path}")
        return rel_path
    except Exception as exc:
        print(f"[ASSETS] Failed {key}: {exc}")
        return None


def _localize_css_file(
    css_path: Path,
    assets_dir: Path,
    manifest: dict[str, str],
    *,
    referer: str,
) -> None:
    text = css_path.read_text(encoding="utf-8", errors="ignore")
    changed = False

    def _replace_url(match: re.Match) -> str:
        nonlocal changed
        raw = match.group(2).strip().strip("'\"")
        if raw.startswith(("data:", "blob:", "#")):
            return match.group(0)
        absolute = urljoin(referer, raw) if not raw.startswith(("http://", "https://")) else raw
        ext = _ext_from_url(absolute)
        if ext and ext not in DOWNLOAD_EXTS and ext not in {".css"}:
            return match.group(0)
        if ext in {".css"} or not ext or ext in DOWNLOAD_EXTS:
            rel = _download_url(absolute, assets_dir, manifest)
            if not rel:
                return match.group(0)
            changed = True
            css_rel = "../" + rel if not rel.startswith("../") else rel
            return f"url({css_rel})"

    new_text = _STYLE_URL_RE.sub(_replace_url, text)

    def _replace_import(match: re.Match) -> str:
        nonlocal changed
        raw = match.group(1).strip().strip("'\"")
        rel = _download_url(urljoin(referer, raw), assets_dir, manifest)
        if not rel:
            return match.group(0)
        changed = True
        css_rel = "../" + rel if not rel.startswith("../") else rel
        return f'@import url("{css_rel}")'

    new_text = _CSS_IMPORT_RE.sub(_replace_import, new_text)
    if changed:
        css_path.write_text(new_text, encoding="utf-8")


def _rewrite_url(raw: str, assets_dir: Path, manifest: dict[str, str], url_prefix: str) -> str:
    fragment = ""
    if "#" in raw and not raw.startswith("#"):
        raw, fragment = raw.split("#", 1)
        fragment = "#" + fragment

    if raw.startswith(("http://", "https://")):
        rel = _download_url(raw, assets_dir, manifest)
        if not rel:
            return raw + fragment
        return f"{url_prefix}{rel}{fragment}"

    local_match = _LOCAL_ASSET_RE.match(raw)
    if local_match:
        rel = local_match.group(1)
        return f"{url_prefix}{rel}{fragment}"

    return raw + fragment


def localize_html_assets(
    html: str,
    page_url: str,
    assets_dir: Path,
    url_prefix: str,
    *,
    download_missing: bool = True,
) -> tuple[str, dict]:
    """Download remote assets referenced in HTML and rewrite to local paths."""
    manifest = _load_manifest(assets_dir)
    stats = {"downloaded": 0, "rewritten": 0}
    before = len(manifest)

    def _attr_repl(match: re.Match) -> str:
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith("#") or any(url.startswith(s) for s in _SKIP_SCHEMES):
            return match.group(0)
        ext = _ext_from_url(url.split("#")[0].split("?")[0])
        if ext == ".js" or ext == ".mjs":
            return match.group(0)
        if not download_missing and url.startswith(("http://", "https://")):
            rel = _local_path_for_url(url, manifest)
            if not rel:
                return match.group(0)
            stats["rewritten"] += 1
            frag = ""
            if "#" in url:
                _, frag = url.split("#", 1)
                frag = "#" + frag
            return f"{attr}={quote}{url_prefix}{rel}{frag}{quote}"
        new_url = _rewrite_url(url, assets_dir, manifest, url_prefix)
        if new_url != url:
            stats["rewritten"] += 1
        return f"{attr}={quote}{new_url}{quote}"

    html = _ATTR_URL_RE.sub(_attr_repl, html)

    def _style_block_repl(match: re.Match) -> str:
        block = match.group(0)

        def _url_repl(um: re.Match) -> str:
            raw = um.group(2).strip().strip("'\"")
            if raw.startswith(("data:", "blob:", "#")):
                return um.group(0)
            absolute = urljoin(page_url, raw) if not raw.startswith(("http://", "https://", "../")) else raw
            if absolute.startswith("../"):
                rel = _LOCAL_ASSET_RE.match(absolute)
                if rel:
                    stats["rewritten"] += 1
                    return f"url({url_prefix}{rel.group(1)})"
                return um.group(0)
            new_url = _rewrite_url(absolute, assets_dir, manifest, url_prefix)
            if new_url != absolute:
                stats["rewritten"] += 1
                return f"url({new_url})"
            return um.group(0)

        return _STYLE_URL_RE.sub(_url_repl, block)

    html = re.sub(
        r"<style\b[^>]*>[\s\S]*?</style>",
        _style_block_repl,
        html,
        flags=re.IGNORECASE,
    )

    stats["downloaded"] = len(manifest) - before
    _save_manifest(assets_dir, manifest)
    return html, stats


def rewire_asset_prefix(html: str, url_prefix: str) -> str:
    """Replace any (.../)+assets/ prefix with the stitch-time prefix."""
    return _LOCAL_ASSET_RE.sub(lambda m: f"{url_prefix}{m.group(1)}", html)


def copy_assets_to_stitched(app_assets_dir: Path, stitched_assets_dir: Path) -> int:
    """Copy app-level crawl assets into stitched/assets (merge, do not wipe)."""
    if not app_assets_dir.is_dir():
        stitched_assets_dir.mkdir(parents=True, exist_ok=True)
        return 0
    copied = 0
    for src in app_assets_dir.rglob("*"):
        if not src.is_file() or src.name == _MANIFEST_NAME:
            continue
        rel = src.relative_to(app_assets_dir)
        dest = stitched_assets_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
            copied += 1
    manifest_src = app_assets_dir / _MANIFEST_NAME
    if manifest_src.is_file():
        shutil.copy2(manifest_src, stitched_assets_dir / _MANIFEST_NAME)
    return copied


def finalize_asset_tree(assets_dir: Path) -> None:
    """Ensure CSS bundles under assets/ have fonts/images localized."""
    if not assets_dir.is_dir():
        return
    manifest = _load_manifest(assets_dir)
    for css_path in assets_dir.glob("css/*.css"):
        _localize_css_file(
            css_path, assets_dir, manifest, referer=css_path.resolve().as_uri()
        )
    _save_manifest(assets_dir, manifest)
