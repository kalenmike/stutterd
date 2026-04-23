# Copyright (c) 2026 Kalen Michael
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

from stutterd.classes.listener import Listener, WhisperLanguage
from stutterd.classes.typer import Typer
import time
import sys
import os
import inspect
import tempfile

import threading
from pynput import keyboard

STT_MODEL_PATH = os.path.expanduser(
    "~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
)
MIC_THRESHOLD = 0.001

STATUS_FILE = os.path.join(tempfile.gettempdir(), "stutterd_status")


class AppState:
    def __init__(self, hands, ears):
        # Event starts "cleared" (Paused)
        self.is_active = False
        self.last_transcription = ""
        self.lock = threading.Lock()
        self.abort_listening = threading.Event()
        self.language = WhisperLanguage.ENGLISH
        # listener = keyboard.Listener(on_press=lambda k: self.on_press(k, hands))
        # listener.start()

        self.hotkeys = keyboard.GlobalHotKeys(
            {
                "<ctrl>+<alt>+<space>": self.toggle_mic,
                "<ctrl>+<alt>+v": lambda: self.paste_last(hands),
                "<ctrl>+<alt>+s": self.stop_listening,  # "S" for Stop/Submit
                "<ctrl>+<alt>+t": lambda: self.toggle_language(ears),
            }
        )

        self.hotkeys.start()

        self.print_welcome()
        self.update_shared_status()

    def update_shared_status(self):
        """Writes the current state to a temp file for Polybar to read."""
        try:
            with open(STATUS_FILE, "w") as f:
                if not self.is_active:
                    # Muted icon (Requires a font like FontAwesome or Nerd Fonts)
                    f.write("OFF")
                else:
                    # Display language code (EN/ES)
                    lang_code = (
                        "EN" if self.language == WhisperLanguage.ENGLISH else "ES"
                    )
                    f.write(f"{lang_code}")
        except Exception:
            pass

    def print_welcome(self):
        # ANSI Color codes for a bit of flair
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        ascii_art = f"""{CYAN}
          _____ _         _   _               _ 
         / ____| |       | | | |             | |
        | (___ | |_ _   _| |_| |_ ___ _ __ __| |
         \___ \| __| | | | __| __/ _ \ '__/ _` |
         ____) | |_| |_| | |_| ||  __/ | | (_| |
        |_____/ \__|\__,_|\__|\__\___|_|  \__,_|{RESET}"""

        intro_text = inspect.cleandoc(f"""
        {ascii_art}
        {BOLD}STT HID Interface | Version 1.0.0{RESET}
        {GREEN}System Status: [READY]{RESET}
        {GREEN}Language     : {self.language.name}{RESET}

        {BOLD}⌨️  GLOBAL COMMAND CENTER{RESET}
        {"-" * 50}
        {YELLOW}Ctrl + Alt + Space{RESET}  ->  {BOLD}Toggle Mic{RESET} (ON/OFF)
        {YELLOW}Ctrl + Alt + V{RESET}      ->  {BOLD}Paste Last{RESET} (Re-type previous)
        {YELLOW}Ctrl + Alt + S{RESET}      ->  {BOLD}Submit{RESET}     (Force transcription)
        {YELLOW}Ctrl + Alt + T{RESET}      ->  {BOLD}Toggle Language{RESET}(English/Spanish)
        {"-" * 50}
        
        """)

        # Clear terminal if you want a fresh start
        os.system("cls" if os.name == "nt" else "clear")

        print(intro_text)
        self.print_status("Waiting for activation...")

    def print_status(self, status):
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        sys.stdout.write(f"\r{CYAN}{status}{RESET}")
        sys.stdout.flush()

    def toggle_language(self, ears):
        self._disable()
        if self.language == WhisperLanguage.ENGLISH:
            self.language = WhisperLanguage.SPANISH
        else:
            self.language = WhisperLanguage.ENGLISH

        ears.set_language(self.language)
        self.print_welcome()
        self.update_shared_status()

    def stop_listening(self):
        self.abort_listening.set()

    def allow_listening(self):
        self.abort_listening.clear()

    def _disable(self):
        self.is_active = False
        self.stop_listening()
        self.update_shared_status()

    def _enable(self):
        self.allow_listening()
        self.is_active = True
        self.update_shared_status()

    def toggle_mic(self):
        with self.lock:
            if self.is_active:
                self._disable()
            else:
                self._enable()

    def stop_and_submit(self):
        if self.is_active:
            self.stop_listening()
            print("\n[!] Force Transcribe Triggered")

    def paste_last(self, hands):
        with self.lock:
            if self.last_transcription:
                hands.smart_inject(self.last_transcription)


def show_heartbeat(volume, threshold, active):
    # 1. Define the scale based on the threshold
    # We want the bar to be "Full" when volume is 3x the threshold
    max_expected = threshold * 20

    # 2. Calculate percentage (0.0 to 1.0)
    # If volume is at threshold, it's 33% full. If it's at max, it's 100% full.
    if max_expected > 0:
        percent = min(volume / max_expected, 1.0)
    else:
        percent = 0

    # 3. Map to bar length
    bar_total_width = 30
    filled_width = int(percent * bar_total_width)

    # 4. Determine bar character based on state
    # Use a different character if we are actually above the threshold (Loud)
    if volume >= threshold:
        char = "█"  # Solid block
    else:
        char = "▒"  # Shaded block

    prefix = " [●] Active " if active else " [○] Paused"
    bar = char * filled_width + "-" * (bar_total_width - filled_width)

    # We add the threshold line visual marker '|' at the 33% mark
    # This shows the user exactly where their voice needs to hit to trigger the mic
    sys.stdout.write(f"\r{prefix} [{bar}]")
    sys.stdout.flush()


def main():
    ears = Listener(STT_MODEL_PATH, threshold=MIC_THRESHOLD)
    hands = Typer()
    state = AppState(hands, ears)

    try:
        while True:
            # If state is False, we loop and sleep without touching the mic
            if not state.is_active:
                time.sleep(0.1)  # Saves CPU while paused
                continue

            # This part ONLY runs when state.is_active is True
            # It will capture one "phrase" at a time
            audio = ears.listen(
                callback=lambda vol: show_heartbeat(
                    vol, ears.threshold, state.is_active
                ),
                abort_flag=state.abort_listening,
            )
            state.abort_listening.clear()

            # Check again after listening (in case you toggled OFF while speaking)
            if state.is_active:
                text = ears.transcribe(audio)
                state.last_transcription = text
                if text.strip():
                    hands.smart_inject(text)

    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
