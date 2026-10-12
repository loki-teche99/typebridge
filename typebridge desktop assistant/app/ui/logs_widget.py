from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QFileDialog
from app.core.events import EventBus
from app.core.logger import StructuredLogger
import os

class LogsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = EventBus()
        self.logger = StructuredLogger()
        self._setup_ui()
        self.logger.signals.log_line.connect(self.append_log)
        
        for line in self.logger.log_deque:
            self.append_log(line)
            
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.text_edit.clear)
        btn_export = QPushButton("Export Logs")
        btn_export.clicked.connect(self.export_logs)
        btn_diag = QPushButton("🩺 Support Diagnostics")
        btn_diag.clicked.connect(self.export_diagnostics)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_diag)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
    def append_log(self, line):
        color = "white"
        if "[WARNING]" in line: color = "yellow"
        elif "[ERROR]" in line: color = "red"
        
        html = f'<span style="color: {color};">{line}</span>'
        self.text_edit.append(html)
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())
        
    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Logs", os.path.expanduser("~"), "Log Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())

    def export_diagnostics(self):
        import platform
        import sys
        from PyQt6.QtWidgets import QMessageBox
        from app.core.config import ConfigManager
        cfg = ConfigManager()
        report = [
            "==================================================",
            "   TYPEBRIDGE DESKTOP SUPPORT & DIAGNOSTIC BUNDLE",
            "==================================================",
            f"App Version       : {cfg.get('app_version', '1.0.0')}",
            f"Platform          : {platform.platform()} ({platform.architecture()[0]})",
            f"Python Runtime    : {sys.version.split()[0]}",
            f"Canonical Repo    : {cfg.get('github_repo', 'loki-teche99/typebridge')}",
            f"Official Website  : https://typebridge.42web.io/",
            f"Server Port       : {cfg.get('server_port', 8765)}",
            f"Typing Delay      : {cfg.get('typing_delay_ms', 30)} ms (Human-like: {cfg.get('human_like_delay', False)})",
            f"Code Mode         : {cfg.get('code_mode', 'raw')}",
            "--------------------------------------------------",
            "Recent Sanitized Logs:",
            "--------------------------------------------------",
            self.text_edit.toPlainText().strip() or "(No logs recorded yet)",
            "=================================================="
        ]
        text_report = "\n".join(report)
        path, _ = QFileDialog.getSaveFileName(self, "Save Diagnostic Bundle", os.path.expanduser("~"), "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text_report)
            QMessageBox.information(self, "Diagnostics Exported", f"Diagnostic report saved successfully to:\n{path}")
