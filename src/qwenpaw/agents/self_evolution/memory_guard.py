# -*- coding: utf-8 -*-
"""Memory guard — security scanner for self-evolution writes.

Scans memory and skill content for injection, exfiltration, and
destructive patterns before they are persisted. Inspired by
Hermes-agent's memory guard with adapted threat patterns.

Threat categories:
- Prompt injection: Attempts to override system instructions
- Role hijacking: Attempts to change the agent's role or identity
- Data exfiltration: Attempts to extract sensitive data via URLs or encoding
- Destructive commands: Commands that could damage the system
- Invisible unicode: Zero-width or homoglyph characters
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Threat patterns ──────────────────────────────────────────────────

_PROMPT_INJECTION_PATTERNS = [
    # System instruction overrides
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)forget\s+(all\s+)?previous\s+(instructions|rules)"),
    re.compile(r"(?i)disregard\s+(all\s+)?previous"),
    re.compile(r"(?i)you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"(?i)new\s+instructions?\s*:"),
    re.compile(r"(?i)system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>"),
    # Role manipulation
    re.compile(r"(?i)pretend\s+(you\s+are|to\s+be)"),
    re.compile(r"(?i)act\s+as\s+if\s+you"),
    re.compile(r"(?i)roleplay\s+as"),
    # Instruction injection via markdown
    re.compile(r"<!--\s*system"),
    re.compile(r"<\s*!\s*--\s*inject"),
]

_ROLE_HIJACK_PATTERNS = [
    re.compile(r"(?i)your\s+(true\s+)?identity\s+is"),
    re.compile(r"(?i)your\s+real\s+(name|purpose)\s+is"),
    re.compile(r"(?i)you\s+were\s+(actually|really)\s+designed\s+to"),
    re.compile(r"(?i)override\s+your\s+(role|persona|identity)"),
]

_EXFILTRATION_PATTERNS = [
    # Credential/secret extraction
    re.compile(r"(?i)(api[_-]?key|secret|password|token|credential)\s*[:=]\s*\S+"),
    # Data beaconing URLs
    re.compile(r"https?://[^\s]+/(exfil|steal|grab|collect|webhook)"),
    # Base64 encoded exfil
    re.compile(r"(?i)base64\s*\([^)]*encode"),
    # Environment variable dumping
    re.compile(r"(?i)environ\b.*\b(get|keys|items|values)\b"),
    re.compile(r"(?i)os\.environ\["),
]

_DESTRUCTIVE_PATTERNS = [
    # rm -rf variants
    re.compile(r"(?i)rm\s+-(?:rf|fr)\s+/"),
    re.compile(r"(?i)rm\s+-(?:rf|fr)\s+~"),
    re.compile(r"(?i)rm\s+-(?:rf|fr)\s+\*"),
    # Format/partition
    re.compile(r"(?i)mkfs\."),
    re.compile(r"(?i)dd\s+if=.*of=/dev/"),
    # Fork bomb
    re.compile(r":\(\)\{.*:\|:&\}"),
    # Shutdown/reboot
    re.compile(r"(?i)shutdown\s+(-(h|halt|now))"),
    re.compile(r"(?i)reboot"),
    # Overwrite critical files
    re.compile(r"(?i)>/etc/passwd"),
    re.compile(r"(?i)>/etc/shadow"),
]

_INVISIBLE_UNICODE_RANGES = [
    # Zero-width characters
    ("\u200b", "zero-width space (U+200B)"),
    ("\u200c", "zero-width non-joiner (U+200C)"),
    ("\u200d", "zero-width joiner (U+200D)"),
    ("\u200e", "left-to-right mark (U+200E)"),
    ("\u200f", "right-to-left mark (U+200F)"),
    ("\ufeff", "byte-order mark (U+FEFF)"),
    ("\u2060", "word joiner (U+2060)"),
    ("\u2061", "function application (U+2061)"),
    ("\u2062", "invisible times (U+2062)"),
    ("\u2063", "invisible separator (U+2063)"),
    ("\u2064", "invisible plus (U+2064)"),
    # Soft hyphen
    ("\u00ad", "soft hyphen (U+00AD)"),
]


def _check_injection_patterns(text: str) -> list[str]:
    """Check for prompt injection patterns."""
    findings = []
    for pattern in _PROMPT_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Prompt injection: matched '{match.group()[:50]}'")
    return findings


def _check_role_hijack(text: str) -> list[str]:
    """Check for role hijacking patterns."""
    findings = []
    for pattern in _ROLE_HIJACK_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Role hijack: matched '{match.group()[:50]}'")
    return findings


def _check_exfiltration(text: str) -> list[str]:
    """Check for data exfiltration patterns."""
    findings = []
    for pattern in _EXFILTRATION_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Data exfiltration: matched '{match.group()[:50]}'")
    return findings


def _check_destructive(text: str) -> list[str]:
    """Check for destructive command patterns."""
    findings = []
    for pattern in _DESTRUCTIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Destructive command: matched '{match.group()[:50]}'")
    return findings


def _check_invisible_unicode(text: str) -> list[str]:
    """Check for invisible or homoglyph unicode characters."""
    findings = []
    for char, description in _INVISIBLE_UNICODE_RANGES:
        if char in text:
            findings.append(f"Invisible unicode: {description}")
    return findings


def scan_memory_content(text: str) -> dict[str, Any]:
    """Scan memory/skill content for security threats.

    Runs all pattern checks and returns a result dict with:
    - safe: bool indicating whether the content is safe to persist
    - findings: list of threat descriptions
    - reason: human-readable summary if not safe

    Args:
        text: Content to scan.

    Returns:
        Dict with 'safe' (bool), 'findings' (list), and 'reason' (str).
    """
    all_findings = []

    all_findings.extend(_check_injection_patterns(text))
    all_findings.extend(_check_role_hijack(text))
    all_findings.extend(_check_exfiltration(text))
    all_findings.extend(_check_destructive(text))
    all_findings.extend(_check_invisible_unicode(text))

    if all_findings:
        reason = "; ".join(all_findings)
        logger.warning("Memory guard blocked content: %s", reason)
        return {
            "safe": False,
            "findings": all_findings,
            "reason": reason,
        }

    return {
        "safe": True,
        "findings": [],
        "reason": "",
    }
