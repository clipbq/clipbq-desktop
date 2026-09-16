import sys
import os
import ctypes
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import pyperclip
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QMessageBox,
)
from PyQt6.QtGui import QIcon
from supabase import create_client, Client
from dotenv import load_dotenv

from history_list import NumberedListWidget


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


env_path = os.path.join(resource_path(".env"))
load_dotenv(env_path)

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
LOGIN_PAGE_URL = os.environ.get("LOGIN_PAGE_URL")  # Vite dev server
TOKEN_FILE = os.path.expanduser("~/.clipbq_auth_token.json")

# Global handle for local auth callback server
auth_callback_token = None


class TokenCallbackHandler(BaseHTTPRequestHandler):
    """Local server endpoint to receive authentication token from browser."""

    def do_GET(self):
        global auth_callback_token
        if "/callback" in self.path:
            from urllib.parse import urlparse, parse_qs

            query = parse_qs(urlparse(self.path).query)
            if "token" in query:
                auth_callback_token = query["token"][0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authentication Successful!</h1><p>You may close this tab and return to the application.</p>"
            )

    def log_message(self, format, *args):
        return  # Silence standard HTTP server logs in console


def start_local_auth_server(port=9999):
    """Runs a temporary HTTP server on port 9999 to capture browser callback."""
    server = HTTPServer(("localhost", port), TokenCallbackHandler)
    server.single_request = True
    server.handle_request()  # Block until one callback request is received
    server.server_close()


class ClipboardMonitorThread(QThread):
    new_clip_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.last_clip = ""

    def run(self):
        try:
            self.last_clip = pyperclip.paste()
        except Exception:
            self.last_clip = ""

        while self.running:
            self.msleep(1000)
            try:
                current_clip = pyperclip.paste()
                if (
                    current_clip
                    and isinstance(current_clip, str)
                    and current_clip != self.last_clip
                ):
                    self.last_clip = current_clip
                    self.new_clip_signal.emit(current_clip)
            except Exception:
                pass

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("clipBQ Cloud Monitor")
        self.resize(480, 550)
        self.supabase: Client = None
        self.monitor_thread = None

        self.init_ui()
        self.check_or_route_auth()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Status Display
        self.status_label = QLabel("Status: Not Authenticated")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        # History List View
        layout.addWidget(QLabel("Clipboard Sync History:"))
        self.history_list = NumberedListWidget()
        layout.addWidget(self.history_list)

        # Token Input Section (Manual Paste Option)
        token_input_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste Access Token here...")
        token_input_layout.addWidget(self.token_input)

        self.btn_submit_token = QPushButton("Submit Token")
        self.btn_submit_token.clicked.connect(self.handle_manual_token_submit)
        token_input_layout.addWidget(self.btn_submit_token)
        layout.addLayout(token_input_layout)

        # Quick Actions
        button_layout = QHBoxLayout()
        self.btn_paste_clipboard = QPushButton("Paste from Clipboard")
        self.btn_paste_clipboard.clicked.connect(self.paste_from_clipboard)
        button_layout.addWidget(self.btn_paste_clipboard)

        self.btn_open_portal = QPushButton("Open Login Page")
        self.btn_open_portal.clicked.connect(self.route_to_login)
        button_layout.addWidget(self.btn_open_portal)
        layout.addLayout(button_layout)

    def load_saved_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("access_token")
            except Exception:
                return None
        return None

    def save_token(self, token):
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": token}, f)

    def check_or_route_auth(self):
        token = self.load_saved_token()
        if token:
            self.init_supabase_with_token(token)
        else:
            # Route automatically to browser login while leaving manual inputs accessible
            self.route_to_login()

    def route_to_login(self):
        """Automatically opens browser to login page and listens for redirect."""
        self.status_label.setText("Redirecting to login portal in browser...")

        # Start local listener thread to capture callback automatically
        server_thread = Thread(target=self.await_browser_callback, daemon=True)
        server_thread.start()

        # Open web browser
        callback_url = f"{LOGIN_PAGE_URL}?redirect_port=9999"
        webbrowser.open(callback_url)

    def await_browser_callback(self):
        global auth_callback_token
        auth_callback_token = None

        # Block until callback server hears response from browser
        start_local_auth_server(port=9999)

        if auth_callback_token:
            self.save_token(auth_callback_token)
            self.init_supabase_with_token(auth_callback_token)

    def handle_manual_token_submit(self):
        """Processes manually typed or pasted token from QLineEdit."""
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Input Error", "Token field is empty.")
            return

        self.save_token(token)
        self.init_supabase_with_token(token)

    def paste_from_clipboard(self):
        """Pastes current clipboard text straight into the token input field."""
        try:
            clip_text = pyperclip.paste().strip()
            if clip_text:
                self.token_input.setText(clip_text)
            else:
                QMessageBox.information(
                    self, "Clipboard Empty", "No text found in clipboard."
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Clipboard Error", f"Failed to read clipboard: {e}"
            )

    def init_supabase_with_token(self, token):
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

            user_response = self.supabase.auth.get_user(token)
            if not user_response.user:
                raise Exception("Invalid token response")

            self.user_id = user_response.user.id
            self.access_token = token

            self.supabase.postgrest.auth(token)

            # Update UI on successful connection
            self.status_label.setText(
                f"Status: Authenticated ({user_response.user.email})"
            )
            self.status_label.setStyleSheet("color: green;")
            self.token_input.setDisabled(True)
            self.btn_open_portal.setDisabled(True)
            self.btn_paste_clipboard.setDisabled(True)
            self.btn_submit_token.setDisabled(True)

            self.fetch_history()
            self.start_monitoring()
        except Exception as e:
            self.status_label.setText("Status: Authentication Failed")
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.critical(
                self, "Auth Error", f"Failed to authenticate: {str(e)}"
            )

    def fetch_history(self):
        """Loads user's clipboard history enforced by RLS."""
        try:
            response = (
                self.supabase.table("clipboard_history")
                .select("content, created_at")
                .order("created_at", desc=True)
                .execute()
            )

            self.history_list.clear()
            for record in response.data:
                item_text = f"{record['content']}"
                self.history_list.append_item(item_text)
        except Exception as e:
            QMessageBox.critical(
                self, "Fetch Error", f"Could not load history: {str(e)}"
            )

    def start_monitoring(self):
        if self.monitor_thread is None:
            self.monitor_thread = ClipboardMonitorThread()
            self.monitor_thread.new_clip_signal.connect(self.upload_clip)
            self.monitor_thread.start()

    def upload_clip(self, content: str):
        """Pushes detected clipboard content to Cloud."""
        try:
            data = {"user_id": self.user_id, "content": content}
            response = self.supabase.table("clipboard_history").insert(data).execute()
            if response.data:
                self.history_list.prepend_item(f"{content}")
        except Exception as e:
            print(f"Error pushing clipboard entry: {e}")

    def closeEvent(self, event):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.quit()
            if not self.monitor_thread.wait(2000):
                # If it takes too long (e.g. pyperclip hangs), forcefully terminate it
                self.monitor_thread.terminate()
                self.monitor_thread.wait()
        event.accept()


if __name__ == "__main__":
    if sys.platform == "win32":
        appId = "clipbq.clipBQ.cloud.1.0.1"
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
