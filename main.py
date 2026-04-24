# ============================================================
#  CRYSTAL AI - Main Entry Point  v2.1
#  Run: python main.py
# ============================================================

import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import get_logger
from src.utils.config_loader import get
from src.core.brain import Brain
from src.voice.speaker import Speaker
from src.voice.listener import Listener
from src.gui.window import Window

log = get_logger("main")

LOGO = r"""
   ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗
  ██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║
  ██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║
  ██║     ██╔══██╗  ╚██╔╝  ╚════██║   ██║   ██╔══██║██║
  ╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗
   ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
        Personal AI Companion  //  by Renzo  //  v2.1
"""


def main():
    print("\033[96m" + LOGO + "\033[0m")
    print("\033[90m" + "─" * 62 + "\033[0m\n")

    # ── 1. Check Ollama ───────────────────────────────────────
    log.info("Checking Ollama connection...")
    brain = Brain()
    if not brain.is_online():
        log.error("Ollama is not running or mistral:7b not found!")
        log.error("Run:  ollama pull mistral:7b")
        sys.exit(1)
    log.info("Ollama connected ✓")
    from src.control.pc_control import APP_ALIASES
    log.info(f"PC Control ready ✓  ({len(APP_ALIASES)} app aliases loaded)")

    # ── 2. Speaker ────────────────────────────────────────────
    log.info("Loading speaker (Piper TTS)...")
    try:
        speaker = Speaker()
        log.info("Speaker ready ✓")
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    # ── 3. Listener ───────────────────────────────────────────
    log.info("Loading listener (faster-whisper)...")
    listener = Listener()
    log.info("Listener ready ✓")

    # ── 4. Web UI ─────────────────────────────────────────────
    log.info("Launching web UI at http://localhost:5000 ...")
    window = Window(brain=brain, speaker=speaker, listener=listener)

    # Greet Renzo on startup
    def greet():
        greeting = brain.think(
            "Greet Renzo. Mention you're ready to chat AND control his PC. "
            "Keep it to 2 sentences max."
        )
        speaker.speak(greeting)

    threading.Thread(target=greet, daemon=True).start()

    # ── 5. Start ──────────────────────────────────────────────
    log.info("Crystal is online! 🚀")
    window.run()


if __name__ == "__main__":
    main()