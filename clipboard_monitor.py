from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    new_clip_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clipboard = QApplication.clipboard()
        self.last_clip = self.clipboard.text()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

    def on_clipboard_changed(self):
        try:
            current_clip = self.clipboard.text()

            if current_clip and len(current_clip) > 50000:
                current_clip = current_clip[:50000] + "... (truncated)"

            if current_clip and current_clip != self.last_clip:
                self.last_clip = current_clip
                self.new_clip_signal.emit(current_clip)

        except Exception as e:
            error_msg = f"System clipboard error occurred: {str(e)}"
            self.error_signal.emit("Clipboard Error", error_msg)

    def stop(self):
        try:
            self.clipboard.dataChanged.disconnect(self.on_clipboard_changed)
        except TypeError:
            pass  # Already done
