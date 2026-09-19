from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox


class SettingsDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Settings")
        self.resize(320, 180)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(QLabel("<b>Account Options</b>"))

        self.btn_logout = QPushButton("Log Out of Session")
        self.btn_logout.setFixedHeight(35)
        self.btn_logout.clicked.connect(self.handle_logout)
        layout.addWidget(self.btn_logout)

        self.btn_delete_account = QPushButton("Delete Account Permanently")
        self.btn_delete_account.setFixedHeight(35)

        self.btn_delete_account.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        self.btn_delete_account.clicked.connect(self.handle_account_deletion)
        layout.addWidget(self.btn_delete_account)

        layout.addStretch()

    def handle_logout(self):

        reply = QMessageBox.question(
            self,
            "Confirm Log Out",
            "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()
            self.main_window.execute_logout_routine()

    def handle_account_deletion(self):

        reply1 = QMessageBox.warning(
            self,
            "CRITICAL WARNING",
            "Are you absolutely sure you want to permanently delete your account?\n\n"
            "This will instantly erase your profile, credentials, and ALL synchronized cloud clipboard history data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply1 == QMessageBox.StandardButton.Yes:
            reply2 = QMessageBox.critical(
                self,
                "FINAL CONFIRMATION",
                "This action cannot be undone. Final confirmation: Delete account?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply2 == QMessageBox.StandardButton.Yes:
                self.accept()
                self.main_window.execute_account_deletion_routine()
