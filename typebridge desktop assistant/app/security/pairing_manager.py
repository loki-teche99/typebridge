import os
import io
import random
import socket
import qrcode
from PyQt6.QtGui import QImage
from app.core.config import ConfigManager
from app.security.crypto_engine import CryptoEngine

class PairingManager:
    def __init__(self):
        self.config = ConfigManager()
        self.pin = None
        self._load_or_generate_keypair()
        self.selected_ip = None

    def _load_or_generate_keypair(self):
        keys_dir = os.path.join(self.config.appdata_dir, 'keys')
        os.makedirs(keys_dir, exist_ok=True)
        key_file = os.path.join(keys_dir, 'desktop_identity.key')
        if os.path.exists(key_file):
            try:
                with open(key_file, 'r', encoding='utf-8') as f:
                    priv_b64 = f.read().strip()
                self.private_key = CryptoEngine.deserialize_private_key(priv_b64)
                self.public_key = self.private_key.public_key()
                self.pub_b64 = CryptoEngine.serialize_public_key(self.public_key)
                return
            except Exception:
                pass
        self.private_key, self.public_key = CryptoEngine.generate_keypair()
        self.pub_b64 = CryptoEngine.serialize_public_key(self.public_key)
        try:
            with open(key_file, 'w', encoding='utf-8') as f:
                f.write(CryptoEngine.serialize_private_key(self.private_key))
        except Exception:
            pass

    def get_local_ips(self) -> list[tuple[str, str]]:
        """Return list of (adapter_name, ip) for all active non-loopback IPv4 interfaces."""
        ips = []
        try:
            import ifaddr
            adapters = ifaddr.get_adapters()
            for adapter in adapters:
                for ip in adapter.ips:
                    if ip.is_IPv4:
                        addr = ip.ip
                        if not addr.startswith("127.") and not addr.startswith("169.254."):
                            nice_name = adapter.nice_name or adapter.name
                            ips.append((nice_name, addr))
        except Exception:
            pass

        # Fallback using standard socket
        if not ips:
            fallback = self._get_fallback_ip()
            ips.append(("Local Network", fallback))

        # Sort so 192.168.x.x and 10.x.x.x appear first (most common Wi-Fi/LAN)
        def sort_priority(item):
            name, ip = item
            name_lower = name.lower()
            if "wi-fi" in name_lower or "wireless" in name_lower or "wlan" in name_lower:
                return 0
            if "ethernet" in name_lower:
                return 1
            if ip.startswith("192.168."):
                return 2
            if ip.startswith("10."):
                return 3
            if "vethernet" in name_lower or "wsl" in name_lower or "docker" in name_lower:
                return 9
            return 5

        ips.sort(key=sort_priority)
        return ips

    def _get_fallback_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def get_local_ip(self) -> str:
        if self.selected_ip:
            return self.selected_ip
        available = self.get_local_ips()
        if available:
            return available[0][1]
        return self._get_fallback_ip()

    def set_selected_ip(self, ip: str):
        self.selected_ip = ip

    def generate_pin(self) -> str:
        self.pin = f"{random.randint(0, 999999):06d}"
        return self.pin

    def generate_qr_image(self, ip=None, port=8765) -> QImage:
        if not self.pin:
            self.generate_pin()
        active_ip = ip or self.get_local_ip()
        data = f"typebridge://pair?ip={active_ip}&port={port}&pubkey={self.pub_b64}&pin={self.pin}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qimg = QImage()
        qimg.loadFromData(buf.getvalue())
        return qimg
