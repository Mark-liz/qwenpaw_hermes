# -*- coding: utf-8 -*-
"""Memory tool for QwenPaw Agent self-evolution.

Provides a `memory` tool that the agent can call to persist knowledge
across sessions. This is inspired by Hermes-agent's memory system.

Two memory targets:
- 'memory': Agent's personal notes (env facts, conventions, tool quirks)
- 'user': What the agent knows about the user (preferences, style)

Actions:
- add: Add a new entry
- replace: Replace an existing entry (identified by old_text)
- remove: Remove an existing entry (identified by old_text)

All writes are validated by the memory guard before being persisted.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .memory_store import MemoryStore
from .memory_guard import scan_memory_content

logger = logging.getLogger(__name__)


def create_memory_tool(working_dir: Path):
    """Create and return the memory tool function bound to a working directory.

    The returned function conforms to agentscope's tool function interface
    (decorated with type hints and docstrings for schema generation).

    Args:
        working_dir: The workspace directory for memory file storage.

    Returns:
        A callable tool function for memory management.
    """
    store = MemoryStore(working_dir)

    def memory(
        action: str,
        content: str = "",
        old_text: str = "",
        target: str = "memory",
    ) -> str:
        """Save durable information to persistent memory that survives across sessions.

        Memory is injected into future turns, so keep it compact and focused on facts
        that will still matter later. Prioritize what reduces future user steering —
        the most valuable memory is one that prevents the user from having to correct
        or remind you again. User preferences and recurring corrections matter more
        than procedural task details.

        Do NOT save task progress, session outcomes, completed-work logs, or temporary
        TODO state to memory. If you've discovered a new way to do something, solved a
        problem that could be necessary later, save it as a skill instead.

        TWO TARGETS:
        - 'memory': your notes — environment facts, project conventions, tool quirks,
          lessons learned
        - 'user': who the user is — name, role, preferences, communication style,
          pet peeves

        ACTIONS: add (new entry), replace (update existing — old_text identifies it),
        remove (delete — old_text identifies it).

        SKIP: trivial/obvious info, things easily re-discovered, raw data dumps,
        and temporary task state.

        Args:
            action: The action to perform. One of 'add', 'replace', 'remove'.
            content: The entry content. Required for 'add' and 'replace'.
            old_text: Short unique substring identifying the entry to replace or remove.
            target: Which memory store: 'memory' for personal notes, 'user' for user profile.

        Returns:
            JSON string with status information.
        """
        if action not in ("add", "replace", "remove"):
            return json.dumps({
                "success": False,
                "error": f"Invalid action '{action}'. Must be 'add', 'replace', or 'remove'.",
            })

        if target not in ("memory", "user"):
            return json.dumps({
                "success": False,
                "error": f"Invalid target '{target}'. Must be 'memory' or 'user'.",
            })

        if action == "add" and not content:
            return json.dumps({
                "success": False,
                "error": "Content is required for 'add' action.",
            })

        if action in ("replace", "remove") and not old_text:
            return json.dumps({
                "success": False,
                "error": f"old_text is required for '{action}' action.",
            })

        if action == "replace" and not content and content != "":
            # Allow empty string for replace (effectively same as remove but explicit)
            return json.dumps({
                "success": False,
                "error": "Content is required for 'replace' action.",
            })

        # Security scan before any write
        text_to_scan = content if action == "add" else (
            content if action == "replace" else old_text
        )
        scan_result = scan_memory_content(text_to_scan)
        if not scan_result["safe"]:
            return json.dumps({
                "success": False,
                "error": f"Memory write blocked by security scan: {scan_result['reason']}",
            })

        try:
            if target == "memory":
                if action == "add":
                    result = store.add_memory_entry(content)
                elif action == "replace":
                    result = store.replace_memory_entry(old_text, content)
                elif action == "remove":
                    result = store.remove_memory_entry(old_text)
            else:  # user
                if action == "add":
                    result = store.add_user_entry(content)
                elif action == "replace":
                    result = store.replace_user_entry(old_text, content)
                elif action == "remove":
                    result = store.remove_user_entry(old_text)

            return json.dumps({
                "success": True,
                "message": result,
            })

        except ValueError as e:
            return json.dumps({
                "success": False,
                "error": str(e),
            })
        except Exception as e:
            logger.error("Memory tool error: %s", e, exc_info=True)
            return json.dumps({
                "success": False,
                "error": f"Internal error: {e}",
            })

    # Set function name and docstring for agentscope schema generation
    memory.__name__ = "memory"
    memory.__qualname__ = "memory"

    return memory
