# ============================================================
#  CRYSTAL AI - Speaker (Piper TTS)
#  Pipes audio directly from Piper — no temp files, no lag
# ============================================================

import subprocess
import os
import io
import sounddevice as sd
import numpy as np
import wave
from src.utils.config_loader import get
from src.utils.logger import get_logger

log = get_logger(__name__)


class Speaker:
    def __init__(self):
        self.root = self._get_root()
        self.piper_exe = os.path.join(self.root, get("tts", "piper_exe"))
        self.model     = os.path.join(self.root, get("tts", "piper_model"))
        self.config    = os.path.join(self.root, get("tts", "piper_config"))
        self.volume    = get("tts", "volume", 1.0)

        self._check_files()
        log.info("Speaker ready — Piper TTS (direct pipe)")

    def speak(self, text: str):
        if not text or not text.strip():
            return

        # Clean text — remove markdown symbols that sound weird
        clean = text.replace("*", "").replace("#", "").replace("`", "").strip()
        log.info(f"Speaking: {clean[:60]}...")

        try:
            # Run Piper — output raw WAV to stdout
            cmd = [
                self.piper_exe,
                "--model",  self.model,
                "--config", self.config,
                "--output-raw",          # raw PCM to stdout
            ]

            proc = subprocess.run(
                cmd,
                input=clean.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if proc.returncode != 0:
                err = proc.stderr.decode(errors="ignore")
                log.error(f"Piper error: {err}")
                # Fallback to file method if raw fails
                self._speak_via_file(clean)
                return

            raw_audio = proc.stdout
            if not raw_audio:
                log.warning("Piper returned no audio")
                return

            # Piper raw output is 16-bit PCM mono at 22050Hz
            audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
            audio = (audio / 32768.0) * self.volume

            sd.play(audio, samplerate=22050)
            sd.wait()

        except subprocess.TimeoutExpired:
            log.error("Piper timed out")
        except Exception as e:
            log.error(f"Speaker error: {e}")
            self._speak_via_file(clean)

    def _speak_via_file(self, text: str):
        """Fallback: write to temp file and play."""
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                self.piper_exe,
                "--model",       self.model,
                "--config",      self.config,
                "--output_file", tmp_path,
            ]
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0:
                self._play_wav(tmp_path)
        except Exception as e:
            log.error(f"Fallback speaker error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _play_wav(self, path: str):
        with wave.open(path, "rb") as wf:
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        audio = (audio / 32768.0) * self.volume
        sd.play(audio, samplerate=rate)
        sd.wait()

    def _check_files(self):
        missing = []
        for label, path in [
            ("piper.exe",          self.piper_exe),
            ("voice model (.onnx)", self.model),
            ("voice config (.onnx.json)", self.config),
        ]:
            if not os.path.exists(path):
                missing.append(f"  ✗ {label} → {path}")
        if missing:
            for m in missing:
                log.error(m)
            raise FileNotFoundError("Piper files missing. Check piper_voices/ folder.")

    def _get_root(self) -> str:
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )