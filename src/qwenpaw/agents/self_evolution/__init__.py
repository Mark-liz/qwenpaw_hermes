# -*- coding: utf-8 -*-
"""Self-evolution module for QwenPaw Agent.

This module provides Hermes-inspired self-evolution capabilities:
- Persistent memory stores (MEMORY.md, USER.md)
- Agent-writable skill creation/management
- Security scanning for self-created content
- Self-evolution system prompt injection

These capabilities allow the agent to accumulate knowledge and skills
across sessions, making it progressively more capable and personalized.
"""

from .memory_store import MemoryStore
from .memory_tool import create_memory_tool
from .skill_evolution_tool import create_skill_evolution_tool
from .memory_guard import scan_memory_content

__all__ = [
    "MemoryStore",
    "create_memory_tool",
    "create_skill_evolution_tool",
    "scan_memory_content",
]
