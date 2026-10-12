"""
TypeBridge Desktop - Bluetooth SPP Server
==========================================
Listens on a Bluetooth Serial Port Profile (SPP) virtual COM port.
Uses the same MessageProtocol JSON format as the WebSocket server.
Framing: 4-byte big-endian length prefix + JSON payload.

Fallback transport when Wi-Fi WebSocket is unavailable or unstable.
"""
import base64
import json
import os
import struct
import threading
import time
import uuid

from PyQt6.QtCore import QObject, pyqtSignal

from app.core.config import ConfigManager
from app.core.logger import StructuredLogger
from app.network.message_protocol import MessageBuilder, MessageParser, MessageType
from app.security.crypto_engine import CryptoEngine
from app.security.trust_store import TrustStore

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class BluetoothServer(QObject):
    """
    Bluetooth SPP transport server.
    Runs in a background daemon thread, emits Qt signals for UI thread safety.
    Compatible with the same signal interface as WebSocketServer.
    """
    # Same signal interface as WebSocketServer for drop-in compatibility
    connection_signal = pyqtSignal(dict)
    text_signal       = pyqtSignal(dict)
    ack_signal        = pyqtSignal(str)
    pairing_signal    = pyqtSignal(dict)
    control_signal    = pyqtSignal(dict)

    def __init__(self, pairing_manager):
        super().__init__()
        self.config = ConfigManager()
        self.logger = StructuredLogger()
        self.trust_store = TrustStore()
        self.pairing_manager = pairing_manager

        # Session state (mirrors WebSocketServer)
        self.active_session_id: str | None = None
        self.session_key: bytes | None = None
        self.paired_device_id: str | None = None
        self.paired_device_name: str | None = None
        self.latency_ms: int = 0

        # Serial port state
        self._serial: serial.Serial | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._last_heartbeat_received: float = 0.0
        self._heartbeat_miss_count: int = 0
        self._processed_msg_ids: dict[str, float] = {}
        self._ensure_session()

    def _ensure_session(self):
        """Restore session from trusted store if available."""
        if not self.session_key:
            devices = self.trust_store.list_devices()
            for dev in devices:
                self.paired_device_name = dev.get('device_name', 'Android Device')
                self.paired_device_id = dev.get('device_id')
                if not self.active_session_id:
                    self.active_session_id = str(uuid.uuid4())
                s_b64 = dev.get('session_key_b64', '')
                if s_b64:
                    try:
                        self.session_key = base64.b64decode(s_b64)
                        return
                    except Exception:
                        pass
                pub_b64 = dev.get('public_key_b64', '')
                if pub_b64:
                    try:
                        their_pub = CryptoEngine.deserialize_public_key(pub_b64)
                        self.session_key = CryptoEngine.derive_session_key(self.pairing_manager.private_key, their_pub)
                        return
                    except Exception:
                        pass

    # ------------------------------------------------------------------ #
    #  COM Port Discovery
    # ------------------------------------------------------------------ #
    @staticmethod
    def find_bluetooth_ports() -> list[dict]:
        """Find available Bluetooth SPP COM ports."""
        if not SERIAL_AVAILABLE:
            return []
        bt_ports = []
        for port_info in serial.tools.list_ports.comports():
            desc = (port_info.description or '').lower()
            hwid = (port_info.hwid or '').lower()
            # Match Bluetooth serial ports by description or hardware ID
            if any(kw in desc for kw in ['bluetooth', 'bt ', 'bth', 'rfcomm', 'serial port']):
                bt_ports.append({
                    'port': port_info.device,
                    'description': port_info.description,
                    'hwid': port_info.hwid,
                })
            elif 'bthenum' in hwid or 'bluetooth' in hwid:
                bt_ports.append({
                    'port': port_info.device,
                    'description': port_info.description,
                    'hwid': port_info.hwid,
                })
        return bt_ports

    # ------------------------------------------------------------------ #
    #  Framed I/O (4-byte length prefix + JSON)
    # ------------------------------------------------------------------ #
    def _send_frame(self, data: str) -> bool:
        """Send a length-prefixed JSON frame over serial."""
        if not self._serial or not self._serial.is_open:
            return False
        try:
            payload = data.encode('utf-8')
            header = struct.pack('>I', len(payload))
            self._serial.write(header + payload)
            self._serial.flush()
            return True
        except Exception as e:
            self.logger.error(f"BT send error: {e}")
            return False

    def _recv_frame(self, timeout: float = 1.0) -> str | None:
        """Read a length-prefixed JSON frame from serial."""
        if not self._serial or not self._serial.is_open:
            return None
        try:
            self._serial.timeout = timeout
            header = self._serial.read(4)
            if len(header) < 4:
                return None
            length = struct.unpack('>I', header)[0]
            if length > 10 * 1024 * 1024:  # 10MB safety limit
                self.logger.warning(f"BT frame too large: {length} bytes")
                return None
            data = b''
            remaining = length
            while remaining > 0:
                chunk = self._serial.read(min(remaining, 4096))
                if not chunk:
                    return None
                data += chunk
                remaining -= len(chunk)
            return data.decode('utf-8')
        except Exception as e:
            self.logger.error(f"BT recv error: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Decryption (same as WebSocketServer)
    # ------------------------------------------------------------------ #
    def _decrypt_payload(self, ciphertext_b64: str, iv_b64: str) -> tuple[dict | None, str | None]:
        if self.session_key:
            try:
                decrypted = CryptoEngine.decrypt(self.session_key, ciphertext_b64, iv_b64)
                return json.loads(decrypted), self.paired_device_name
            except Exception:
                pass
        devices = self.trust_store.list_devices()
        for dev in devices:
            try:
                s_key = None
                s_b64 = dev.get('session_key_b64', '')
                if s_b64:
                    try:
                        s_key = base64.b64decode(s_b64)
                    except Exception:
                        pass
                if not s_key and dev.get('public_key_b64'):
                    their_pub = CryptoEngine.deserialize_public_key(dev['public_key_b64'])
                    s_key = CryptoEngine.derive_session_key(self.pairing_manager.private_key, their_pub)

                if s_key:
                    decrypted = CryptoEngine.decrypt(s_key, ciphertext_b64, iv_b64)
                    self.session_key = s_key
                    self.paired_device_name = dev['device_name']
                    self.paired_device_id = dev['device_id']
                    # Restore session_id so ACKs work on reconnect (Fix #8)
                    if not self.active_session_id:
                        self.active_session_id = str(uuid.uuid4())
                    self.connection_signal.emit({
                        'status': 'connected',
                        'device_name': dev['device_name'],
                        'latency_ms': 0,
                        'transport': 'bluetooth',
                    })
                    return json.loads(decrypted), dev['device_name']
            except Exception:
                continue
        return None, None

    # ------------------------------------------------------------------ #
    #  Message Processing (mirrors WebSocketServer._process_message)
    # ------------------------------------------------------------------ #
    def _process_message(self, raw_msg: str):
        try:
            msg = MessageParser.parse(raw_msg)
        except Exception as e:
            self.logger.error(f"BT parse error: {e}")
            return

        mtype = msg.get('type')

        # Fix #8: Auto-start heartbeat for reconnecting trusted clients
        if self.session_key and mtype != MessageType.PAIR_REQUEST:
            if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
                self.logger.info("Auto-starting BT heartbeat for reconnected trusted client")
                self._start_heartbeat()

        # ---- PAIR_REQUEST ---- #
        if mtype == MessageType.PAIR_REQUEST:
            try:
                payload = json.loads(msg.get('payload', '{}'))
                device_name   = payload.get('device_name', 'Android')
                their_pub_b64 = payload.get('public_key', '')
                received_pin  = payload.get('pin', '')

                if received_pin != self.pairing_manager.pin:
                    self.logger.warning("BT pairing rejected: wrong PIN")
                    resp = MessageBuilder.build(
                        MessageType.PAIR_RESPONSE, json.dumps({'status': 'rejected'}), '', ''
                    )
                    self._send_frame(resp)
                    self.pairing_signal.emit({'device_name': device_name, 'success': False})
                    return

                their_pub = CryptoEngine.deserialize_public_key(their_pub_b64)
                session_key = CryptoEngine.derive_session_key(
                    self.pairing_manager.private_key, their_pub
                )
                session_id = str(uuid.uuid4())
                device_id  = str(uuid.uuid4())

                # Persist trusted device with session key
                session_key_b64 = base64.b64encode(session_key).decode('utf-8')
                self.trust_store.add_device(device_id, device_name, their_pub_b64, session_key_b64)

                self.session_key        = session_key
                self.active_session_id  = session_id
                self.paired_device_id   = device_id
                self.paired_device_name = device_name

                resp_payload = json.dumps({
                    'status':     'accepted',
                    'public_key': self.pairing_manager.pub_b64,
                    'session_id': session_id,
                })
                resp = MessageBuilder.build(MessageType.PAIR_RESPONSE, resp_payload, '', '')
                self._send_frame(resp)

                self.pairing_signal.emit({'device_name': device_name, 'success': True})
                self.connection_signal.emit({
                    'status': 'connected',
                    'device_name': device_name,
                    'latency_ms': 0,
                    'transport': 'bluetooth',
                })
                self.logger.info(f"BT paired with {device_name}")
                self._start_heartbeat()

            except Exception as e:
                self.logger.error(f"BT pairing error: {e}")

        # ---- TEXT_PAYLOAD ---- #
        elif mtype == MessageType.TEXT_PAYLOAD:
            ciphertext_b64 = msg.get('payload', '')
            iv_b64         = msg.get('iv', '')
            data, dev_name = self._decrypt_payload(ciphertext_b64, iv_b64)
            if data is None:
                self.logger.warning("BT: Failed to decrypt TEXT_PAYLOAD")
                return
            text   = data.get('text', '')
            msg_id = data.get('msg_id', str(uuid.uuid4()))

            # Deduplication
            now = time.time()
            self._processed_msg_ids = {k: v for k, v in self._processed_msg_ids.items() if now - v < 900.0}
            if msg_id in self._processed_msg_ids:
                self.logger.info(f"BT duplicate msg_id={msg_id[:8]} detected. Dropping to prevent double typing.")
                self.send_ack(msg_id)
                return
            self._processed_msg_ids[msg_id] = now

            if text:
                self.text_signal.emit({
                    'text': text,
                    'msg_id': msg_id,
                    'device_name': dev_name or 'Device',
                })
                self.logger.info(f"BT received {len(text)} chars (msg_id={msg_id[:8]}...)")

        # ---- HEARTBEAT ---- #
        elif mtype == MessageType.HEARTBEAT:
            self._ensure_session()
            try:
                payload = json.loads(msg.get('payload', '{}')) if msg.get('payload') else {}
                t_sent = payload.get('t_sent', 0)
                if t_sent > 0:
                    now_ms = int(time.time() * 1000)
                    self.latency_ms = max(1, now_ms - t_sent)
                else:
                    self.latency_ms = 5
            except Exception:
                self.latency_ms = 5

            self._last_heartbeat_received = time.time()
            self._heartbeat_miss_count = 0

            quality = 'excellent' if self.latency_ms < 20 else ('good' if self.latency_ms < 100 else 'poor')
            self.connection_signal.emit({
                'status':      'connected',
                'device_name': self.paired_device_name or 'Android Device',
                'latency_ms':  self.latency_ms,
                'transport':   'bluetooth',
                'quality':     quality,
            })

        # ---- CONTROL ---- #
        elif mtype == MessageType.CONTROL:
            ciphertext_b64 = msg.get('payload', '')
            iv_b64         = msg.get('iv', '')
            data, _        = self._decrypt_payload(ciphertext_b64, iv_b64)
            if data:
                cmd = data.get('command', '')
                if cmd:
                    self.control_signal.emit({'command': cmd})
                    self.logger.info(f"BT control: {cmd}")

    # ------------------------------------------------------------------ #
    #  Heartbeat (background thread)
    # ------------------------------------------------------------------ #
    def _start_heartbeat(self):
        self._stop_heartbeat()
        self._heartbeat_miss_count = 0
        self._last_heartbeat_received = time.time()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _stop_heartbeat(self):
        self._heartbeat_thread = None

    def _heartbeat_loop(self):
        current_thread = threading.current_thread()
        while self._running and self._heartbeat_thread is current_thread:
            time.sleep(3)
            if not self._running or self._heartbeat_thread is not current_thread:
                break
            try:
                t_sent = int(time.time() * 1000)
                hb_payload = json.dumps({'t_sent': t_sent})
                hb = MessageBuilder.build(
                    MessageType.HEARTBEAT, hb_payload, '', self.active_session_id or ''
                )
                if not self._send_frame(hb):
                    break
                self._heartbeat_miss_count += 1
                if self._heartbeat_miss_count >= 5:
                    self.logger.warning("BT: 5 heartbeats missed, connection may be dead")
                    break
            except Exception:
                break

    # ------------------------------------------------------------------ #
    #  Send ACK
    # ------------------------------------------------------------------ #
    def schedule_ack(self, msg_id: str):
        if not self.session_key or not self.active_session_id:
            return
        try:
            payload = json.dumps({'ack_id': msg_id})
            enc, iv = CryptoEngine.encrypt(self.session_key, payload)
            msg = MessageBuilder.build(MessageType.ACK, enc, iv, self.active_session_id)
            self._send_frame(msg)
            self.logger.info(f"BT ACK sent for {msg_id[:8]}...")
        except Exception as e:
            self.logger.error(f"BT ACK error: {e}")

    # ------------------------------------------------------------------ #
    #  Server start/stop
    # ------------------------------------------------------------------ #
    def start(self):
        if not SERIAL_AVAILABLE:
            self.logger.warning("pyserial not installed — Bluetooth transport disabled")
            return
        if not self.config.get('bluetooth_enabled', True):
            self.logger.info("Bluetooth transport disabled in config")
            return

        self._running = True
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()
        self.logger.info("Bluetooth SPP server started")

    def stop(self):
        self._running = False
        self._stop_heartbeat()
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        if self.paired_device_name:
            self.connection_signal.emit({
                'status': 'disconnected',
                'device_name': self.paired_device_name,
                'latency_ms': 0,
                'transport': 'bluetooth',
            })
        self.logger.info("Bluetooth SPP server stopped")

    def _serve_loop(self):
        """Main loop: find BT port, open, read messages."""
        while self._running:
            try:
                # Find and open a Bluetooth COM port
                com_port = self.config.get('bluetooth_com_port', 'auto')
                if com_port == 'auto':
                    ports = self.find_bluetooth_ports()
                    if not ports:
                        time.sleep(5)  # Retry every 5s
                        continue
                    com_port = ports[0]['port']
                    self.logger.info(f"BT auto-detected port: {com_port}")

                self._serial = serial.Serial(
                    port=com_port,
                    baudrate=115200,
                    timeout=1.0,
                    write_timeout=5.0,
                )
                self.logger.info(f"BT serial port opened: {com_port}")

                # Read loop
                while self._running and self._serial and self._serial.is_open:
                    raw_msg = self._recv_frame(timeout=0.5)
                    if raw_msg:
                        self._process_message(raw_msg)

            except serial.SerialException as e:
                self.logger.error(f"BT serial error: {e}")
                if self.paired_device_name:
                    self.connection_signal.emit({
                        'status': 'disconnected',
                        'device_name': self.paired_device_name,
                        'latency_ms': 0,
                        'transport': 'bluetooth',
                    })
                self._stop_heartbeat()
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                # Wait before retry
                if self._running:
                    time.sleep(3)

            except Exception as e:
                self.logger.error(f"BT unexpected error: {e}")
                if self._running:
                    time.sleep(3)
