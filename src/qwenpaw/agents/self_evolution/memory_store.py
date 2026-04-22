# -*- coding: utf-8 -*-
"""Persistent memory stores for self-evolution.

Implements the Hermes-style bounded, file-backed memory pattern:
- MEMORY.md: Agent's personal notes (env facts, conventions, tool quirks)
- USER.md: What the agent knows about the user (preferences, style)

Memory is loaded at session start as a frozen snapshot injected into the
system prompt. Mid-session writes update disk immediately but do NOT
change the system prompt snapshot — this preserves prompt caching and
avoids confusing the agent with a shifting system prompt.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

logger = logging.getLogger(__name__)

# Character limits for each store
MEMORY_MAX_CHARS = 2200
USER_MAX_CHARS = 1375

# Entry delimiter
ENTRY_DELIMITER = "§"


class MemoryStore:
    """Bounded, file-backed persistent memory store.

    Two stores are maintained:
    - MEMORY.md: Agent personal notes (env facts, project conventions, tool quirks)
    - USER.md: User profile (preferences, communication style, habits)

    Thread-safe via file locking (fcntl on Unix, msvcrt on Windows).
    """

    def __init__(self, working_dir: Path):
        """Initialize memory store.

        Args:
            working_dir: The workspace directory where memory files are stored.
        """
        self._working_dir = working_dir
        self._memory_path = working_dir / "MEMORY.md"
        self._user_path = working_dir / "USER.md"

    @property
    def memory_path(self) -> Path:
        """Path to MEMORY.md."""
        return self._memory_path

    @property
    def user_path(self) -> Path:
        """Path to USER.md."""
        return self._user_path

    def _read_file(self, path: Path) -> str:
        """Read file content, returning empty string if not found."""
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read memory file %s: %s", path, e)
            return ""

    def _write_file_atomic(self, path: Path, content: str) -> None:
        """Write content to file atomically using temp file + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent),
                prefix=".memory_",
                suffix=".tmp",
            )
            try:
                os.write(fd, content.encode("utf-8"))
                os.close(fd)
                os.replace(tmp_path, str(path))
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Failed to write memory file %s: %s", path, e)
            raise

    def _acquire_lock(self, path: Path):
        """Acquire file lock (context manager support via _FileLock)."""
        return _FileLock(path)

    # ── MEMORY.md (agent notes) ──────────────────────────────────────

    def read_memory(self) -> str:
        """Read MEMORY.md content.

        Returns:
            Memory content string, empty if not found.
        """
        return self._read_file(self._memory_path)

    def write_memory(self, content: str) -> None:
        """Write MEMORY.md content, enforcing character limit.

        Args:
            content: New content to write.

        Raises:
            ValueError: If content exceeds MEMORY_MAX_CHARS.
        """
        if len(content) > MEMORY_MAX_CHARS:
            raise ValueError(
                f"MEMORY.md content ({len(content)} chars) exceeds "
                f"limit ({MEMORY_MAX_CHARS} chars). "
                f"Remove old entries before adding new ones."
            )
        with self._acquire_lock(self._memory_path):
            self._write_file_atomic(self._memory_path, content)

    def add_memory_entry(self, entry: str) -> str:
        """Add a new entry to MEMORY.md.

        Entries are delimited by the section sign character.
        If the total content would exceed the limit, the oldest entries
        are removed to make room.

        Args:
            entry: New entry to add.

        Returns:
            Status message.
        """
        current = self.read_memory()
        if current:
            new_content = current.rstrip() + "\n" + ENTRY_DELIMITER + "\n" + entry
        else:
            new_content = entry

        # Trim oldest entries if over limit
        new_content = self._trim_to_fit(new_content, MEMORY_MAX_CHARS)

        with self._acquire_lock(self._memory_path):
            self._write_file_atomic(self._memory_path, new_content)

        return f"Added memory entry. MEMORY.md is now {len(new_content)}/{MEMORY_MAX_CHARS} chars."

    def replace_memory_entry(self, old_text: str, new_text: str) -> str:
        """Replace a specific entry in MEMORY.md.

        Args:
            old_text: Unique substring identifying the entry to replace.
            new_text: Replacement text.

        Returns:
            Status message.

        Raises:
            ValueError: If old_text not found or result exceeds limit.
        """
        current = self.read_memory()
        if old_text not in current:
            raise ValueError(
                f"Text not found in MEMORY.md: {old_text[:50]}..."
            )

        new_content = current.replace(old_text, new_text, 1)
        if len(new_content) > MEMORY_MAX_CHARS:
            raise ValueError(
                f"Replacement would exceed MEMORY.md limit "
                f"({len(new_content)}/{MEMORY_MAX_CHARS} chars)."
            )

        with self._acquire_lock(self._memory_path):
            self._write_file_atomic(self._memory_path, new_content)

        return f"Replaced memory entry. MEMORY.md is now {len(new_content)}/{MEMORY_MAX_CHARS} chars."

    def remove_memory_entry(self, old_text: str) -> str:
        """Remove a specific entry from MEMORY.md.

        Args:
            old_text: Unique substring identifying the entry to remove.

        Returns:
            Status message.

        Raises:
            ValueError: If old_text not found.
        """
        current = self.read_memory()
        if old_text not in current:
            raise ValueError(
                f"Text not found in MEMORY.md: {old_text[:50]}..."
            )

        new_content = current.replace(old_text, "", 1)
        # Clean up double newlines left by removal
        new_content = new_content.replace("\n\n\n", "\n\n").strip()

        with self._acquire_lock(self._memory_path):
            self._write_file_atomic(self._memory_path, new_content)

        return f"Removed memory entry. MEMORY.md is now {len(new_content)}/{MEMORY_MAX_CHARS} chars."

    # ── USER.md (user profile) ───────────────────────────────────────

    def read_user(self) -> str:
        """Read USER.md content.

        Returns:
            User profile content string, empty if not found.
        """
        return self._read_file(self._user_path)

    def write_user(self, content: str) -> None:
        """Write USER.md content, enforcing character limit.

        Args:
            content: New content to write.

        Raises:
            ValueError: If content exceeds USER_MAX_CHARS.
        """
        if len(content) > USER_MAX_CHARS:
            raise ValueError(
                f"USER.md content ({len(content)} chars) exceeds "
                f"limit ({USER_MAX_CHARS} chars). "
                f"Remove old entries before adding new ones."
            )
        with self._acquire_lock(self._user_path):
            self._write_file_atomic(self._user_path, content)

    def add_user_entry(self, entry: str) -> str:
        """Add a new entry to USER.md.

        Args:
            entry: New entry to add.

        Returns:
            Status message.
        """
        current = self.read_user()
        if current:
            new_content = current.rstrip() + "\n" + ENTRY_DELIMITER + "\n" + entry
        else:
            new_content = entry

        new_content = self._trim_to_fit(new_content, USER_MAX_CHARS)

        with self._acquire_lock(self._user_path):
            self._write_file_atomic(self._user_path, new_content)

        return f"Added user entry. USER.md is now {len(new_content)}/{USER_MAX_CHARS} chars."

    def replace_user_entry(self, old_text: str, new_text: str) -> str:
        """Replace a specific entry in USER.md.

        Args:
            old_text: Unique substring identifying the entry to replace.
            new_text: Replacement text.

        Returns:
            Status message.
        """
        current = self.read_user()
        if old_text not in current:
            raise ValueError(
                f"Text not found in USER.md: {old_text[:50]}..."
            )

        new_content = current.replace(old_text, new_text, 1)
        if len(new_content) > USER_MAX_CHARS:
            raise ValueError(
                f"Replacement would exceed USER.md limit "
                f"({len(new_content)}/{USER_MAX_CHARS} chars)."
            )

        with self._acquire_lock(self._user_path):
            self._write_file_atomic(self._user_path, new_content)

        return f"Replaced user entry. USER.md is now {len(new_content)}/{USER_MAX_CHARS} chars."

    def remove_user_entry(self, old_text: str) -> str:
        """Remove a specific entry from USER.md.

        Args:
            old_text: Unique substring identifying the entry to remove.

        Returns:
            Status message.
        """
        current = self.read_user()
        if old_text not in current:
            raise ValueError(
                f"Text not found in USER.md: {old_text[:50]}..."
            )

        new_content = current.replace(old_text, "", 1)
        new_content = new_content.replace("\n\n\n", "\n\n").strip()

        with self._acquire_lock(self._user_path):
            self._write_file_atomic(self._user_path, new_content)

        return f"Removed user entry. USER.md is now {len(new_content)}/{USER_MAX_CHARS} chars."

    # ── Snapshot for system prompt ───────────────────────────────────

    def get_snapshot(self) -> str:
        """Get a frozen snapshot of all memory for system prompt injection.

        This snapshot is loaded once at session start and does not change
        within the session, even if memory files are updated. This preserves
        prompt caching and prevents confusion from shifting system prompts.

        Returns:
            Formatted memory snapshot string for system prompt.
        """
        parts = []

        memory_content = self.read_memory()
        if memory_content:
            usage_pct = len(memory_content) * 100 // MEMORY_MAX_CHARS
            parts.append(
                f"══════════════════════════════════════════════\n"
                f"MEMORY (your personal notes) [{usage_pct}% — "
                f"{len(memory_content)}/{MEMORY_MAX_CHARS} chars]\n"
                f"══════════════════════════════════════════════\n"
                f"{memory_content}\n"
            )

        user_content = self.read_user()
        if user_content:
            usage_pct = len(user_content) * 100 // USER_MAX_CHARS
            parts.append(
                f"══════════════════════════════════════════════\n"
                f"USER PROFILE (what you know about the user) "
                f"[{usage_pct}% — {len(user_content)}/{USER_MAX_CHARS} chars]\n"
                f"══════════════════════════════════════════════\n"
                f"{user_content}\n"
            )

        return "\n".join(parts) if parts else ""

    # ── Utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _trim_to_fit(content: str, max_chars: int) -> str:
        """Trim content to fit within character limit by removing oldest entries.

        Entries are split by the delimiter and removed from the top
        until the content fits.

        Args:
            content: Content to potentially trim.
            max_chars: Maximum allowed character count.

        Returns:
            Trimmed content that fits within the limit.
        """
        if len(content) <= max_chars:
            return content

        entries = content.split(ENTRY_DELIMITER)

        # Remove entries from the beginning (oldest) until we fit
        while len(entries) > 1 and len(ENTRY_DELIMITER.join(entries)) > max_chars:
            entries.pop(0)

        result = ENTRY_DELIMITER.join(entries)
        if len(result) > max_chars:
            # Last resort: truncate
            result = result[:max_chars]

        return result


class _FileLock:
    """Simple file-based lock using fcntl (Unix) or msvcrt (Windows)."""

    def __init__(self, path: Path):
        self._path = path
        self._lock_path = path.with_suffix(".lock")
        self._fd = None

    def __enter__(self):
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self._lock_path, "w")  # noqa: SIM115

        if fcntl is not None:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            msvcrt.locking(self._fd.fileno(), msvcrt.LK_LOCK, 1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if fcntl is not None:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            if self._fd:
                self._fd.close()
            try:
                self._lock_path.unlink(missing_ok=True)
            except OSError:
                pass
        return False
