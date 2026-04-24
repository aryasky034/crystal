# ============================================================
#  CRYSTAL AI - PC Control  (Phase 3)
#  src/control/pc_control.py
#
#  What Crystal can do:
#
#  APPS        — open / close any app by name or alias
#  VOLUME      — set, mute, unmute, volume up/down
#  SCREENSHOTS — take a screenshot, save with timestamp
#  CLIPBOARD   — read / write clipboard text
#  SYSTEM      — lock screen, sleep, shutdown, restart
#  WINDOW      — minimize, maximize, alt+tab
#  FILES       — open a file or folder in Explorer
#  WEB         — open a URL in the default browser
#
#  Usage (called by Brain when it detects a PC command):
#
#    pc = PCControl()
#    result = pc.execute("open spotify")
#    result = pc.execute("volume 40")
#    result = pc.execute("screenshot")
#    result = pc.execute("mute")
# ============================================================

import os
import re
import subprocess
import webbrowser
from datetime import datetime
from src.utils.logger import get_logger

log = get_logger(__name__)

# ── Try importing optional dependencies ──────────────────────
try:
    import pyautogui
    PYAUTOGUI = True
except ImportError:
    PYAUTOGUI = False
    log.warning("pyautogui not installed — keyboard/mouse control disabled")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    PYCAW = True
except ImportError:
    PYCAW = False
    log.warning("pycaw not installed — using nircmd fallback for volume")

try:
    import pyperclip
    PYPERCLIP = True
except ImportError:
    PYPERCLIP = False
    log.warning("pyperclip not installed — clipboard control disabled")


# ── APP ALIASES ───────────────────────────────────────────────
# Maps voice-friendly names → actual executable / command
APP_ALIASES: dict[str, str] = {
    # Browsers
    "chrome":         "chrome",
    "google chrome":  "chrome",
    "firefox":        "firefox",
    "edge":           "msedge",
    "browser":        "chrome",

    # Dev tools
    "vs code":        "code",
    "vscode":         "code",
    "visual studio":  "code",
    "terminal":       "wt",          # Windows Terminal
    "cmd":            "cmd",
    "powershell":     "powershell",
    "git":            "git-bash",

    # Media
    "spotify":        "spotify",
    "vlc":            "vlc",
    "youtube":        "https://youtube.com",

    # System apps
    "notepad":        "notepad",
    "explorer":       "explorer",
    "file explorer":  "explorer",
    "task manager":   "taskmgr",
    "calculator":     "calc",
    "settings":       "ms-settings:",
    "discord":        "discord",
    "steam":          "steam",
    "obs":            "obs64",
    "blender":        "blender",
    "arduino ide":    "arduino_debug",
    "arduino":        "arduino_debug",
}

# ── SCREENSHOT FOLDER ─────────────────────────────────────────
SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Crystal_Screenshots")


