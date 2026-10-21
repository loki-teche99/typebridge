"""
TypeBridge Desktop - Main Entry Point
Starts the Qt application with system tray, background WebSocket server,
Windows taskbar integration, and single-instance enforcement.
"""
import sys
import os
import ctypes

# Set Windows AppUserModelID so taskbar groups properly and displays the custom icon
try:
    myappid = 'TypeBridge.Desktop.Assistant.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# Ensure app data directory exists before anything else
appdata = os.path.join(os.environ.get('APPDATA', ''), 'TypeBridge')
os.makedirs(appdata, exist_ok=True)

# Base directory (supports both dev and PyInstaller frozen binary)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from app.ui.tray_app import TrayApp


SINGLE_INSTANCE_SERVER = "TypeBridge_SingleInstance_App_Server"


def activate_existing_instance() -> bool:
    """Check if an instance is already running; if so, notify it to show its window and return True."""
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_SERVER)
    if socket.waitForConnected(500):
        # Already running, send command to bring it to front
        socket.write(b"ACTIVATE")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True
    return False


def main():
    # Enable High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TypeBridge")
    app.setApplicationVersion("1.0.2")
    app.setOrganizationName("TypeBridge")
    app.setQuitOnLastWindowClosed(False)

    # Set application icon
    icon_path = os.path.join(BASE_DIR, 'assets', 'icon.ico')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(BASE_DIR, 'assets', 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Single-Instance check
    if activate_existing_instance():
        print("TypeBridge is already running. Existing window activated.")
        sys.exit(0)

    # Initialize single-instance local server to listen for subsequent launches
    local_server = QLocalServer()
    # Remove old socket file if uncleanly closed
    local_server.removeServer(SINGLE_INSTANCE_SERVER)
    local_server.listen(SINGLE_INSTANCE_SERVER)

    tray = TrayApp(app)

    def on_new_connection():
        client_sock = local_server.nextPendingConnection()
        if client_sock:
            if client_sock.waitForReadyRead(500):
                msg = client_sock.readAll().data().decode('utf-8', errors='ignore')
                if "ACTIVATE" in msg:
                    tray.main_window.show()
                    tray.main_window.raise_()
                    tray.main_window.activateWindow()
            client_sock.disconnectFromServer()

    local_server.newConnection.connect(on_new_connection)

    # Show main window on first launch
    tray.main_window.show()

    # Clean up local server on exit
    def cleanup():
        local_server.close()
        local_server.removeServer(SINGLE_INSTANCE_SERVER)

    app.aboutToQuit.connect(cleanup)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
