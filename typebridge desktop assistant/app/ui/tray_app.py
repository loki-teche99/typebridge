"""
TypeBridge Desktop - System Tray Application
Owns the main window, WebSocket server thread, and mDNS discovery.
"""
import os
import sys
import threading
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QPen
from PyQt6.QtCore import QObject, Qt

from app.network.websocket_server import WebSocketServer
from app.network.discovery import DiscoveryManager
from app.security.pairing_manager import PairingManager
from app.ui.main_window import MainWindow

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TrayApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app

        # Resolve asset paths
        self.icon_path = os.path.join(BASE_DIR, 'assets', 'icon.png')
        if not os.path.exists(self.icon_path):
            self.icon_path = os.path.join(BASE_DIR, 'assets', 'icon.ico')

        # Create shared server + pairing manager FIRST
        self.pairing_manager = PairingManager()
        self.pairing_manager.generate_pin()
        self.ws_server = WebSocketServer(self.pairing_manager)
        self.discovery = DiscoveryManager()

        # Tray icon
        self.icon = QSystemTrayIcon()
        self._set_icon_color("#e94560")  # red = disconnected
        self.icon.setVisible(True)
        self.icon.setToolTip("TypeBridge – Disconnected")

        # Main window
        self.main_window = MainWindow(self.ws_server, self.pairing_manager, self)
        if os.path.exists(self.icon_path):
            self.main_window.setWindowIcon(QIcon(self.icon_path))

        self._setup_menu()
        self.icon.activated.connect(self._on_tray_activated)

        # Wire server signals to main window
        self.ws_server.ack_signal.connect(self.main_window.on_ack_needed)
        self.ws_server.connection_signal.connect(self.main_window.on_connection_changed)
        self.ws_server.text_signal.connect(self.main_window.on_text_received)
        self.ws_server.pairing_signal.connect(self.main_window.on_pairing_complete)
        self.ws_server.control_signal.connect(self.main_window.on_control_received)

        # Start WebSocket server in background daemon thread
        self.ws_thread = threading.Thread(target=self.ws_server.start, daemon=True, name="WS-Server")
        self.ws_thread.start()

        # Start mDNS discovery advertisement safely
        try:
            self.discovery.start()
        except Exception as e:
            self.logger.warning(f"Failed to start discovery advertisement: {e}")

    # ------------------------------------------------------------------ #
    #  Icon helpers
    # ------------------------------------------------------------------ #
    def _create_icon(self, hex_color: str) -> QIcon:
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw base app icon if available
        if os.path.exists(self.icon_path):
            base_pixmap = QPixmap(self.icon_path).scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, base_pixmap)
        else:
            # Fallback circle base
            painter.setBrush(QBrush(QColor("#1e293b")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

        # Draw status badge dot on bottom-right corner
        badge_radius = 9
        badge_cx = size - badge_radius - 2
        badge_cy = size - badge_radius - 2

        # Outer border for badge
        painter.setBrush(QBrush(QColor("#0f172a")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(badge_cx - badge_radius - 2, badge_cy - badge_radius - 2, (badge_radius + 2) * 2, (badge_radius + 2) * 2)

        # Inner status color
        painter.setBrush(QBrush(QColor(hex_color)))
        painter.drawEllipse(badge_cx - badge_radius, badge_cy - badge_radius, badge_radius * 2, badge_radius * 2)

        painter.end()
        return QIcon(pixmap)

    def _set_icon_color(self, hex_color: str):
        self.icon.setIcon(self._create_icon(hex_color))

    def update_status(self, connected: bool):
        color = "#00c957" if connected else "#e94560"
        self._set_icon_color(color)
        self.icon.setToolTip(
            "TypeBridge – Connected" if connected else "TypeBridge – Disconnected"
        )

    # ------------------------------------------------------------------ #
    #  Tray menu
    # ------------------------------------------------------------------ #
    def _setup_menu(self):
        menu = QMenu()

        act_show = menu.addAction("Show Window")
        act_show.triggered.connect(self._show_main)

        act_pair = menu.addAction("Pair Device")
        act_pair.triggered.connect(self.main_window.show_pairing)

        menu.addSeparator()

        self.act_pause = menu.addAction("Pause Typing")
        self.act_pause.triggered.connect(self.main_window.toggle_pause)

        menu.addSeparator()

        act_settings = menu.addAction("Settings")
        act_settings.triggered.connect(self.main_window.show_settings)

        act_update = menu.addAction("Check for Updates")
        act_update.triggered.connect(lambda: self.main_window.check_for_updates(silent=False, is_manual=True))

        act_mobile = menu.addAction("📱 Get Mobile App (APK)")
        act_mobile.triggered.connect(self.main_window.open_mobile_download)

        menu.addSeparator()

        act_quit = menu.addAction("Quit TypeBridge")
        act_quit.triggered.connect(self._quit_app)

        self.icon.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick or reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main()

    def _show_main(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def show_message(self, title: str, message: str):
        self.icon.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, 3000
        )

    def _quit_app(self):
        self.discovery.stop()
        self.main_window.typing_worker.stop()
        self.main_window.bt_server.stop()
        self.main_window.typing_worker.wait(2000)
        self.app.quit()
