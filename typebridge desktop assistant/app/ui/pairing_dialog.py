from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPixmap


class PairingDialog(QDialog):
    def __init__(self, manager, ws_server=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.ws_server = ws_server
        self.setWindowTitle("Pair Device — TypeBridge")
        self.setFixedSize(440, 560)
        self._setup_ui()

        if self.ws_server is not None:
            self.ws_server.pairing_signal.connect(self.on_pairing_complete)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        lbl_title = QLabel("Scan QR Code with TypeBridge Mobile")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_title)

        # Network interface dropdown
        self.interfaces = self.manager.get_local_ips()
        if len(self.interfaces) > 1:
            row_net = QHBoxLayout()
            row_net.addWidget(QLabel("Network Adapter:"))
            self.combo_ip = QComboBox()
            for name, ip in self.interfaces:
                self.combo_ip.addItem(f"{name} ({ip})", ip)
            self.combo_ip.currentIndexChanged.connect(self._on_interface_changed)
            row_net.addWidget(self.combo_ip)
            layout.addLayout(row_net)

        # QR code container card
        qr_card = QFrame()
        qr_card.setStyleSheet("background: #ffffff; border-radius: 12px; padding: 12px;")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self.lbl_qr)
        layout.addWidget(qr_card)

        # PIN display
        pin_box = QHBoxLayout()
        self.lbl_pin = QLabel()
        self.lbl_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pin.setStyleSheet("font-size: 26px; font-weight: bold; letter-spacing: 3px; color: #00f0ff;")
        pin_box.addWidget(self.lbl_pin)

        btn_regen_pin = QPushButton("🔄 New PIN")
        btn_regen_pin.setFixedHeight(30)
        btn_regen_pin.clicked.connect(self._regenerate_pin)
        pin_box.addWidget(btn_regen_pin)
        layout.addLayout(pin_box)

        # Manual entry info
        self.lbl_manual = QLabel()
        self.lbl_manual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_manual.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(self.lbl_manual)

        self.lbl_status = QLabel("Waiting for phone to scan or connect...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        layout.addWidget(self.lbl_status)

        # Mobile app download action
        row_download = QHBoxLayout()
        btn_get_mobile = QPushButton("📱 Download Mobile App (https://typebridge.42web.io/)")
        btn_get_mobile.setStyleSheet("""
            QPushButton {
                background: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #0369a1;
            }
        """)
        btn_get_mobile.clicked.connect(self._open_website)
        row_download.addStretch()
        row_download.addWidget(btn_get_mobile)
        row_download.addStretch()
        layout.addLayout(row_download)

        # Bottom close button
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Done")
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._refresh_qr_and_info()

    def _open_website(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://typebridge.42web.io/"))

    def _on_interface_changed(self, index: int):
        if hasattr(self, 'combo_ip'):
            selected_ip = self.combo_ip.currentData()
            self.manager.set_selected_ip(selected_ip)
            self._refresh_qr_and_info()

    def _regenerate_pin(self):
        self.manager.generate_pin()
        self._refresh_qr_and_info()

    def _refresh_qr_and_info(self):
        active_ip = self.manager.get_local_ip()
        pin = self.manager.pin or self.manager.generate_pin()

        img = self.manager.generate_qr_image(ip=active_ip)
        pixmap = QPixmap.fromImage(img).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_qr.setPixmap(pixmap)

        self.lbl_pin.setText(f"PIN: {pin}")
        self.lbl_manual.setText(f"Manual Entry → IP: {active_ip}  |  Port: 8765")

    @pyqtSlot(dict)
    def on_pairing_complete(self, data: dict):
        device_name = data.get('device_name', 'Phone')
        success = data.get('success', False)

        if success:
            self.lbl_status.setText(f"✅ Paired & Connected to {device_name}!")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #00c957;")
            QTimer.singleShot(1400, self.accept)
        else:
            self.lbl_status.setText(f"❌ Pairing Rejected (Incorrect PIN)")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #e94560;")
