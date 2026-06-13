"""Registry that owns and coordinates all active BrowserSession instances."""

from __future__ import annotations

import uuid
from pathlib import Path

from sandbox.browser_session import BrowserSession
from sandbox.session_store import SESSIONS_ROOT


class SandboxManager:
    """Create, restore, query, and close browser sessions.

    Each session is an independent Playwright browser process with its own
    cookies, localStorage, and screenshot history.

    Usage (async):

        manager = SandboxManager()

        # Start a fresh session
        session = await manager.create_session()
        await manager.open(session.session_id, "https://example.com")
        path = await manager.screenshot(session.session_id)
        await manager.save_state(session.session_id)

        # Later — resume a previous session
        session = await manager.restore_session(session.session_id)

        # Cleanup
        await manager.close_all()
    """

    def __init__(self) -> None:
        self._sessions: dict[str, BrowserSession] = {}

    # ------------------------------------------------------------------
    # Session creation / restoration
    # ------------------------------------------------------------------

    async def create_session(
        self,
        session_id: str | None = None,
        storage_state_path: str | None = None,
    ) -> BrowserSession:
        """Launch a new browser and register the session.

        Args:
            session_id: Optional explicit ID. Defaults to a random UUID.
            storage_state_path: Optional path to a Playwright storage-state JSON
                to pre-load into the new browser context (e.g. an app auth.json).

        Raises `ValueError` if a session with *session_id* is already active.
        """
        sid = session_id or str(uuid.uuid4())
        if sid in self._sessions:
            raise ValueError(
                f"Session {sid!r} is already active. "
                "Call close_session() first or use a different ID."
            )
        session = BrowserSession(sid)
        await session.start(storage_state_path=storage_state_path)
        self._sessions[sid] = session
        return session

    async def restore_session(self, session_id: str) -> BrowserSession:
        """Restore a previously saved session from disk.

        Raises `KeyError` if no saved state exists for *session_id*.
        """
        if session_id in self._sessions:
            return self._sessions[session_id]
        session = BrowserSession(session_id)
        await session.restore_state()
        self._sessions[session_id] = session
        return session

    # ------------------------------------------------------------------
    # Delegated session operations
    # ------------------------------------------------------------------

    async def open(self, session_id: str, url: str) -> None:
        """Navigate the session's browser to *url*."""
        await self._get(session_id).open(url)

    async def screenshot(self, session_id: str) -> Path:
        """Capture a screenshot and return the file path."""
        return await self._get(session_id).screenshot()

    async def save_state(self, session_id: str) -> None:
        """Persist cookies and storage state for the session."""
        await self._get(session_id).save_state()

    def current_url(self, session_id: str) -> str:
        """Return the current URL of the session's page."""
        return self._get(session_id).current_url()

    # ------------------------------------------------------------------
    # Registry queries
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> BrowserSession:
        """Return the active session object. Raises `KeyError` if not found."""
        return self._get(session_id)

    def list_sessions(self) -> list[str]:
        """Return IDs of all currently active (in-memory) sessions."""
        return list(self._sessions)

    def list_saved_sessions(self) -> list[str]:
        """Return IDs of all sessions that have a saved state on disk."""
        if not SESSIONS_ROOT.exists():
            return []
        return [
            p.name
            for p in sorted(SESSIONS_ROOT.iterdir())
            if p.is_dir() and (p / "storage_state.json").exists()
        ]

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    async def close_session(self, session_id: str) -> None:
        """Save state and close the browser for one session."""
        session = self._get(session_id)
        await session.close()
        del self._sessions[session_id]

    async def close_all(self) -> None:
        """Close every active session."""
        for sid in list(self._sessions):
            try:
                await self.close_session(sid)
            except Exception as exc:
                print(f"  [sandbox] warning: failed to close {sid} — {exc}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, session_id: str) -> BrowserSession:
        if session_id not in self._sessions:
            raise KeyError(
                f"No active session {session_id!r}. "
                "Use create_session() or restore_session() first."
            )
        return self._sessions[session_id]

    def __repr__(self) -> str:
        return f"SandboxManager(active_sessions={list(self._sessions)})"
