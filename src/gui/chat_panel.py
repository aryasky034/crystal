# ============================================================
#  CRYSTAL AI - Chat Panel
#  Displays the conversation between user and Crystal
# ============================================================

import tkinter as tk
from src.utils.config_loader import get


class ChatPanel(tk.Frame):
    def __init__(self, parent):
        font_family = get("gui", "font_family", "Consolas")
        font_size = get("gui", "font_size", 12)

        super().__init__(parent, bg="#080c14")

        # Scrollable text area
        self.text = tk.Text(
            self,
            bg="#080c14",
            fg="#c9d6e3",
            font=(font_family, font_size),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=16,
            pady=12,
            spacing1=4,
            spacing3=4,
            cursor="arrow",
        )

        scrollbar = tk.Scrollbar(self, command=self.text.yview, bg="#080c14")
        self.text.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Text tags for styling
        self.text.tag_config("you",      foreground="#38bdf8", font=(font_family, font_size, "bold"))
        self.text.tag_config("crystal",  foreground="#00ff9d", font=(font_family, font_size, "bold"))
        self.text.tag_config("msg",      foreground="#c9d6e3", font=(font_family, font_size))
        self.text.tag_config("system",   foreground="#2a3a50", font=(font_family, font_size - 1, "italic"))
        self.text.tag_config("error",    foreground="#ff4444", font=(font_family, font_size - 1, "italic"))

    def add_message(self, role: str, text: str):
        """
        Add a message to the chat display.
        role: "user" | "crystal" | "system" | "error"
        """
        self.text.config(state=tk.NORMAL)

        if role == "user":
            self.text.insert(tk.END, "You\n", "you")
            self.text.insert(tk.END, f"{text}\n\n", "msg")
        elif role == "crystal":
            self.text.insert(tk.END, "Crystal\n", "crystal")
            self.text.insert(tk.END, f"{text}\n\n", "msg")
        elif role == "system":
            self.text.insert(tk.END, f"[ {text} ]\n\n", "system")
        elif role == "error":
            self.text.insert(tk.END, f"[ ERROR: {text} ]\n\n", "error")

        self.text.config(state=tk.DISABLED)
        self.text.see(tk.END)  # Auto-scroll to bottom

    def append_token(self, token: str):
        """
        Append a single token to the last message (for streaming).
        Call this from brain.think(on_token=...) callback.
        """
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, token, "msg")
        self.text.config(state=tk.DISABLED)
        self.text.see(tk.END)

    def start_crystal_message(self):
        """Call this before streaming to add the Crystal label."""
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, "Crystal\n", "crystal")
        self.text.config(state=tk.DISABLED)

    def end_crystal_message(self):
        """Call this after streaming to add spacing."""
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, "\n\n", "msg")
        self.text.config(state=tk.DISABLED)
        self.text.see(tk.END)

    def clear(self):
        """Clear all messages."""
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)