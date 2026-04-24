# ============================================================
#  CRYSTAL AI - Memory System  v2.0
#
#  Three-layer memory architecture:
#
#  LAYER 1 — SHORT-TERM  (session_messages)
#    Raw conversation messages for the current session.
#    The last N are passed directly to Mistral as context.
#
#  LAYER 2 — LONG-TERM   (long_term.json)
#    Persistent facts about Renzo: name, projects, goals,
#    preferences, tools, etc. Auto-detected from every user
#    message via regex patterns, plus explicitly stored.
#    Injected into the system prompt on EVERY call.
#
#  LAYER 3 — SESSION SUMMARIES  (summaries.json)
#    When a session ends or grows too long, a compressed
#    summary is saved. Next session Crystal reads it back
#    and injects it as a "recap" at the top of context —
#    giving her true cross-session memory.
# ============================================================

import json
import os
import re
from datetime import datetime
from src.utils.config_loader import get


# ── FACT DETECTION PATTERNS ──────────────────────────────────
MEMORY_PATTERNS = [
    # Projects & builds
    (r"i(?:'m| am) (?:building|working on|making|creating|developing) (.+)",       "project"),
    (r"(?:my|our) (?:new )?project (?:is|called|named) (.+)",                      "project"),
    (r"i(?:'m| am) (?:trying to|going to|planning to) (?:build|make|create) (.+)", "project"),

    # Goals
    (r"(?:my goal is|i want to|i need to|i have to) (.+)", "goal"),
    (r"i(?:'m| am) (?:trying to) (.+)",                     "goal"),

    # Personal info
    (r"(?:my name is|i(?:'m| am) called) ([a-zA-Z]+)",  "name"),
    (r"i(?:'m| am) (\d+) years old",                     "age"),
    (r"i(?:'m| am) from ([a-zA-Z ,]+)",                  "location"),
    (r"i(?:'m| am) (?:a |an )(.+?)(?:\.|,|$)",           "occupation"),
    (r"i (?:study|go to|attend) (.+)",                   "school"),

    # Preferences & dislikes
    (r"i (?:really )?(?:love|like|enjoy|prefer) (.+)",   "preference"),
    (r"my favorite (.+?) is (.+)",                        "favorite"),
    (r"i (?:really )?(?:hate|dislike|don't like) (.+)",  "dislike"),

    # Tech stack
    (r"i(?:'m| am) using (.+?) (?:for|to)",              "tool"),
    (r"i (?:use|run|installed) (.+?) (?:on|for|as)",     "tool"),
    (r"my (?:pc|computer|machine|laptop) (?:has|is|runs) (.+)", "hardware"),

    # Dates & events
    (r"(?:my deadline|due date) (?:is|for .+? is) (.+)",        "deadline"),
    (r"i have (?:an exam|a test|a meeting|an interview) (.+)",   "event"),
    (r"(?:tomorrow|next week|on \w+day) i (?:have|need to|will) (.+)", "upcoming"),
]


