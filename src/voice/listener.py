# ============================================================
#  CRYSTAL AI - Listener (faster-whisper STT)
#  Records microphone audio and converts to text
# ============================================================

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from src.utils.config_loader import get
from src.utils.logger import get_logger

log = get_logger(__name__)


class Listener:
    def __init__(self):
        self.model_size = get("stt", "model_size", "base")
        self.language = get("stt", "language", "en")
        self.device = get("stt", "device", "cpu")
        self.compute_type = get("stt", "compute_type", "int8")
        self.silence_timeout = get("stt", "silence_timeout", 2.0)

        self.sample_rate = 16000   # Whisper expects 16kHz
        self.chunk_duration = 0.5  # seconds per audio chunk
        self.chunk_size = int(self.sample_rate * self.chunk_duration)

        log.info(f"Loading Whisper model: {self.model_size} (this may take a moment...)")
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        log.info("Listener ready")

    def listen(self) -> str:
        """
        Records audio from microphone until silence is detected.
        Returns transcribed text string.
        """
        log.info("Listening...")
        audio_chunks = []
        silent_chunks = 0
        max_silent_chunks = int(self.silence_timeout / self.chunk_duration)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_size,
        ) as stream:
            while True:
                chunk, _ = stream.read(self.chunk_size)
                chunk = chunk.flatten()
                audio_chunks.append(chunk)

                # Detect silence by checking audio energy
                energy = np.sqrt(np.mean(chunk ** 2))
                if energy < 0.01:  # silence threshold
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                # Stop after enough silence
                if silent_chunks >= max_silent_chunks and len(audio_chunks) > max_silent_chunks:
                    break

        # Combine all chunks into one array
        audio = np.concatenate(audio_chunks)

        # Transcribe with Whisper
        log.info("Transcribing...")
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
        )

        text = " ".join(segment.text for segment in segments).strip()
        log.info(f"Heard: {text}")
        return text

    def listen_once(self, duration: float = 5.0) -> str:
        """
        Records for a fixed duration and transcribes.
        Useful for testing.
        """
        log.info(f"Recording for {duration} seconds...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = audio.flatten()

        segments, _ = self.model.transcribe(audio, language=self.language)
        text = " ".join(s.text for s in segments).strip()
        log.info(f"Heard: {text}")
        return text