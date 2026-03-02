from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np

from enum import Enum


class WhisperLanguage(Enum):
    # Standard selection
    AUTO = None
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"
    TURKISH = "tr"

    @classmethod
    def list_codes(cls):
        """Returns a list of all valid string codes."""
        return [lang.value for lang in cls if lang.value is not None]


class Listener:
    def __init__(self, model_path, threshold=0.1, silence_duration=1.5):
        self.sample_rate = 16000
        self.threshold = threshold
        self.silence_duration = silence_duration

        # Load Model
        self.model = WhisperModel(
            model_path,
            device="cpu",
            compute_type="int8",
            local_files_only=True,
        )
        self.language = None

    def set_language(self, lang_choice: WhisperLanguage):
        self.language = lang_choice.value

    def listen_until_silence(self, callback=None):
        audio_data = []
        silent_chunks = 0
        recording_started = False  # The "Gate Keeper" variable

        with sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32"
        ) as stream:
            while True:
                chunk, _ = stream.read(int(self.sample_rate * 0.1))
                audio_data.append(chunk)
                volume = np.linalg.norm(chunk)

                if callback:
                    callback(volume)

                # PHASE 1: Waiting for a sound loud enough to be a voice
                if not recording_started:
                    if volume >= self.threshold:
                        recording_started = True
                        # Optional: Keep only the last chunk or two to avoid lead-in silence
                        audio_data = audio_data[-2:]
                    else:
                        # Keep the audio buffer small while waiting so we don't
                        # send 10 minutes of silence to Whisper if it's been idle
                        if len(audio_data) > 10:
                            audio_data.pop(0)
                        continue  # Skip the silence counting below

                # PHASE 2: User is talking, now we monitor for the end (silence)
                if volume < self.threshold:
                    silent_chunks += 0.1
                else:
                    silent_chunks = 0

                # Only break if we actually started recording and then hit silence
                if silent_chunks >= self.silence_duration:
                    break

        return np.concatenate(audio_data).flatten()

    def listen(self, abort_flag=None, callback=None):
        audio_data = []
        silent_chunks = 0

        with sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32"
        ) as stream:
            while True:
                # Check if the user forced an end via the hotkey
                if abort_flag and abort_flag.is_set():
                    break

                chunk, _ = stream.read(int(self.sample_rate * 0.1))
                audio_data.append(chunk)

                # volume = np.linalg.norm(chunk)
                volume = np.sqrt(np.mean(chunk**2))

                if callback:
                    callback(volume)

                # Track Silence
                if volume < self.threshold:
                    silent_chunks += 0.1
                else:
                    silent_chunks = 0

                # Normal silence detection
                if silent_chunks >= self.silence_duration and len(audio_data) > 5:
                    break

        if not audio_data:
            # Return a tiny bit of silence (0.1s) so the rest of the app doesn't break
            return np.zeros(int(self.sample_rate * 0.1), dtype="float32")

        return np.concatenate(audio_data).flatten()

    def transcribe(self, audio):
        """Converts raw audio to text."""
        segments, _ = self.model.transcribe(
            audio,
            vad_filter=True,
            language=self.language,
        )
        return "".join([s.text for s in segments]).strip()
