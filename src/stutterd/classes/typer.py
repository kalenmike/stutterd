from pynput.keyboard import Key, Controller
import pyperclip
import time
import sys


class Typer:
    def __init__(self):
        self.keyboard = Controller()
        self.paste_key = "v"
        self.modifier = Key.ctrl
        if sys.platform == "darwin":
            self.modifier = Key.cmd

    def send_input(self, text):
        self.keyboard.type(text)

    def smart_inject(self, text):
        old_clipboard = pyperclip.paste()
        pyperclip.copy(text)

        # Give the OS a moment to register the new clipboard content
        time.sleep(0.05)

        try:
            # For Terminal/Neovim, Ctrl+Shift+V is often more reliable
            # We use a context manager to ensure keys are released
            with self.keyboard.pressed(self.modifier):
                # If in a terminal, many require Shift as well
                with self.keyboard.pressed(Key.shift):
                    self.keyboard.tap("v")
        finally:
            # Ensure we wait before restoring to prevent the 'old' text
            # from being pasted instead of the 'new' text
            time.sleep(0.15)
            pyperclip.copy(old_clipboard)
