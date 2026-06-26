import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

from config import STORAGE_DIR

QUERY_HASH_LENGTH = 8


def apps_storage_dir(app_name: str) -> Path:
    return STORAGE_DIR / "apps" / app_name


def global_mock_dir(app_name: str) -> Path:
    path = apps_storage_dir(app_name) / "mock_api"
    path.mkdir(parents=True, exist_ok=True)
    return path


def global_registry_path(app_name: str) -> Path:
    return apps_storage_dir(app_name) / "mock_registry.json"


def mock_filename(method: str, url: str) -> str:
    parsed = urlparse(url)
    path_part = parsed.path.strip("/").replace("/", "_") or "root_api"
    query_suffix = ""
    if parsed.query:
        digest = hashlib.md5(parsed.query.encode("utf-8")).hexdigest()[:QUERY_HASH_LENGTH]
        query_suffix = f"_{digest}"
    return f"{method.lower()}_{path_part}{query_suffix}.json"


def mock_registry_key(method: str, url: str) -> str:
    parsed = urlparse(url)
    query = parsed.query
    if query:
        query = urlencode(sorted(parse_qsl(query, keep_blank_values=True)))
    path = parsed.path or "/"
    return f"{method.upper()} {path}" + (f"?{query}" if query else "")


def mock_path_key(method: str, url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    return f"{method.upper()} {path}"


def save_mock_payload(app_name: str, method: str, url: str, payload) -> tuple[str, str]:
    filename = mock_filename(method, url)
    filepath = global_mock_dir(app_name) / filename
    filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return filename, mock_registry_key(method, url)


class PageApiRecorder:
    def __init__(self, app_name: str, api_origin: str) -> None:
        self.app_name = app_name
        self.api_origin = api_origin.rstrip("/")
        self.captures: list[dict] = []
        self._seen_keys: set[str] = set()

    def should_capture(self, url: str, content_type: str) -> bool:
        if "application/json" not in content_type.lower():
            return False
        return url.startswith(self.api_origin)

    async def handle_response(self, response) -> None:
        url = response.url
        method = response.request.method
        content_type = response.headers.get("content-type", "")

        if not self.should_capture(url, content_type):
            return

        try:
            payload = await response.json()
            registry_key = mock_registry_key(method, url)
            if registry_key in self._seen_keys:
                return

            filename, registry_key = save_mock_payload(self.app_name, method, url, payload)
            self._seen_keys.add(registry_key)

            entry = {
                "method": method,
                "url": url,
                "registry_key": registry_key,
                "path_key": mock_path_key(method, url),
                "mock_file": filename,
            }
            self.captures.append(entry)

            print("\n" + "┌" + "─" * 78 + "┐")
            print("│ [NETWORK-API] CAPTURED ENDPOINT MATCH")
            print("├" + "─" * 78 + "┤")
            print(f"│  URL    : {url[:70]}")
            print(f"│  METHOD : {method} | TYPE: {content_type}")
            print(f"│  STORAGE: storage/apps/{self.app_name}/mock_api/{filename}")
            if isinstance(payload, dict):
                keys_found = list(payload.keys())[:8]
                print(f"│  PAYLOAD: Keys extracted -> {keys_found}")
            elif isinstance(payload, list):
                print(f"│  PAYLOAD: Root layout is an Array [Length: {len(payload)} items]")
            print("└" + "─" * 78 + "┘\n")

        except Exception as exc:
            print(
                f"  └─> [RECORDER-WARN] Skipped file serialization pass for {url[:50]} "
                f"| Reason: {exc}"
            )

    def save_page_manifest(self, page_dir: Path, page_slug: str) -> None:
        manifest = {
            "page_slug": page_slug,
            "api_origin": self.api_origin,
            "captures": self.captures,
        }
        (page_dir / "api-manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )

    def merge_into_global_registry(self, page_slug: str) -> None:
        registry_path = global_registry_path(self.app_name)
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        else:
            registry = {}

        for capture in self.captures:
            key = capture["registry_key"]
            entry = registry.setdefault(
                key,
                {
                    "mock_file": capture["mock_file"],
                    "method": capture["method"],
                    "url": capture["url"],
                    "path_key": capture["path_key"],
                    "pages": [],
                },
            )
            if page_slug not in entry["pages"]:
                entry["pages"].append(page_slug)

        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def rebuild_registry_from_mock_files(app_name: str) -> dict:
    registry: dict = {}
    mock_dir = global_mock_dir(app_name)
    if not mock_dir.exists():
        return registry

    for mock_file in sorted(mock_dir.glob("*.json")):
        stem = mock_file.stem
        method, rest = stem.split("_", 1) if "_" in stem else ("get", stem)
        path_part = re.sub(r"_[0-9a-f]{8}$", "", rest)
        path = "/" + path_part.replace("_", "/")
        path_key = f"{method.upper()} {path}"
        registry[path_key] = {
            "mock_file": mock_file.name,
            "method": method.upper(),
            "url": "",
            "path_key": path_key,
            "pages": [],
        }

    global_registry_path(app_name).write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def load_or_build_registry(app_name: str) -> dict:
    registry = load_mock_registry(app_name)
    if registry:
        return registry

    registry = rebuild_registry_from_manifests(app_name)
    if registry:
        return registry

    return rebuild_registry_from_mock_files(app_name)


def load_mock_registry(app_name: str) -> dict:
    path = global_registry_path(app_name)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def rebuild_registry_from_manifests(app_name: str) -> dict:
    crawl_dir = STORAGE_DIR / app_name / "crawl"
    registry: dict = {}

    for manifest_path in crawl_dir.glob("**/api-manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        page_slug = manifest.get("page_slug", manifest_path.parent.name)
        for capture in manifest.get("captures", []):
            key = capture["registry_key"]
            entry = registry.setdefault(
                key,
                {
                    "mock_file": capture["mock_file"],
                    "method": capture["method"],
                    "url": capture["url"],
                    "path_key": capture.get(
                        "path_key",
                        mock_path_key(capture["method"], capture["url"]),
                    ),
                    "pages": [],
                },
            )
            if page_slug not in entry["pages"]:
                entry["pages"].append(page_slug)

    global_registry_path(app_name).write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def resolve_mock_file(app_name: str, registry: dict, method: str, path: str, query: str = "") -> Path | None:
    url = f"http://placeholder{path}"
    if query:
        url = f"{url}?{query}"

    exact_key = mock_registry_key(method, url)
    entry = registry.get(exact_key)
    if entry:
        mock_path = global_mock_dir(app_name) / entry["mock_file"]
        if mock_path.exists():
            return mock_path

    path_key = mock_path_key(method, url)
    for key, candidate in registry.items():
        if candidate.get("path_key") == path_key and candidate.get("method", "").upper() == method.upper():
            mock_path = global_mock_dir(app_name) / candidate["mock_file"]
            if mock_path.exists():
                return mock_path

    return None
