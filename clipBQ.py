import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from dotenv import load_dotenv

from main_window import MainWindow


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


env_path = os.path.join(resource_path(".env"))
load_dotenv(env_path)


if __name__ == "__main__":
    if sys.platform == "win32":
        appId = "clipbq.clipBQ.cloud.1.1.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    app = QApplication(sys.argv)
    app_icon = QIcon()
    app_icon.addFile(resource_path("icon.png"))
    app_icon.addFile(resource_path("icon.ico"))
    app.setWindowIcon(app_icon)
    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())
