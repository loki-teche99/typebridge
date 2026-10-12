import os
import sys
import subprocess
import winreg
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSlider, QCheckBox,
    QComboBox, QSpinBox, QHBoxLayout, QPushButton, QLabel, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from app.core.config import ConfigManager

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RUN_NAME = "TypeBridge"


def set_run_at_startup(enable: bool):
    """Adds or removes the application from the Windows CurrentVersion\\Run registry key."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        if enable:
            if getattr(sys, 'frozen', False):
                app_path = f'"{sys.executable}"'
            else:
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'main.py'))
                app_path = f'"{sys.executable}" "{main_py}"'
            winreg.SetValueEx(key, APP_RUN_NAME, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, APP_RUN_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to update startup registry: {e}")


def is_run_at_startup() -> bool:
    """Checks if TypeBridge is configured in the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_QUERY_VALUE)
        val, _ = winreg.QueryValueEx(key, APP_RUN_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.setWindowTitle("Settings — TypeBridge")
        self.setFixedSize(480, 490)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        form.setSpacing(12)

        # Typing delay slider
        delay_box = QHBoxLayout()
        self.slider_delay = QSlider(Qt.Orientation.Horizontal)
        self.slider_delay.setRange(5, 200)
        current_delay = self.config.get('typing_delay_ms') or 30
        self.slider_delay.setValue(current_delay)
        self.lbl_delay_val = QLabel(f"{current_delay} ms")
        self.lbl_delay_val.setFixedWidth(50)
        self.slider_delay.valueChanged.connect(lambda v: self.lbl_delay_val.setText(f"{v} ms"))
        delay_box.addWidget(self.slider_delay)
        delay_box.addWidget(self.lbl_delay_val)
        form.addRow("Typing Delay:", delay_box)

        self.chk_human = QCheckBox("Add human-like natural speed variation")
        self.chk_human.setChecked(bool(self.config.get('human_like_delay')))
        form.addRow("Natural Rhythm:", self.chk_human)

        self.chk_auto = QCheckBox("Start typing immediately when text arrives")
        self.chk_auto.setChecked(bool(self.config.get('auto_type')))
        form.addRow("Auto-type:", self.chk_auto)

        self.cmb_code_mode = QComboBox()
        self.cmb_code_mode.addItem("Smart Web IDE (HackerEarth, LeetCode, VS Code)", "ide")
        self.cmb_code_mode.addItem("Plain Text / Notepad (Full Explicit Indent)", "java_perfect")
        self.cmb_code_mode.addItem("Raw Exact (No adjustment)", "raw")
        mode_val = self.config.get('code_mode')
        idx = self.cmb_code_mode.findData(mode_val)
        if idx >= 0:
            self.cmb_code_mode.setCurrentIndex(idx)
        form.addRow("Code Typing Mode:", self.cmb_code_mode)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(['dark', 'light'])
        self.cmb_theme.setCurrentText(self.config.get('theme') or 'dark')
        form.addRow("Theme:", self.cmb_theme)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(self.config.get('server_port') or 8765)
        form.addRow("Server Port:", self.spin_port)

        self.chk_startup = QCheckBox("Launch TypeBridge on Windows startup")
        self.chk_startup.setChecked(is_run_at_startup())
        form.addRow("Windows Startup:", self.chk_startup)

        self.chk_auto_update = QCheckBox("Check for updates automatically on startup")
        self.chk_auto_update.setChecked(bool(self.config.get('auto_check_updates', True)))
        form.addRow("Auto-Update Check:", self.chk_auto_update)

        # Windows Firewall helper
        btn_fw = QPushButton("🛡️ Verify / Add Firewall Rule")
        btn_fw.clicked.connect(self._configure_firewall)
        form.addRow("Firewall Status:", btn_fw)

        layout.addLayout(form)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 6px 16px;")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _configure_firewall(self):
        port = self.spin_port.value()
        try:
            # Check if rule exists
            check_cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=TypeBridge WSS']
            res = subprocess.run(check_cmd, capture_output=True, text=True)
            if "TypeBridge WSS" in res.stdout:
                QMessageBox.information(self, "Firewall", f"✅ Windows Firewall rule 'TypeBridge WSS' is already active for port {port}.")
                return

            # Request elevated rule creation via PowerShell Start-Process -Verb runAs
            ps_cmd = f'Start-Process netsh -ArgumentList "advfirewall firewall add rule name=\\"TypeBridge WSS\\" dir=in action=allow protocol=TCP localport={port}" -Verb runAs -Wait'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
            QMessageBox.information(self, "Firewall", f"✅ Successfully added Windows Firewall inbound rule for port {port}!")
        except Exception as e:
            QMessageBox.warning(self, "Firewall", f"Could not configure firewall rule automatically: {e}\n\nYou can manually run in Administrator PowerShell:\nnetsh advfirewall firewall add rule name=\"TypeBridge WSS\" dir=in action=allow protocol=TCP localport={port}")

    def save_settings(self):
        self.config.set('typing_delay_ms', self.slider_delay.value())
        self.config.set('human_like_delay', self.chk_human.isChecked())
        self.config.set('auto_type', self.chk_auto.isChecked())
        self.config.set('code_mode', self.cmb_code_mode.currentData())
        self.config.set('theme', self.cmb_theme.currentText())
        self.config.set('server_port', self.spin_port.value())
        self.config.set('start_with_windows', self.chk_startup.isChecked())
        self.config.set('github_repo', 'v4358137-lang/typebridge')
        self.config.set('auto_check_updates', self.chk_auto_update.isChecked())

        set_run_at_startup(self.chk_startup.isChecked())

        self.accept()