class PCControl:
    """
    Crystal's interface to the Windows operating system.
    All methods return a human-readable result string that
    Crystal will speak back to the user.
    """

    def __init__(self):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        log.info("PC Control module loaded")

    # ── MAIN DISPATCHER ──────────────────────────────────────

    def execute(self, command: str) -> str:
        """
        Parse a natural-language command and run the right action.
        Returns a short result string for Crystal to speak.
        """
        cmd = command.lower().strip()

        # Volume controls
        if re.search(r"\bmute\b",   cmd): return self.mute()
        if re.search(r"\bunmute\b", cmd): return self.unmute()
        if re.search(r"volume\s+(?:up|higher|louder)",   cmd): return self.volume_up()
        if re.search(r"volume\s+(?:down|lower|quieter)", cmd): return self.volume_down()
        m = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d+)", cmd)
        if m: return self.set_volume(int(m.group(1)))

        # Screenshot
        if re.search(r"screenshot|screen\s*shot|capture\s+screen", cmd):
            return self.screenshot()

        # Clipboard
        if re.search(r"(?:what'?s?|read|get)\s+(?:in\s+)?(?:my\s+)?clipboard", cmd):
            return self.read_clipboard()
        m = re.search(r"copy\s+(.+)\s+to\s+clipboard", cmd)
        if m: return self.write_clipboard(m.group(1))

        # System actions
        if re.search(r"lock\s+(?:the\s+)?(?:screen|pc|computer)", cmd): return self.lock_screen()
        if re.search(r"(?:put\s+(?:the\s+)?pc\s+to\s+)?sleep", cmd):   return self.sleep()
        if re.search(r"shut\s*down|power\s+off",                  cmd): return self.shutdown()
        if re.search(r"restart|reboot",                           cmd): return self.restart()

        # Window management
        if re.search(r"minimize",      cmd): return self.minimize_window()
        if re.search(r"maximize",      cmd): return self.maximize_window()
        if re.search(r"alt.?tab|switch\s+(?:app|window)", cmd): return self.alt_tab()

        # Open URL
        m = re.search(r"open\s+(https?://\S+)", cmd)
        if m: return self.open_url(m.group(1))

        # Open file / folder
        m = re.search(r"open\s+(?:the\s+)?(?:file|folder)\s+(.+)", cmd)
        if m: return self.open_path(m.group(1).strip())

        # Open app (must come last — most generic)
        m = re.search(r"open\s+(.+)", cmd)
        if m: return self.open_app(m.group(1).strip())

        # Close app
        m = re.search(r"close\s+(.+)", cmd)
        if m: return self.close_app(m.group(1).strip())

        return f"I'm not sure how to do '{command}' yet."

    # ── APPS ─────────────────────────────────────────────────

    def open_app(self, name: str) -> str:
        """Open an application by name or alias."""
        name_lower = name.lower().strip().rstrip(".,!?")

        # Check alias map
        target = APP_ALIASES.get(name_lower)

        if target is None:
            # Try partial match
            for alias, exe in APP_ALIASES.items():
                if alias in name_lower or name_lower in alias:
                    target = exe
                    break

        if target is None:
            target = name  # try as-is

        # If it looks like a URL, open in browser
        if target.startswith("http"):
            return self.open_url(target)

        # If it looks like a ms-settings URI
        if target.startswith("ms-"):
            try:
                os.startfile(target)
                return f"Opening {name}."
            except Exception as e:
                return f"Couldn't open {name}: {e}"

        try:
            subprocess.Popen(
                target,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log.info(f"Opened: {target}")
            return f"Opening {name}."
        except Exception as e:
            log.error(f"open_app failed: {e}")
            return f"Couldn't open {name}. Make sure it's installed."

    def close_app(self, name: str) -> str:
        """Kill a process by name."""
        exe = APP_ALIASES.get(name.lower(), name)
        # Strip path, add .exe if needed
        process_name = os.path.basename(exe)
        if not process_name.endswith(".exe"):
            process_name += ".exe"
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", process_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"Closed {name}."
        except Exception as e:
            return f"Couldn't close {name}: {e}"

    # ── VOLUME ───────────────────────────────────────────────

    def set_volume(self, level: int) -> str:
        """Set system volume to a percentage (0–100)."""
        level = max(0, min(100, level))
        if PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                # pycaw uses -65.25 to 0.0 dB — map from 0-100
                scalar = level / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                log.info(f"Volume set to {level}%")
                return f"Volume set to {level} percent."
            except Exception as e:
                log.error(f"pycaw volume error: {e}")

        # Fallback: use PowerShell
        try:
            ps_cmd = (
                f"$vol = New-Object -ComObject WScript.Shell; "
                f"$vol.SendKeys([char]174 * 50); "   # mute first
            )
            # Simpler fallback using nircmd if available
            subprocess.run(
                f'powershell -c "$wsh = New-Object -ComObject WScript.Shell; '
                f'(New-Object -ComObject Shell.Application).SetVolume({level})"',
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Volume set to {level} percent."
        except Exception as e:
            return f"Couldn't change volume: {e}"

    def volume_up(self, steps: int = 5) -> str:
        if PYAUTOGUI:
            for _ in range(steps):
                pyautogui.press("volumeup")
            return "Volume up."
        subprocess.run("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]175)",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Volume up."

    def volume_down(self, steps: int = 5) -> str:
        if PYAUTOGUI:
            for _ in range(steps):
                pyautogui.press("volumedown")
            return "Volume down."
        subprocess.run("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]174)",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Volume down."

    def mute(self) -> str:
        if PYAUTOGUI:
            pyautogui.press("volumemute")
            return "Muted."
        subprocess.run("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]173)",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Muted."

    def unmute(self) -> str:
        return self.mute()   # volumemute is a toggle

    # ── SCREENSHOT ───────────────────────────────────────────

    def screenshot(self, filename: str = None) -> str:
        """Take a screenshot and save to Desktop/Crystal_Screenshots/."""
        if not PYAUTOGUI:
            return "pyautogui is not installed — can't take screenshots yet."
        try:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = filename or f"screenshot_{ts}.png"
            path = os.path.join(SCREENSHOT_DIR, filename)
            img = pyautogui.screenshot()
            img.save(path)
            log.info(f"Screenshot saved: {path}")
            return f"Screenshot saved to your Desktop in the Crystal_Screenshots folder."
        except Exception as e:
            log.error(f"Screenshot failed: {e}")
            return f"Screenshot failed: {e}"

    # ── CLIPBOARD ─────────────────────────────────────────────

    def read_clipboard(self) -> str:
        if not PYPERCLIP:
            return "pyperclip is not installed — clipboard access unavailable."
        try:
            text = pyperclip.paste()
            if not text:
                return "The clipboard is empty."
            preview = text[:200] + "..." if len(text) > 200 else text
            return f"Your clipboard contains: {preview}"
        except Exception as e:
            return f"Couldn't read clipboard: {e}"

    def write_clipboard(self, text: str) -> str:
        if not PYPERCLIP:
            return "pyperclip is not installed — clipboard access unavailable."
        try:
            pyperclip.copy(text)
            return f"Copied to clipboard."
        except Exception as e:
            return f"Couldn't write to clipboard: {e}"

    # ── SYSTEM ───────────────────────────────────────────────

    def lock_screen(self) -> str:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return "Locking the screen."

    def sleep(self) -> str:
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "Going to sleep."

    def shutdown(self) -> str:
        subprocess.run("shutdown /s /t 10", shell=True)
        return "Shutting down in 10 seconds. Say cancel if you changed your mind."

    def cancel_shutdown(self) -> str:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown cancelled."

    def restart(self) -> str:
        subprocess.run("shutdown /r /t 10", shell=True)
        return "Restarting in 10 seconds."

    # ── WINDOW MANAGEMENT ────────────────────────────────────

    def minimize_window(self) -> str:
        if PYAUTOGUI:
            pyautogui.hotkey("win", "down")
            return "Minimized."
        return "pyautogui not installed."

    def maximize_window(self) -> str:
        if PYAUTOGUI:
            pyautogui.hotkey("win", "up")
            return "Maximized."
        return "pyautogui not installed."

    def alt_tab(self) -> str:
        if PYAUTOGUI:
            pyautogui.hotkey("alt", "tab")
            return "Switched window."
        return "pyautogui not installed."

    # ── FILES & WEB ──────────────────────────────────────────

    def open_path(self, path: str) -> str:
        """Open a file or folder in Explorer."""
        expanded = os.path.expandvars(os.path.expanduser(path))
        if os.path.exists(expanded):
            os.startfile(expanded)
            return f"Opened {path}."
        return f"Path not found: {path}"

    def open_url(self, url: str) -> str:
        """Open a URL in the default browser."""
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url}."