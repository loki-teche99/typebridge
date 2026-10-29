"""
TypeBridge Desktop - Main Window
Modern glassmorphic UI window showing connection status, typing progress, controls, and logs.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QProgressBar, QPushButton, QSlider,
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont

from app.core.config import ConfigManager
from app.core.events import EventBus
from app.typing_engine.typing_queue import TypingQueue
from app.typing_engine.typing_worker import TypingWorker
from app.ui.logs_widget import LogsWidget
from app.network.bluetooth_server import BluetoothServer
from app.ui.pairing_dialog import PairingDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.styles import get_stylesheet
from app.core.updater import UpdateCheckerThread, CURRENT_VERSION
from app.ui.update_dialog import UpdateDialog


class MainWindow(QMainWindow):
    def __init__(self, ws_server, pairing_manager, tray_app):
        super().__init__()
        self.ws_server       = ws_server
        self.pairing_manager = pairing_manager
        self.tray_app        = tray_app
        self.config          = ConfigManager()
        self.events          = EventBus()
        self.queue           = TypingQueue()
        self._is_paused      = False
        self._transports     = {
            'wifi': {'connected': False, 'device_name': '', 'latency_ms': 0},
            'bluetooth': {'connected': False, 'device_name': '', 'latency_ms': 0},
        }

        # Typing worker runs in its own thread
        self.typing_worker = TypingWorker()
        self.typing_worker.progress_signal.connect(self._on_typing_progress)
        self.typing_worker.complete_signal.connect(self._on_typing_complete)
        self.typing_worker.ack_needed.connect(self.on_ack_needed)
        self.typing_worker.start()

        # Bluetooth SPP transport
        self.bt_server = BluetoothServer(self.pairing_manager)
        self.bt_server.connection_signal.connect(self.on_connection_changed)
        self.bt_server.text_signal.connect(self.on_text_received)
        self.bt_server.control_signal.connect(self.on_control_received)
        self.bt_server.pairing_signal.connect(self.on_pairing_complete)

        # Start Bluetooth transport
        self.bt_server.start()

        # Window setup
        self.setWindowTitle("TypeBridge Desktop Assistant")
        self.setMinimumSize(680, 600)
        self.resize(740, 640)
        self.setStyleSheet(get_stylesheet(self.config.get('theme') or 'dark'))

        self._build_ui()

        # Remote auto-update check (runs in background on startup and checks every 1 hour)
        self.update_checker = None
        if self.config.get('auto_check_updates', True):
            self.check_for_updates(silent=True, is_manual=False)
            self._update_timer = QTimer(self)
            self._update_timer.timeout.connect(lambda: self.check_for_updates(silent=True, is_manual=False))
            self._update_timer.start(3600 * 1000)  # Check every 1 hour (7-day gate enforced)

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # --- Header --------------------------------------------------- #
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("TypeBridge")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setObjectName("appTitle")

        subtitle = QLabel("Wireless Mobile-to-PC Typing Bridge")
        subtitle.setObjectName("dimLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr.addLayout(title_box)

        hdr.addStretch()

        self._lbl_status = QLabel("🔴  Disconnected")
        self._lbl_status.setObjectName("statusBadge")
        self._lbl_status.setProperty("connected", "false")
        self._lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(self._lbl_status)
        layout.addLayout(hdr)

        # --- Device info card ----------------------------------------- #
        dev_card = self._card()
        dev_inner = QVBoxLayout(dev_card)
        dev_inner.setSpacing(6)

        row1 = QHBoxLayout()
        self._lbl_device = QLabel("📱  No device paired")
        self._lbl_device.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._lbl_security = QLabel("🔒  AES-256-GCM Encrypted")
        self._lbl_security.setObjectName("dimLabel")
        row1.addWidget(self._lbl_device)
        row1.addStretch()
        row1.addWidget(self._lbl_security)
        dev_inner.addLayout(row1)

        row2 = QHBoxLayout()
        self._lbl_latency = QLabel("Latency: —")
        self._lbl_latency.setObjectName("dimLabel")
        self._lbl_ip_info = QLabel(f"Server Port: {self.config.get('server_port') or 8765}")
        self._lbl_ip_info.setObjectName("dimLabel")
        row2.addWidget(self._lbl_latency)
        row2.addStretch()
        row2.addWidget(self._lbl_ip_info)
        dev_inner.addLayout(row2)

        layout.addWidget(dev_card)

        # --- Typing progress card ------------------------------------- #
        prog_card = self._card()
        prog_inner = QVBoxLayout(prog_card)
        prog_inner.setSpacing(8)

        prog_hdr = QHBoxLayout()
        lbl_prog_title = QLabel("Currently Typing:")
        lbl_prog_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._lbl_prog_stats = QLabel("Idle")
        self._lbl_prog_stats.setObjectName("dimLabel")
        prog_hdr.addWidget(lbl_prog_title)
        prog_hdr.addStretch()
        prog_hdr.addWidget(self._lbl_prog_stats)
        prog_inner.addLayout(prog_hdr)

        self._lbl_current = QLabel("Waiting for text from Android…")
        self._lbl_current.setWordWrap(True)
        self._lbl_current.setObjectName("dimLabel")
        self._lbl_current.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; color: #cbd5e1; background: transparent;")

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(10)

        prog_inner.addWidget(self._lbl_current)
        prog_inner.addWidget(self._progress)
        layout.addWidget(prog_card)

        # --- Controls ------------------------------------------------- #
        ctrl_card = self._card()
        ctrl_inner = QVBoxLayout(ctrl_card)
        ctrl_inner.setSpacing(12)

        btn_row = QHBoxLayout()
        self._btn_pause = QPushButton("⏸   Pause Typing")
        self._btn_pause.setObjectName("primaryBtn")
        self._btn_pause.clicked.connect(self.toggle_pause)

        self._btn_stop = QPushButton("⏹   Stop")
        self._btn_stop.setObjectName("dangerBtn")
        self._btn_stop.clicked.connect(self.stop_typing)

        btn_row.addWidget(self._btn_pause, stretch=3)
        btn_row.addWidget(self._btn_stop, stretch=1)
        ctrl_inner.addLayout(btn_row)

        # Speed slider & Quick Presets
        spd_col = QVBoxLayout()
        spd_col.setSpacing(6)

        spd_row = QHBoxLayout()
        lbl_spd = QLabel("⚡ Typing Speed:")
        lbl_spd.setObjectName("dimLabel")
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 100)
        current_delay = int(self.config.get('typing_delay_ms') or 5)
        self._slider.setValue(current_delay)
        self._slider.valueChanged.connect(self._on_speed_change)

        self._lbl_delay = QLabel(self._format_speed_label(current_delay))
        self._lbl_delay.setMinimumWidth(85)
        self._lbl_delay.setStyleSheet("font-weight: bold; color: #38bdf8;")

        spd_row.addWidget(lbl_spd)
        spd_row.addWidget(self._slider)
        spd_row.addWidget(self._lbl_delay)
        spd_col.addLayout(spd_row)

        # Speed Preset Pills
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        presets = [
            ("⚡ Turbo (1ms)", 1),
            ("🚀 Ultra (4ms)", 4),
            ("⚡ Fast (10ms)", 10),
            ("✍️ Human (30ms)", 30),
        ]
        for p_label, p_val in presets:
            btn_p = QPushButton(p_label)
            btn_p.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #334155;
                    color: #38bdf8;
                    border-color: #38bdf8;
                }
            """)
            btn_p.clicked.connect(lambda checked=False, tv=p_val: self._slider.setValue(tv))
            preset_row.addWidget(btn_p)
        preset_row.addStretch()
        spd_col.addLayout(preset_row)

        ctrl_inner.addLayout(spd_col)

        layout.addWidget(ctrl_card)

        # --- Logs (collapsible) --------------------------------------- #
        self._logs = LogsWidget()
        self._logs.hide()
        layout.addWidget(self._logs)

        # --- Bottom bar ----------------------------------------------- #
        bot = QHBoxLayout()
        btn_pair = QPushButton("🔗   Pair Device")
        btn_pair.setObjectName("primaryBtn")
        btn_pair.clicked.connect(self.show_pairing)

        btn_settings = QPushButton("⚙   Settings")
        btn_settings.setObjectName("secondaryBtn")
        btn_settings.clicked.connect(self.show_settings)

        btn_logs = QPushButton("📋   Logs")
        btn_logs.setObjectName("secondaryBtn")
        btn_logs.clicked.connect(lambda: self._logs.setVisible(not self._logs.isVisible()))

        btn_mobile = QPushButton("📱   Get Mobile App")
        btn_mobile.setObjectName("secondaryBtn")
        btn_mobile.setToolTip("Download TypeBridge Mobile for Android (https://typebridge.42web.io/)")
        btn_mobile.clicked.connect(self.open_mobile_download)

        bot.addWidget(btn_pair)
        bot.addWidget(btn_mobile)
        bot.addWidget(btn_settings)
        bot.addWidget(btn_logs)
        bot.addStretch()

        lbl_author = QLabel("Crafted by Lokesh N")
        lbl_author.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        bot.addWidget(lbl_author)
        bot.addSpacing(6)

        lbl_ver = QLabel(f"v{self.config.get('app_version', '1.0.3')}")
        lbl_ver.setObjectName("dimLabel")
        bot.addWidget(lbl_ver)

        if getattr(self.config, 'is_msix', False):
            self.btn_update = QPushButton("🏪 Microsoft Store Edition")
            self.btn_update.setObjectName("linkBtn")
            self.btn_update.setToolTip("TypeBridge is installed from the Microsoft Store. Updates are managed automatically by Windows.")
            self.btn_update.setStyleSheet("""
                QPushButton#linkBtn {
                    background: transparent;
                    color: #38bdf8;
                    border: none;
                    font-size: 11px;
                    padding: 2px 6px;
                }
                QPushButton#linkBtn:hover {
                    color: #7dd3fc;
                    text-decoration: underline;
                }
            """)
            self.btn_update.clicked.connect(self._open_store_page)
        else:
            self.btn_update = QPushButton("✨ Check for Updates")
            self.btn_update.setObjectName("linkBtn")
            self.btn_update.setStyleSheet("""
                QPushButton#linkBtn {
                    background: transparent;
                    color: #38bdf8;
                    border: none;
                    font-size: 11px;
                    text-decoration: underline;
                    padding: 2px 6px;
                    cursor: pointer;
                }
                QPushButton#linkBtn:hover {
                    color: #7dd3fc;
                }
            """)
            self.btn_update.clicked.connect(lambda: self.check_for_updates(silent=False, is_manual=True))

        bot.addWidget(self.btn_update)
        layout.addLayout(bot)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _card() -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        return frame

    # ------------------------------------------------------------------ #
    #  Slots (called from Qt main thread via signals)
    # ------------------------------------------------------------------ #
    @pyqtSlot(dict)
    def on_connection_changed(self, data: dict):
        status    = data.get('status', 'disconnected')
        name      = data.get('device_name', '')
        latency   = data.get('latency_ms', 0)
        transport = str(data.get('transport', 'wifi')).lower()

        if transport not in self._transports:
            transport = 'wifi'

        is_conn = (status == 'connected')
        self._transports[transport]['connected'] = is_conn
        if is_conn:
            self._transports[transport]['device_name'] = name
            self._transports[transport]['latency_ms'] = latency

        # Prioritize Wi-Fi if connected, else Bluetooth, else Disconnected
        if self._transports['wifi']['connected']:
            t_data = self._transports['wifi']
            dev_name = t_data['device_name'] or 'Android Device'
            lat = t_data['latency_ms']
            self._lbl_status.setText(f"🟢   Connected via WiFi • {lat}ms")
            self._lbl_status.setProperty("connected", "true")
            self._lbl_device.setText(f"📱   {dev_name}")
            self._lbl_latency.setText(f"Latency: {lat} ms (RTT)")
            self.tray_app.update_status(True)
        elif self._transports['bluetooth']['connected']:
            t_data = self._transports['bluetooth']
            dev_name = t_data['device_name'] or 'Android Device'
            lat = t_data['latency_ms']
            self._lbl_status.setText(f"🟢   Connected via Bluetooth • {lat}ms")
            self._lbl_status.setProperty("connected", "true")
            self._lbl_device.setText(f"📱   {dev_name}")
            self._lbl_latency.setText(f"Latency: {lat} ms (RTT)")
            self.tray_app.update_status(True)
        else:
            self._lbl_status.setText("🔴   Disconnected")
            self._lbl_status.setProperty("connected", "false")
            self._lbl_device.setText("📱   No device paired")
            self._lbl_latency.setText("Latency: —")
            self.tray_app.update_status(False)

        self._lbl_status.style().unpolish(self._lbl_status)
        self._lbl_status.style().polish(self._lbl_status)

    @pyqtSlot(dict)
    def on_text_received(self, data: dict):
        text   = data.get('text', '')
        msg_id = data.get('msg_id', '')
        if not text or not msg_id:
            return

        self.queue.enqueue(msg_id, text)
        preview = text[:80].replace('\n', '↵ ') + ("…" if len(text) > 80 else "")
        self._lbl_current.setText(preview)
        self._progress.setMaximum(len(text))
        self._progress.setValue(0)
        self._lbl_prog_stats.setText(f"0% (0 / {len(text)} chars)")

        if self.config.get('auto_type'):
            self.queue.mark_typing(msg_id)
            self.typing_worker.enqueue(text, msg_id)

    @pyqtSlot(int, int, str)
    def _on_typing_progress(self, done: int, total: int, msg_id: str):
        self._progress.setMaximum(total)
        self._progress.setValue(done)
        pct = int((done / total) * 100) if total > 0 else 0
        self._lbl_prog_stats.setText(f"Typing... {pct}% ({done} / {total} chars)")

    @pyqtSlot(str)
    def _on_typing_complete(self, msg_id: str):
        self.queue.mark_done(msg_id)
        self._lbl_current.setText("Waiting for text from Android…")
        self._progress.setValue(0)
        self._lbl_prog_stats.setText("✅ Completed")

    @pyqtSlot(str)
    def on_ack_needed(self, msg_id: str):
        self.ws_server.schedule_ack(msg_id)

    @pyqtSlot(dict)
    def on_pairing_complete(self, data: dict):
        if data.get('success'):
            self.tray_app.show_message(
                "Pairing Successful", f"Paired with {data.get('device_name', 'device')}"
            )

    @pyqtSlot(dict)
    def on_control_received(self, data: dict):
        cmd = data.get('command', '').upper()
        if cmd == 'PAUSE':
            if not self._is_paused:
                self.toggle_pause()
        elif cmd == 'RESUME':
            if self._is_paused:
                self.toggle_pause()
        elif cmd == 'STOP':
            self.stop_typing()
        elif cmd == 'MODE_JAVA_PERFECT':
            self.config.set('code_mode', 'java_perfect')
            self._lbl_current.setText("⚡ Mode: Java Perfect 4-Space Structure")
        elif cmd == 'MODE_IDE':
            self.config.set('code_mode', 'ide')
            self._lbl_current.setText("💻 Mode: Smart IDE Auto-Indent")
        elif cmd == 'MODE_RAW':
            self.config.set('code_mode', 'raw')
            self._lbl_current.setText("📝 Mode: Raw Exact Characters")

    # ------------------------------------------------------------------ #
    #  Controls
    # ------------------------------------------------------------------ #
    def toggle_pause(self):
        if self._is_paused:
            self.typing_worker.resume()
            self._btn_pause.setText("⏸   Pause Typing")
            self._is_paused = False
        else:
            self.typing_worker.pause()
            self._btn_pause.setText("▶   Resume Typing")
            self._is_paused = True

    def stop_typing(self):
        self.typing_worker.clear_queue()
        self.queue.clear_pending()
        self._lbl_current.setText("⏹ Typing stopped.")
        self._progress.setValue(0)
        self._lbl_prog_stats.setText("Stopped")
        if self._is_paused:
            self.toggle_pause()

    def _format_speed_label(self, val: int) -> str:
        if val <= 1:
            return f"{val} ms (Turbo)"
        elif val <= 4:
            return f"{val} ms (Ultra)"
        elif val <= 10:
            return f"{val} ms (Fast)"
        else:
            return f"{val} ms"

    def _on_speed_change(self, val: int):
        self.config.set('typing_delay_ms', val)
        self._lbl_delay.setText(self._format_speed_label(val))

    def show_pairing(self):
        dlg = PairingDialog(self.pairing_manager, self.ws_server, self)
        dlg.exec()

    def show_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.setStyleSheet(get_stylesheet(self.config.get('theme') or 'dark'))

    def open_mobile_download(self):
        """Open official download page for TypeBridge Android Mobile App."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://typebridge.42web.io/"))

    def _open_store_page(self):
        """Open official Microsoft Store product listing for updates."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("ms-windows-store://pdp/?ProductId=9PL56S4CL4NW"))

    def closeEvent(self, event):
        # Hide to tray instead of quitting
        event.ignore()
        self.hide()
        self.tray_app.show_message(
            "TypeBridge", "Still running in system tray. Right-click tray icon to quit."
        )

    def shutdown(self):
        """Cleanup resources on application exit."""
        if hasattr(self, 'bt_server'):
            self.bt_server.stop()
        if hasattr(self, 'typing_worker'):
            self.typing_worker.stop()

    # ------------------------------------------------------------------ #
    #  Remote Auto-Updater
    # ------------------------------------------------------------------ #
    def check_for_updates(self, silent: bool = False, is_manual: bool = False):
        """Initiate background GitHub release check with duplicate in-flight protection."""
        if self.update_checker and self.update_checker.isRunning():
            return

        self._check_silent = silent
        if not silent:
            self.btn_update.setText("Checking GitHub...")
            self.btn_update.setEnabled(False)

        self.update_checker = UpdateCheckerThread(is_manual=is_manual, parent=self)
        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.no_update_found.connect(self._on_no_update_found)
        self.update_checker.check_failed.connect(self._on_update_check_failed)
        self.update_checker.start()

    def _on_update_available(self, update_info: dict):
        ver = update_info.get('version', '')
        self.btn_update.setText(f"🔥 Update v{ver} Available!")
        self.btn_update.setEnabled(True)
        self.btn_update.setStyleSheet("""
            QPushButton#linkBtn {
                background: rgba(239, 68, 68, 0.2);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton#linkBtn:hover {
                background: rgba(239, 68, 68, 0.3);
            }
        """)
        # Open update dialog
        dlg = UpdateDialog(update_info, self)
        dlg.exec()

    def _on_no_update_found(self, current_ver: str):
        self.btn_update.setText("✨ Up to date")
        self.btn_update.setEnabled(True)
        if not getattr(self, '_check_silent', False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "TypeBridge Updater",
                f"You are running the latest version (v{current_ver})!\n\nNo updates are needed."
            )

    def _on_update_check_failed(self, err_msg: str):
        self.btn_update.setText("✨ Check for Updates")
        self.btn_update.setEnabled(True)
        if not getattr(self, '_check_silent', False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "TypeBridge Updater",
                f"Could not check for updates:\n\n{err_msg}"
            )
