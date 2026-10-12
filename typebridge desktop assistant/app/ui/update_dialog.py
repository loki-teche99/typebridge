"""
TypeBridge Desktop - Cyber-Glassmorphism Update Dialog
======================================================
Prompts user with release details and changelog, downloads
installer with live progress, and triggers in-place silent upgrade.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.core.updater import UpdateDownloaderThread, launch_silent_installer


class UpdateDialog(QDialog):
    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.downloader: UpdateDownloaderThread | None = None

        self.setWindowTitle("TypeBridge Software Update")
        self.setFixedSize(520, 480)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Card container with cyber-glass styling
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel("🚀")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 22))
        title_box.addWidget(icon_lbl)

        header_text_box = QVBoxLayout()
        title_lbl = QLabel("TypeBridge Update Available")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")

        version_str = f"Version {self.update_info.get('version', '')} is ready to install"
        sub_lbl = QLabel(version_str)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")

        header_text_box.addWidget(title_lbl)
        header_text_box.addWidget(sub_lbl)
        title_box.addLayout(header_text_box)
        title_box.addStretch()
        card_layout.addLayout(title_box)

        # Release Info Badge
        badge_box = QHBoxLayout()
        lbl_size = QLabel(f"📦 Size: {self.update_info.get('size_mb', 0)} MB")
        lbl_size.setStyleSheet("background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: bold;")

        lbl_cdn = QLabel("⚡ GitHub Fast Global CDN")
        lbl_cdn.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: bold;")

        badge_box.addWidget(lbl_size)
        badge_box.addWidget(lbl_cdn)
        badge_box.addStretch()
        card_layout.addLayout(badge_box)

        # Changelog / Release Notes
        lbl_changes = QLabel("What's New in this Release:")
        lbl_changes.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 12px; margin-top: 4px;")
        card_layout.addWidget(lbl_changes)

        self.txt_notes = QTextEdit()
        self.txt_notes.setReadOnly(True)
        raw_notes = self.update_info.get("body", "General bug fixes and performance improvements.")
        self.txt_notes.setPlainText(raw_notes)
        self.txt_notes.setStyleSheet(
            "background: rgba(15, 23, 42, 0.6); color: #e2e8f0; border: 1px solid #334155; "
            "border-radius: 8px; font-family: 'Segoe UI', sans-serif; font-size: 12px; padding: 8px;"
        )
        self.txt_notes.setFixedHeight(140)
        card_layout.addWidget(self.txt_notes)

        # Progress Section (Initially hidden)
        self.lbl_status = QLabel("Click 'Update & Restart' to download and install automatically.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #1e293b;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #10b981);
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)

        # Action Buttons
        btn_box = QHBoxLayout()
        self.btn_later = QPushButton("Remind Me Later")
        self.btn_later.setObjectName("secondaryBtn")
        self.btn_later.clicked.connect(self.reject)

        self.btn_update = QPushButton("🚀   Update & Restart Now")
        self.btn_update.setObjectName("primaryBtn")
        self.btn_update.setStyleSheet("""
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #0284c7);
            }
            QPushButton#primaryBtn:disabled {
                background: #475569;
                color: #94a3b8;
            }
        """)
        self.btn_update.clicked.connect(self._start_download)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_later)
        btn_box.addWidget(self.btn_update)
        layout.addLayout(btn_box)

    def _start_download(self):
        download_url = self.update_info.get("download_url")
        version = self.update_info.get("version", "latest")

        if not download_url:
            QMessageBox.warning(
                self, "Cannot Download",
                "No Windows setup executable was found in this release on GitHub.\n"
                "Please download it manually from the release page."
            )
            return

        self.btn_update.setEnabled(False)
        self.btn_later.setEnabled(False)
        self.progress_bar.show()
        self.lbl_status.setText("Connecting to GitHub CDN...")

        self.downloader = UpdateDownloaderThread(
            download_url, version, expected_sha256=self.update_info.get("sha256")
        )
        self.downloader.download_progress.connect(self._on_progress)
        self.downloader.download_finished.connect(self._on_finished)
        self.downloader.download_failed.connect(self._on_failed)
        self.downloader.start()

    def _on_progress(self, pct: int, downloaded: int, total: int):
        self.progress_bar.setValue(pct)
        d_mb = downloaded / (1024 * 1024)
        t_mb = total / (1024 * 1024) if total > 0 else 0
        if pct >= 100:
            self.lbl_status.setText("Verifying package SHA-256 integrity...")
        else:
            self.lbl_status.setText(f"Stage 3/5: Downloading ({d_mb:.1f} MB / {t_mb:.1f} MB • {pct}%)...")

    def _on_finished(self, installer_path: str):
        self.lbl_status.setText("Stage 5/5: Verified! Launching silent in-place upgrade...")
        self.lbl_status.setStyleSheet("color: #34d399; font-weight: bold;")
        self.progress_bar.setValue(100)

        # Launch the silent installer and restart
        try:
            launch_silent_installer(installer_path)
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Failed to start installer: {e}")
            self.btn_later.setEnabled(True)

    def _on_failed(self, error: str):
        self.lbl_status.setText(f"Error: {error}")
        self.lbl_status.setStyleSheet("color: #f87171;")
        self.btn_update.setEnabled(True)
        self.btn_later.setEnabled(True)
        QMessageBox.warning(self, "Update Failed", f"Could not download update:\n{error}")

    def closeEvent(self, event):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait(1000)
        super().closeEvent(event)
