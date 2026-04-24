# ============================================================
#  CRYSTAL AI - Wake Word Detection (openwakeword)
#  Listens continuously for "Hey Crystal" before activating
# ============================================================

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from src.utils.config_loader import get
from src.utils.logger import get_logger

log = get_logger(__name__)

# How confident openwakeword must be before triggering (0.0 - 1.0)
DETECTION_THRESHOLD = 0.5


class WakeWord:
    def __init__(self):
        self.wake_word = get("stt", "wake_word", "hey crystal")
        self.sample_rate = 16000
        self.chunk_size = 1280  # openwakeword expects 80ms chunks at 16kHz

        log.info(f"Loading wake word model for: '{self.wake_word}'")

        # Load openwakeword with the hey_mycroft model (closest to "Hey Crystal")
        # openwakeword will auto-download models on first run
        self.model = Model(
            wakeword_models=["hey_mycroft"],
            inference_framework="onnx",
        )

        log.info("Wake word detector ready — listening for 'Hey Crystal'")

    def wait_for_wake_word(self, on_detected=None):
        """
        Blocks and listens continuously until wake word is detected.
        Calls on_detected() callback when triggered.
        """
        log.info(f"Waiting for wake word: '{self.wake_word}'...")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk_size,
        ) as stream:
            while True:
                chunk, _ = stream.read(self.chunk_size)
                chunk = chunk.flatten()

                # Feed chunk to openwakeword
                prediction = self.model.predict(chunk)

                # Check all scores for a detection
                for model_name, score in prediction.items():
                    if score >= DETECTION_THRESHOLD:
                        log.info(f"Wake word detected! (score: {score:.2f})")
                        if on_detected:
                            on_detected()
                        return True

    def is_wake_word(self, text: str) -> bool:
        """
        Fallback text-based wake word check.
        Used when running in text-only mode.
        """
        return self.wake_word.lower() in text.lower()