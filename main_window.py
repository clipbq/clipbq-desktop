import sys
import os
import json
import webbrowser
from http.server import HTTPServer
from threading import Thread
from PyQt6.QtCore import QByteArray
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
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtSvgWidgets import QSvgWidget
from supabase import create_client, Client
from dotenv import load_dotenv

from history_list import NumberedListWidget
from settings import SettingsDialog
from token_callback_handler import TokenCallbackHandler
from clipboard_monitor import ClipboardMonitor


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


env_path = os.path.join(resource_path(".env"))
load_dotenv(env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
LOGIN_PAGE_URL = os.environ.get("LOGIN_PAGE_URL")
TOKEN_FILE = os.path.expanduser("~/.clipbq_auth_token.json")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("clipBQ Cloud")
        self.resize(480, 550)
        self.supabase: Client = None
        self.monitor = None
        self.port = 9999

        self.init_ui()
        self.check_or_route_auth()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        status_controls_layout = QHBoxLayout()

        # Status Display
        self.status_label = QLabel("Status: Not Authenticated")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_controls_layout.addWidget(self.status_label)

        status_controls_layout.addStretch()

        sync_svg = b"""
                <svg xmlns="http://w3.org" viewBox="0 0 24 24" fill="#2196F3">
                    <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L4.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
                """
        pixmap_sync = QPixmap()
        pixmap_sync.loadFromData(QByteArray(sync_svg), "SVG")
        sync_icon = QIcon(pixmap_sync)

        red_trash_svg = b"""
                <svg xmlns="http://w3.org" viewBox="0 0 24 24" fill="#E53935">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
                """
        pixmap_delete = QPixmap()
        pixmap_delete.loadFromData(QByteArray(red_trash_svg), "SVG")
        delete_icon = QIcon(pixmap_delete)

        settings_svg = b"""
        <svg xmlns="http://w3.org" viewBox="0 0 24 24" fill="#333333">
            <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
        </svg>
        """
        pixmap_settings = QPixmap()
        pixmap_settings.loadFromData(QByteArray(settings_svg), "SVG")
        settings_icon = QIcon(pixmap_settings)

        self.btn_sync = QPushButton()
        self.btn_sync.setIcon(sync_icon)
        self.btn_sync.setToolTip("Cloud Sync")
        self.btn_sync.setFixedSize(30, 30)
        self.btn_sync.setVisible(False)
        self.btn_sync.clicked.connect(self.handle_sync_action)
        status_controls_layout.addWidget(self.btn_sync)

        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(delete_icon)
        self.btn_delete.setStyleSheet("color: red;")
        self.btn_delete.setToolTip("Clear all synced history")
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setVisible(False)
        self.btn_delete.clicked.connect(self.handle_delete_action)
        status_controls_layout.addWidget(self.btn_delete)

        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(settings_icon)
        self.btn_settings.setToolTip("Open settings panel")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setVisible(False)
        self.btn_settings.clicked.connect(self.handle_settings_action)
        status_controls_layout.addWidget(self.btn_settings)

        layout.addLayout(status_controls_layout)

        # History List View
        header_layout = QHBoxLayout()
        clipboard_svg = b"""
        <svg xmlns="http://w3.org" viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1" fill="#2196F3"/>
        </svg>
        """

        clipboard_svg_widget = QSvgWidget()
        clipboard_svg_widget.load(clipboard_svg)
        clipboard_svg_widget.setFixedSize(18, 18)

        title_text_label = QLabel("Clipboard Sync History:")

        header_layout.addWidget(clipboard_svg_widget)
        header_layout.addWidget(title_text_label)

        layout.addLayout(header_layout)
        self.history_list = NumberedListWidget()

        self.history_list.setVerticalScrollMode(
            self.history_list.ScrollMode.ScrollPerPixel
        )
        self.history_list.setHorizontalScrollMode(
            self.history_list.ScrollMode.ScrollPerPixel
        )

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

    def handle_sync_action(self):
        previous_text = self.status_label.text()
        previous_style = self.status_label.styleSheet()
        self.status_label.setText("Status: Syncing ...")
        self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        QApplication.processEvents()
        self.fetch_history()
        self.status_label.setText(previous_text)
        self.status_label.setStyleSheet(previous_style)

    def handle_delete_action(self):
        if self.history_list.count() == 0:
            return
        reply = QMessageBox.question(
            self,
            "Wipe Entire History?",
            "Are you sure you want to permanently delete ALL items from your clipboard sync history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return
        previous_text = self.status_label.text()
        previous_style = self.status_label.styleSheet()
        self.status_label.setText("Status: Clearing ...")
        self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        QApplication.processEvents()
        try:
            self.supabase.table("clipboard_history").delete().eq(
                "user_id", self.user_id
            ).execute()
            self.history_list.clear()
            QMessageBox.information(
                self, "Success", "Clipboard history has been completely cleared."
            )

        except Exception as e:
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return

            QMessageBox.critical(
                self,
                "Cloud Sync Error",
                f"Failed to clear clipboard history from clipBQ:\n{str(e)}",
            )
        finally:
            self.status_label.setText(previous_text)
            self.status_label.setStyleSheet(previous_style)

    def handle_settings_action(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def execute_logout_routine(self):
        try:
            self.supabase.auth.sign_out()
        except Exception as e:
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return
            print(f"Cloud sign out failed: {e}")
        self.supabase = None
        self.user_id = None
        self.access_token = None
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception as e:
                print(f"Could not delete local file index target: {e}")
        self.history_list.clear()
        self.token_input.clear()
        self.status_label.setText("Status: Not Authenticated")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        QMessageBox.information(
            self,
            "Logged Out",
            "You have been successfully logged out.",
        )
        try:
            os.execv(sys.executable, ["python"] + sys.argv)
        except Exception as e:
            print(f"Failed to auto-restart process: {e}")
            QApplication.quit()

    def execute_account_deletion_routine(self):
        try:
            self.supabase.table("clipboard_history").delete().eq(
                "user_id", self.user_id
            ).execute()
            self.supabase.rpc("delete_authenticated_user").execute()
            QMessageBox.information(
                self,
                "Account Deleted",
                "Your account and data have been permanently removed.",
            )
            self.execute_logout_routine()

        except Exception as e:
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return
            QMessageBox.critical(
                self,
                "Account Deletion Failed",
                f"Could not complete acount deletion flow:\n{str(e)}\n\n",
            )

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
            self.route_to_login()

    def route_to_login(self):
        self.status_label.setText("Redirecting to login portal in browser...")

        server_thread = Thread(target=self.await_browser_callback, daemon=True)
        server_thread.start()

        callback_url = f"{LOGIN_PAGE_URL}?redirect_port=9999"
        webbrowser.open(callback_url)

    def start_local_auth_server(self):
        server = HTTPServer(("localhost", self.port), TokenCallbackHandler)
        server.single_request = True
        server.handle_request()
        server.server_close()

    def await_browser_callback(self):
        global auth_callback_token
        auth_callback_token = None
        self.start_local_auth_server()
        if auth_callback_token:
            self.save_token(auth_callback_token)
            self.init_supabase_with_token(auth_callback_token)

    def handle_manual_token_submit(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Input Error", "Token field is empty.")
            return

        self.save_token(token)
        self.init_supabase_with_token(token)

    def paste_from_clipboard(self):
        try:
            clipboard = QApplication.clipboard()
            clip_text = clipboard.text()
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

            self.status_label.setText(
                f"Status: Authenticated ({user_response.user.email})"
            )
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.token_input.setVisible(False)
            self.btn_open_portal.setVisible(False)
            self.btn_paste_clipboard.setVisible(False)
            self.btn_submit_token.setVisible(False)

            # ----- UI Controls -------
            self.btn_sync.setVisible(True)
            self.btn_delete.setVisible(True)
            self.btn_settings.setVisible(True)

            self.fetch_history()
            self.start_monitoring()
        except Exception as e:
            self.status_label.setText("Status: Authentication Failed")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return
            QMessageBox.critical(
                self,
                "Auth Error",
                f"Failed to authenticate. Please verify auth token: {str(e)}",
            )

    def fetch_history(self):
        try:
            response = (
                self.supabase.table("clipboard_history")
                .select("content, created_at")
                .order("created_at", desc=True)
                .execute()
            )

            if self.history_list.count() > 0:
                self.history_list.clear()

            for record in response.data:
                item_text = f"{record['content']}"
                self.history_list.append_item(item_text)

        except Exception as e:
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return
            QMessageBox.critical(
                self, "Fetch Error", f"Could not load history: {str(e)}"
            )
        finally:
            if "response" in locals():
                del response

    def start_monitoring(self):
        self.monitor = ClipboardMonitor(parent=self)
        self.monitor.new_clip_signal.connect(self.upload_clip)
        self.monitor.error_signal.connect(self.show_clipboard_error)

    def upload_clip(self, content: str):
        try:
            data = {"user_id": self.user_id, "content": content}
            response = self.supabase.table("clipboard_history").insert(data).execute()
            if response.data:
                self.history_list.prepend_item(f"{content}")
        except Exception as e:
            if "[Errno -2]" in str(e):
                QMessageBox.critical(
                    self,
                    "Network Error",
                    "Please check your Internet connection and try again.",
                )
                return
            print(f"Error pushing clipboard entry: {e}")

    def show_clipboard_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event):
        self.monitor.stop()
        event.accept()