class Memory:
    def __init__(self):
        self.chat_history_path = get("memory", "chat_history_path",  "data/memory/chat_history.json")
        self.long_term_path    = get("memory", "long_term_path",     "data/memory/long_term.json")
        self.summaries_path    = get("memory", "summaries_path",     "data/memory/summaries.json")
        self.max_context       = get("brain",  "max_context_messages", 20)
        self.max_history       = get("memory", "max_history_size",   500)
        self.summary_threshold = get("memory", "summary_threshold",  60)

        self.session_messages: list = []
        self._load_history()

    # ── PUBLIC API ────────────────────────────────────────────

    def add(self, role: str, content: str):
        """Add a message to session memory and persist it."""
        self.session_messages.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat()
        })
        if role == "user":
            self._auto_detect_facts(content)
        self._save_history()

        # Auto-compress when session gets very long
        if len(self.session_messages) >= self.summary_threshold:
            self._compress_old_messages()

    def get_context(self) -> list:
        """
        Build the full context list for Mistral.

        Structure returned:
          [optional recap inject]  ← previous sessions
          [last N raw messages]    ← current session
        """
        recent = self.session_messages[-self.max_context:]
        raw = [{"role": m["role"], "content": m["content"]} for m in recent]

        summaries = self._load_summaries()
        if summaries:
            # Take the last 5 session summaries, join them into one recap
            recap_lines = [f"[{s['date']}] {s['summary']}" for s in summaries[-5:]]
            recap_text = (
                "Recap of our previous conversations:\n"
                + "\n".join(recap_lines)
            )
            # Inject as a fake Q&A pair so Mistral reads it as
            # established knowledge, not a new instruction
            injected = [
                {"role": "user",      "content": "Do you remember our previous conversations?"},
                {"role": "assistant", "content": recap_text},
            ]
            return injected + raw

        return raw

    def get_context_summary_text(self) -> str:
        """Human-readable summary of what Crystal remembers — for debug/UI."""
        summaries = self._load_summaries()
        if not summaries:
            return "No previous session history."
        return "\n".join(f"• [{s['date']}] {s['summary']}" for s in summaries[-10:])

    def clear_session(self):
        """Wipe in-memory messages (does NOT delete disk files)."""
        self.session_messages = []

    def remember(self, key: str, value: str, category: str = "manual"):
        """Explicitly store a long-term fact."""
        data = self._load_long_term()
        data[key] = {
            "value":    value,
            "category": category,
            "updated":  datetime.now().isoformat()
        }
        self._save_long_term(data)

    def forget(self, key: str):
        """Remove a specific long-term fact."""
        data = self._load_long_term()
        if key in data:
            del data[key]
            self._save_long_term(data)

    def recall(self, key: str) -> str | None:
        """Get a single long-term fact."""
        entry = self._load_long_term().get(key)
        return entry["value"] if entry else None

    def get_all_facts(self) -> dict:
        """All long-term facts — injected into system prompt."""
        return self._load_long_term()

    def get_facts_by_category(self, category: str) -> dict:
        return {k: v for k, v in self._load_long_term().items()
                if v.get("category") == category}

    def save_session_summary(self, summary_text: str):
        """
        Persist a summary of this session.
        Called by Brain on shutdown / manual trigger.
        """
        summaries = self._load_summaries()
        summaries.append({
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary":   summary_text,
            "msg_count": len(self.session_messages)
        })
        self._save_summaries(summaries[-20:])  # keep last 20

    def message_count(self) -> int:
        return len(self.session_messages)

    def session_token_estimate(self) -> int:
        """Rough token estimate (~4 chars per token)."""
        return sum(len(m["content"]) for m in self.session_messages) // 4

    # ── PRIVATE — FACT DETECTION ─────────────────────────────

    def _auto_detect_facts(self, text: str):
        """Scan a user message for facts and save silently."""
        text_lower = text.lower().strip()
        data = self._load_long_term()
        updated = False

        for pattern, category in MEMORY_PATTERNS:
            match = re.search(pattern, text_lower)
            if not match:
                continue

            # Handle patterns with 2 capture groups (e.g. "favorite X is Y")
            value = (
                f"{match.group(1)}: {match.group(2)}".strip()
                if match.lastindex == 2
                else match.group(1).strip().rstrip(".,!?")
            )

            if len(value) < 3 or len(value) > 200:
                continue

            key = f"{category}:{value[:40]}"
            if key not in data:
                data[key] = {
                    "value":    value,
                    "category": category,
                    "updated":  datetime.now().isoformat()
                }
                updated = True

        if updated:
            self._save_long_term(data)

    # ── PRIVATE — SESSION COMPRESSION ────────────────────────

    def _compress_old_messages(self):
        """
        Trim the oldest half of session_messages into a summary
        so the context window never bloats.
        The trimmed content is saved to summaries.json permanently.
        """
        half = len(self.session_messages) // 2
        old  = self.session_messages[:half]
        self.session_messages = self.session_messages[half:]

        lines = []
        for m in old[:10]:          # cap snippet at 10 messages
            role    = "Renzo" if m["role"] == "user" else "Crystal"
            snippet = m["content"][:150] + "..." if len(m["content"]) > 150 else m["content"]
            lines.append(f"{role}: {snippet}")

        self.save_session_summary(
            f"Earlier this session ({len(old)} msgs): " + " | ".join(lines)
        )
        self._save_history()

    # ── PRIVATE — FILE I/O ────────────────────────────────────

    def _load_history(self):
        if os.path.exists(self.chat_history_path):
            try:
                with open(self.chat_history_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.session_messages = json.loads(content)
            except (json.JSONDecodeError, KeyError):
                self.session_messages = []
        else:
            self.session_messages = []

    def _save_history(self):
        trimmed = self.session_messages[-self.max_history:]
        os.makedirs(os.path.dirname(self.chat_history_path), exist_ok=True)
        with open(self.chat_history_path, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2, ensure_ascii=False)

    def _load_long_term(self) -> dict:
        if os.path.exists(self.long_term_path):
            try:
                with open(self.long_term_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return json.loads(content) if content else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_long_term(self, data: dict):
        os.makedirs(os.path.dirname(self.long_term_path), exist_ok=True)
        with open(self.long_term_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_summaries(self) -> list:
        if os.path.exists(self.summaries_path):
            try:
                with open(self.summaries_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return json.loads(content) if content else []
            except json.JSONDecodeError:
                return []
        return []

    def _save_summaries(self, data: list):
        os.makedirs(os.path.dirname(self.summaries_path), exist_ok=True)
        with open(self.summaries_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)