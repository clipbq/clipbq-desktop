import sys
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal
import pyperclip
from supabase import create_client, Client
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_KEY")
TOKEN_FILE = Path.home() / ".clipbq_clipboard_token.json"


class ClipboardMonitor(QThread):
    new_clip_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.last_clip = ""

    def run(self):
        # Initialize baseline clipboard content
        try:
            self.last_clip = pyperclip.paste()
        except Exception:
            self.last_clip = ""

        while self.running:
            self.msleep(500)
            try:
                current_clip = pyperclip.paste()
                if current_clip and current_clip != self.last_clip:
                    self.last_clip = current_clip
                    self.new_clip_signal.emit(current_clip)
            except Exception:
                pass

    def stop(self):
        self.running = False
        self.wait()


class ClipboardApp(QWidget):
    def __init__(self):
        super().__init__()
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.access_token = None
        self.user_id = None
        self.monitor_thread = None

        self.init_ui()
        self.load_local_token()

    def init_ui(self):
        self.setWindowTitle("clipBQ Cloud Monitor")
        self.resize(500, 600)

        layout = QVBoxLayout()

        # Login controls
        self.auth_label = QLabel("Paste Your Access Token:")
        layout.addWidget(self.auth_label)

        auth_input_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your token here...")
        auth_input_layout.addWidget(self.token_input)

        self.login_btn = QPushButton("Authenticate")
        self.login_btn.clicked.connect(self.handle_manual_login)
        auth_input_layout.addWidget(self.login_btn)

        layout.addLayout(auth_input_layout)

        # Status label
        self.status_label = QLabel("Status: Not Authenticated")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        # History List View
        layout.addWidget(QLabel("Clipboard Sync History:"))
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)

        self.setLayout(layout)

    def load_local_token(self):
        """Loads cached token if available."""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    token = data.get("access_token")
                    if token:
                        self.authenticate_supabase(token)
            except Exception as e:
                print(f"Error loading cached token: {e}")

    def save_local_token(self, token: str):
        """Persists access token locally."""
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump({"access_token": token}, f)
        except Exception as e:
            print(f"Error saving token locally: {e}")

    def handle_manual_login(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Warning", "Please enter a valid token.")
            return
        self.authenticate_supabase(token)

    def authenticate_supabase(self, token: str):
        try:
            # Validate token and set session on user client
            user_response = self.supabase.auth.get_user(token)
            if not user_response.user:
                raise Exception("Invalid token response")

            self.user_id = user_response.user.id
            self.access_token = token
            self.save_local_token(token)

            # Update Client options with Bearer Token for RLS
            self.supabase.postgrest.auth(token)

            self.status_label.setText(f"Status: Authenticated ({user_response.user.email})")
            self.status_label.setStyleSheet("color: green;")
            self.token_input.setDisabled(True)
            self.login_btn.setDisabled(True)

            self.fetch_history()
            self.start_monitoring()

        except Exception as e:
            self.status_label.setText("Status: Authentication Failed")
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Auth Error", f"Failed to authenticate: {str(e)}")

    def fetch_history(self):
        """Loads user's clipboard history enforced by RLS."""
        try:
            response = self.supabase.table("clipboard_history") \
                .select("content, created_at") \
                .order("created_at", desc=True) \
                .execute()

            self.history_list.clear()
            for record in response.data:
                item_text = f"{record['content']}"
                self.history_list.addItem(item_text)
        except Exception as e:
            QMessageBox.critical(self, "Fetch Error", f"Could not load history: {str(e)}")

    def start_monitoring(self):
        if not self.monitor_thread:
            self.monitor_thread = ClipboardMonitor()
            self.monitor_thread.new_clip_signal.connect(self.upload_clip)
            self.monitor_thread.start()

    def upload_clip(self, content: str):
        """Pushes detected clipboard content to Cloud."""
        try:
            data = {
                "user_id": self.user_id,
                "content": content
            }
            response = self.supabase.table("clipboard_history").insert(data).execute()
            if response.data:
                # created_at = response.data[0]['created_at'][:19]
                self.history_list.insertItem(0, f"{content}")
        except Exception as e:
            print(f"Error pushing clipboard entry: {e}")

    def closeEvent(self, event):
        if self.monitor_thread:
            self.monitor_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClipboardApp()
    window.show()
    sys.exit(app.exec())