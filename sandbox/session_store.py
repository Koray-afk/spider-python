"""Disk I/O for a single sandbox session — no Playwright dependency."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_ROOT = Path("sandbox") / "sessions"


class SessionStore:
    """Manages all file I/O for one sandbox session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.session_dir = SESSIONS_ROOT / session_id
        self.screenshots_dir = self.session_dir / "screenshots"

    def ensure_dirs(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    # --- metadata ---

    @property
    def metadata_path(self) -> Path:
        return self.session_dir / "metadata.json"

    def save_metadata(self, meta: dict) -> None:
        self.ensure_dirs()
        self.metadata_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_metadata(self) -> dict:
        if not self.metadata_path.exists():
            return {}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    # --- cookies ---

    @property
    def cookies_path(self) -> Path:
        return self.session_dir / "cookies.json"

    def save_cookies(self, cookies: list) -> None:
        self.ensure_dirs()
        self.cookies_path.write_text(
            json.dumps(cookies, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_cookies(self) -> list:
        if not self.cookies_path.exists():
            return []
        return json.loads(self.cookies_path.read_text(encoding="utf-8"))

    # --- storage state (written directly by Playwright) ---

    @property
    def storage_state_path(self) -> Path:
        return self.session_dir / "storage_state.json"

    def has_storage_state(self) -> bool:
        return self.storage_state_path.exists()

    # --- screenshots ---

    def screenshot_path(self, ts: str | None = None) -> Path:
        self.ensure_dirs()
        if ts is None:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        return self.screenshots_dir / f"{ts}.png"

    def list_screenshots(self) -> list[Path]:
        if not self.screenshots_dir.exists():
            return []
        return sorted(self.screenshots_dir.glob("*.png"))
