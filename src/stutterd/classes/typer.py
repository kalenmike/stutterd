from pynput.keyboard import Key, Controller
import pyperclip
import time


class Typer:
    def __init__(self):
        self.keyboard = Controller()

    def send_input(self, text):
        self.keyboard.type(text)

    def smart_inject(self, text):
        # 1. Backup the old clipboard
        old_clipboard = pyperclip.paste()

        # 2. Set new content
        pyperclip.copy(text)

        # 3. Trigger Paste
        with self.keyboard.pressed(Key.ctrl):
            self.keyboard.tap("v")

        # 4. Small delay to let the OS "read" the clipboard before we swap back
        time.sleep(0.1)

        # 5. Restore original clipboard
        pyperclip.copy(old_clipboard)
