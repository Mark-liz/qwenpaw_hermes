# -*- coding: utf-8 -*-
"""Skill evolution tool for QwenPaw Agent self-evolution.

Provides a `skill_evolution` tool that allows the agent to create, edit,
patch, and delete its own skills during a session. This is the primary
self-evolution mechanism — the agent writes its own capability extensions
that persist across sessions.

Inspired by Hermes-agent's skill_manage tool, adapted to QwenPaw's
skill format (SKILL.md with YAML frontmatter).

Actions:
- create: Create a new skill with full SKILL.md content
- edit: Rewrite an existing skill's SKILL.md (major overhauls)
- patch: Targeted find-and-replace in SKILL.md (preferred for fixes)
- delete: Remove an entire skill directory

Security: All skill writes are validated by the memory guard scanner
before being persisted.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import frontmatter

from .memory_guard import scan_memory_content

logger = logging.getLogger(__name__)


def create_skill_evolution_tool(working_dir: Path):
    """Create and return the skill_evolution tool function bound to a working directory.

    Args:
        working_dir: The workspace directory where skills are stored.

    Returns:
        A callable tool function for skill evolution management.
    """
    skills_dir = working_dir / "skills"

    def skill_evolution(
        action: str,
        name: str = "",
        content: str = "",
        old_string: str = "",
        new_string: str = "",
        category: str = "",
    ) -> str:
        """Manage your own skills — create, edit, patch, or delete skill files.

        Skills are your procedural memory — reusable approaches for recurring
        task types. New skills go to the workspace skills/ directory. When you
        discover a new way to do something, solve a problem that could be
        necessary later, or complete a complex task with a repeatable pattern,
        save it as a skill so you can reuse it next time.

        ACTIONS:
        - create: Create a new skill with full SKILL.md content (+ optional category)
        - edit: Rewrite an existing skill's SKILL.md (major overhauls only)
        - patch: Targeted find-and-replace in SKILL.md (preferred for small fixes)
        - delete: Remove an entire skill directory (use with caution)

        Good skills contain: trigger conditions, numbered steps with exact
        commands, pitfalls section, and verification steps.

        Args:
            action: The action to perform. One of 'create', 'edit', 'patch', 'delete'.
            name: Skill name (lowercase, hyphens/underscores, max 64 chars).
                Must match an existing skill for edit/patch/delete.
            content: Full SKILL.md content (YAML frontmatter + markdown body).
                Required for 'create' and 'edit'.
            old_string: Text to find in SKILL.md for 'patch'. Must be unique
                unless replace_all=true. Include enough context for uniqueness.
            new_string: Replacement text for 'patch'. Can be empty to delete.
            category: Optional category for organizing skills (e.g. 'devops',
                'data-science'). Creates a subdirectory grouping. Only for 'create'.

        Returns:
            JSON string with status information.
        """
        if action not in ("create", "edit", "patch", "delete"):
            return json.dumps({
                "success": False,
                "error": (
                    f"Invalid action '{action}'. "
                    f"Must be 'create', 'edit', 'patch', or 'delete'."
                ),
            })

        if not name and action != "create":
            return json.dumps({
                "success": False,
                "error": "Skill name is required for all actions.",
            })

        # Validate skill name format
        if name and not re.match(r"^[a-z0-9][a-z0-9_-]{0,63}$", name):
            return json.dumps({
                "success": False,
                "error": (
                    f"Invalid skill name '{name}'. Must be lowercase, "
                    f"start with alphanumeric, use hyphens/underscores, max 64 chars."
                ),
            })

        # Determine skill directory
        if category and action == "create":
            skill_dir = skills_dir / category / name
        else:
            skill_dir = skills_dir / name

        skill_md_path = skill_dir / "SKILL.md"

        # ── CREATE ────────────────────────────────────────────────────
        if action == "create":
            if not content:
                return json.dumps({
                    "success": False,
                    "error": "Content (SKILL.md body) is required for 'create' action.",
                })

            if skill_dir.exists():
                return json.dumps({
                    "success": False,
                    "error": (
                        f"Skill '{name}' already exists at {skill_dir}. "
                        f"Use 'edit' or 'patch' to modify it."
                    ),
                })

            # Security scan
            scan_result = scan_memory_content(content)
            if not scan_result["safe"]:
                return json.dumps({
                    "success": False,
                    "error": f"Skill creation blocked by security scan: {scan_result['reason']}",
                })

            # Validate frontmatter
            try:
                parsed = frontmatter.loads(content)
                if not parsed.get("name"):
                    # Auto-fill name in frontmatter if missing
                    content = content.replace("---\n", f"---\nname: {name}\n", 1)
                if not parsed.get("description"):
                    return json.dumps({
                        "success": False,
                        "error": "SKILL.md must include 'description' in YAML frontmatter.",
                    })
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid SKILL.md frontmatter: {e}",
                })

            try:
                skill_dir.mkdir(parents=True, exist_ok=True)
                skill_md_path.write_text(content, encoding="utf-8")

                logger.info("Created skill '%s' at %s", name, skill_dir)
                return json.dumps({
                    "success": True,
                    "message": f"Created skill '{name}' at {skill_dir}",
                    "path": str(skill_dir),
                })
            except OSError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to create skill: {e}",
                })

        # ── EDIT ──────────────────────────────────────────────────────
        elif action == "edit":
            if not content:
                return json.dumps({
                    "success": False,
                    "error": "Content (full SKILL.md) is required for 'edit' action.",
                })

            if not skill_md_path.exists():
                return json.dumps({
                    "success": False,
                    "error": f"Skill '{name}' not found at {skill_md_path}.",
                })

            # Security scan
            scan_result = scan_memory_content(content)
            if not scan_result["safe"]:
                return json.dumps({
                    "success": False,
                    "error": f"Skill edit blocked by security scan: {scan_result['reason']}",
                })

            # Validate frontmatter
            try:
                parsed = frontmatter.loads(content)
                if not parsed.get("name") or not parsed.get("description"):
                    return json.dumps({
                        "success": False,
                        "error": "SKILL.md must include 'name' and 'description' in YAML frontmatter.",
                    })
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid SKILL.md frontmatter: {e}",
                })

            try:
                skill_md_path.write_text(content, encoding="utf-8")
                logger.info("Edited skill '%s'", name)
                return json.dumps({
                    "success": True,
                    "message": f"Updated skill '{name}' (full edit)",
                })
            except OSError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to edit skill: {e}",
                })

        # ── PATCH ─────────────────────────────────────────────────────
        elif action == "patch":
            if not old_string:
                return json.dumps({
                    "success": False,
                    "error": "old_string is required for 'patch' action.",
                })

            if not skill_md_path.exists():
                return json.dumps({
                    "success": False,
                    "error": f"Skill '{name}' not found at {skill_md_path}.",
                })

            try:
                current = skill_md_path.read_text(encoding="utf-8")
            except OSError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to read skill: {e}",
                })

            if old_string not in current:
                return json.dumps({
                    "success": False,
                    "error": f"old_string not found in skill '{name}'. "
                             f"Use exact text from the SKILL.md file.",
                })

            # Check uniqueness
            occurrences = current.count(old_string)
            if occurrences > 1:
                return json.dumps({
                    "success": False,
                    "error": (
                        f"old_string found {occurrences} times in skill '{name}'. "
                        f"Include more surrounding context to make it unique."
                    ),
                })

            new_content = current.replace(old_string, new_string, 1)

            # Security scan on the diff
            scan_result = scan_memory_content(new_string or old_string)
            if not scan_result["safe"]:
                return json.dumps({
                    "success": False,
                    "error": f"Skill patch blocked by security scan: {scan_result['reason']}",
                })

            try:
                skill_md_path.write_text(new_content, encoding="utf-8")
                logger.info("Patched skill '%s'", name)
                return json.dumps({
                    "success": True,
                    "message": f"Patched skill '{name}' (1 replacement)",
                })
            except OSError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to patch skill: {e}",
                })

        # ── DELETE ────────────────────────────────────────────────────
        elif action == "delete":
            if not skill_dir.exists():
                return json.dumps({
                    "success": False,
                    "error": f"Skill '{name}' not found at {skill_dir}.",
                })

            # Safety check: don't delete built-in skills
            builtin_marker = skill_md_path
            try:
                if skill_md_path.exists():
                    parsed = frontmatter.loads(
                        skill_md_path.read_text(encoding="utf-8")
                    )
                    meta = parsed.get("metadata", {})
                    if meta.get("builtin_skill_version"):
                        return json.dumps({
                            "success": False,
                            "error": (
                                f"Cannot delete built-in skill '{name}'. "
                                f"Disable it in skill.json instead."
                            ),
                        })
            except Exception:
                pass  # If we can't parse, allow delete

            try:
                import shutil
                shutil.rmtree(skill_dir)
                logger.info("Deleted skill '%s'", name)
                return json.dumps({
                    "success": True,
                    "message": f"Deleted skill '{name}'",
                })
            except OSError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to delete skill: {e}",
                })

    # Set function name for agentscope schema generation
    skill_evolution.__name__ = "skill_evolution"
    skill_evolution.__qualname__ = "skill_evolution"

    return skill_evolution
