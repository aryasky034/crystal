# ============================================================
#  CRYSTAL AI - Status Bar
#  Shows Crystal's current state (listening, thinking, speaking)
# ============================================================

import tkinter as tk
from src.utils.config_loader import get

# Status definitions: (label, color)
STATES = {
    "idle":      ("● IDLE",      "#3a4a60"),
    "listening": ("● LISTENING", "#00ff9d"),
    "thinking":  ("● THINKING",  "#38bdf8"),
    "speaking":  ("● SPEAKING",  "#f472b6"),
    "error":     ("● ERROR",     "#ff4444"),
}


class StatusBar(tk.Frame):
    def __init__(self, parent):
        font_family = get("gui", "font_family", "Consolas")

        super().__init__(parent, bg="#070b12", pady=6)

        self.label = tk.Label(
            self,
            text="● IDLE",
            fg="#3a4a60",
            bg="#070b12",
            font=(font_family, 10, "bold"),
        )
        self.label.pack(side=tk.LEFT, padx=16)

        # Crystal name on the right
        tk.Label(
            self,
            text="CRYSTAL AI  v2.0",
            fg="#1a2a3a",
            bg="#070b12",
            font=(font_family, 9),
        ).pack(side=tk.RIGHT, padx=16)

    def set_state(self, state: str):
        """Update the status indicator. State: idle | listening | thinking | speaking | error"""
        label, color = STATES.get(state, STATES["idle"])
        self.label.config(text=label, fg=color)
        self.update()