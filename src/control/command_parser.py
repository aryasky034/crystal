# ============================================================
#  CRYSTAL AI - Command Parser
#  src/control/command_parser.py
#
#  Sits between the user's message and the brain.
#  If the message is a PC command, it intercepts it and runs
#  PCControl directly — no LLM call needed, instant response.
#  If it's a normal question, it passes through to Brain.
#
#  This keeps Crystal fast:
#    "open spotify"  → instant (no Ollama call)
#    "what is servo PWM?" → goes to Mistral as normal
# ============================================================

import re
from src.utils.logger import get_logger

log = get_logger(__name__)

# ── PC COMMAND TRIGGER PATTERNS ──────────────────────────────
# If any of these match, we route to PCControl instead of Brain

PC_PATTERNS = [
    # Apps
    r"\bopen\b.{1,40}",
    r"\bclose\b.{1,40}",
    r"\blaunch\b.{1,40}",
    r"\bstart\b.{1,30}",

    # Volume
    r"\b(mute|unmute)\b",
    r"\bvolume\b",
    r"\b(louder|quieter|louder|softer)\b",

    # Screenshot
    r"\bscreenshot\b",
    r"\bscreen\s*shot\b",
    r"\bcapture\s+(?:my\s+)?screen\b",

    # Clipboard
    r"\bclipboard\b",

    # System
    r"\block\s+(?:the\s+)?(?:screen|pc|computer)\b",
    r"\b(?:shut\s*down|shutdown|power\s+off)\b",
    r"\b(?:restart|reboot)\b",
    r"\bput\s+(?:the\s+)?(?:pc|computer)\s+to\s+sleep\b",
    r"\bgo\s+to\s+sleep\b",

    # Windows
    r"\b(minimize|maximise|maximize)\b",
    r"\balt.?tab\b",
    r"\bswitch\s+(app|window|tab)\b",

    # Files & web
    r"\bopen\s+(?:the\s+)?(?:file|folder)\b",
    r"\bopen\s+https?://",
    r"\bgo\s+to\s+(?:https?://|\w+\.(?:com|org|net|io|dev))\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in PC_PATTERNS]


def is_pc_command(text: str) -> bool:
    """Return True if this message should be routed to PCControl."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return True
    return False


def parse_and_execute(text: str, pc_control) -> str | None:
    """
    If text is a PC command, execute it and return the result string.
    If not a PC command, return None (caller should use Brain).
    """
    if not is_pc_command(text):
        return None

    log.info(f"PC command detected: '{text}'")
    result = pc_control.execute(text)
    log.info(f"PC command result: '{result}'")
    return result