"""
TypeBridge Website Local Server
Serves the TypeBridge website and installation files across your local Wi-Fi.
"""
import http.server
import socket
import socketserver
import os
import sys
import webbrowser

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def get_local_ip():
    """Retrieve the primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, just determines route
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching for live development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

def main():
    local_ip = get_local_ip()
    port = PORT

    while True:
        try:
            with socketserver.TCPServer(("", port), CustomHandler) as httpd:
                print("\n" + "=" * 65)
                print("       TYPEBRIDGE OFFICIAL DOWNLOAD & SHOWCASE WEBSITE       ")
                print("=" * 65)
                print(f"  [PC Browser]    : http://localhost:{port}")
                print(f"  [Phone / Wi-Fi] : http://{local_ip}:{port}")
                print("-" * 65)
                print("  Downloadable Files:")
                print(f"    - Windows Installer : http://{local_ip}:{port}/downloads/TypeBridgeSetup-v1.0.0.exe")
                print(f"    - Android APK       : http://{local_ip}:{port}/downloads/TypeBridge-Android-v1.0.0.apk")
                print("=" * 65)
                print("  Press Ctrl+C in terminal to stop the web server.\n")

                # Open browser locally
                try:
                    webbrowser.open(f"http://localhost:{port}")
                except Exception:
                    pass

                httpd.serve_forever()
        except OSError as e:
            if e.errno in (10048, 98): # Address already in use
                port += 1
            else:
                raise

if __name__ == "__main__":
    main()
