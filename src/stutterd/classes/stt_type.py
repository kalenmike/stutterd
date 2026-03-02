import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from pynput.keyboard import Controller


def main():
    # Initialize
    model = WhisperModel("base", device="cpu", compute_type="int8")
    keyboard = Controller()

    def callback(indata, frames, time, status):
        """This function is called for every block of audio from the mic"""
        if status:
            print(status)

        # Standardize the audio for the AI
        audio_data = indata.flatten().astype(np.float32)

        # Transcribe the small chunk
        segments, _ = model.transcribe(audio_data, beam_size=5)

        for segment in segments:
            if segment.text.strip():
                keyboard.type(segment.text + " ")

    # Start the 'Ear'
    with sd.InputStream(samplerate=16000, channels=1, callback=callback):
        print("Listening... Whisper away.")
        sd.sleep(1000000)  # Keep the script running


def typing():
    keyboard = Controller()
    keyboard.type("Hello")


if __name__ == "__main__":
    main()
