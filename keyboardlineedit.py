import subprocess

from PyQt5.QtWidgets import QLineEdit


class KeyboardLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(KeyboardLineEdit, self).__init__(parent)

    def focusInEvent(self, e):
        try:
            subprocess.Popen(["matchbox-keyboard", "-i"])
        except FileNotFoundError:
            pass

    def focusOutEvent(self, e):
        subprocess.Popen(["killall", "matchbox-keyboard"])
