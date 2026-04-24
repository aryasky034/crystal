# ============================================================
#  CRYSTAL AI - Brain  v2.1
#
#  Model: Mistral 7B via Ollama
#
#  New in v2.1:
#  - PC Control routing: if user says "open spotify" or
#    "take a screenshot", it goes to PCControl directly
#    without an Ollama call — instant response
#  - Still falls back to Mistral for everything else
# ============================================================

import atexit
import ollama
from src.utils.config_loader import get
from src.core.memory import Memory
from src.core.personality import get_system_prompt, detect_emotion
from src.control.pc_control import PCControl
from src.control.command_parser import parse_and_execute
from src.utils.logger import get_logger

log = get_logger(__name__)


class Brain:
    def __init__(self):
        self.model       = get("brain", "model",       "mistral:7b")
        self.host        = get("brain", "host",        "http://localhost:11434")
        self.temperature = get("brain", "temperature", 0.7)

        self.memory     = Memory()
        self.client     = ollama.Client(host=self.host)
        self.pc         = PCControl()

        log.info(f"Brain online — model: {self.model}")
        log.info(f"Memory: {self.memory.message_count()} messages, "
                 f"{len(self.memory.get_all_facts())} long-term facts")

        atexit.register(self._save_exit_summary)

    # ── MAIN INTERFACE ────────────────────────────────────────

    def think(self, user_input: str) -> str:
        """
        Process user input. Routes to PCControl if it's a
        system command, otherwise calls Mistral.
        """
        # ── Try PC command first (no LLM call, instant) ──────
        pc_result = parse_and_execute(user_input, self.pc)
        if pc_result is not None:
            # Save to memory so Crystal has context of what she did
            self.memory.add("user",      user_input)
            self.memory.add("assistant", pc_result)
            return pc_result

        # ── Normal conversation → Mistral ────────────────────
        self.memory.add("user", user_input)

        emotion = detect_emotion(user_input)

        tokens = self.memory.session_token_estimate()
        if tokens > 20000:
            log.warning(f"Large context: ~{tokens} tokens")

        messages = [
            {
                "role":    "system",
                "content": get_system_prompt(
                    long_term_facts=self.memory.get_all_facts(),
                    emotion=emotion
                )
            }
        ] + self.memory.get_context()

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": self.temperature},
                stream=False,
            )
            full_response = response["message"]["content"]
        except Exception as e:
            log.error(f"Ollama error: {e}")
            full_response = "Sorry, I had a brain glitch. Can you say that again?"

        self.memory.add("assistant", full_response)
        return full_response

    # ── MEMORY HELPERS ────────────────────────────────────────

    def remember(self, key: str, value: str):
        self.memory.remember(key, value, category="manual")

    def forget(self, key: str):
        self.memory.forget(key)

    def what_do_you_know(self) -> str:
        facts = self.memory.get_all_facts()
        summaries_text = self.memory.get_context_summary_text()
        lines = ["=== LONG-TERM FACTS ==="]
        for key, val in facts.items():
            lines.append(f"  {key}: {val['value']}  [{val.get('category','?')}]")
        lines += ["\n=== SESSION SUMMARIES ===", summaries_text,
                  f"\n=== SESSION STATS ===",
                  f"  Messages: {self.memory.message_count()}",
                  f"  ~Tokens:  {self.memory.session_token_estimate()}"]
        return "\n".join(lines)

    # ── STATUS ────────────────────────────────────────────────

    def is_online(self) -> bool:
        try:
            models = self.client.list()
            available = [m.model for m in models.models]
            return any("mistral" in m for m in available)
        except Exception:
            return False

    # ── SHUTDOWN ─────────────────────────────────────────────

    def _save_exit_summary(self):
        if self.memory.message_count() < 4:
            return
        try:
            log.info("Saving session summary...")
            msgs = self.memory.session_messages[-30:]
            transcript = "\n".join(
                f"{'Renzo' if m['role']=='user' else 'Crystal'}: {m['content'][:200]}"
                for m in msgs
            )
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content":
                    f"Summarise this conversation in 2-3 sentences. Be specific — "
                    f"include project names, goals, and key facts.\n\n{transcript}"}],
                options={"temperature": 0.3},
                stream=False,
            )
            summary = response["message"]["content"].strip()
            self.memory.save_session_summary(summary)
            log.info(f"Summary saved: {summary[:80]}...")
        except Exception as e:
            log.warning(f"Could not save session summary: {e}")