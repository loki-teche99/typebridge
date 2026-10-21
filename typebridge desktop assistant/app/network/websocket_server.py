"""
TypeBridge Desktop - WebSocket Server (TLS)
Async WSS server that handles pairing, text payloads, heartbeats, and ACKs.
Uses Qt signals to communicate results back to the UI thread safely.
"""
import asyncio
import base64
import json
import os
import ssl
import time
import uuid
import datetime
import threading

import websockets
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.config import ConfigManager
from app.core.logger import StructuredLogger
from app.network.message_protocol import MessageBuilder, MessageParser, MessageType
from app.security.crypto_engine import CryptoEngine
from app.security.trust_store import TrustStore


class WebSocketServer(QObject):
    """
    Runs in a background thread (asyncio event loop).
    Emits Qt signals so the UI thread can react safely.
    """
    # Signals emitted from the asyncio thread → Qt main thread
    connection_signal = pyqtSignal(dict)   # {'status': 'connected'|'disconnected', 'device_name': str, 'latency_ms': int}
    text_signal       = pyqtSignal(dict)   # {'text': str, 'msg_id': str, 'device_name': str}
    ack_signal        = pyqtSignal(str)    # msg_id that was completed
    pairing_signal    = pyqtSignal(dict)   # {'device_name': str, 'success': bool}
    control_signal    = pyqtSignal(dict)   # {'command': 'PAUSE'|'RESUME'|'STOP'}

    def __init__(self, pairing_manager):
        super().__init__()
        self.config = ConfigManager()
        self.logger = StructuredLogger()
        self.trust_store = TrustStore()
        self.pairing_manager = pairing_manager

        # TLS certificate paths
        tls_dir = os.path.join(self.config.appdata_dir, 'tls')
        os.makedirs(tls_dir, exist_ok=True)
        self.cert_path = os.path.join(tls_dir, 'cert.pem')
        self.key_path  = os.path.join(tls_dir, 'key.pem')
        self._ensure_tls_cert()

        # Session state
        self.active_session_id: str | None = None
        self.session_key: bytes | None = None
        self.paired_device_id: str | None = None
        self.paired_device_name: str | None = None
        self.active_websocket = None
        self._heartbeat_start: float = 0.0
        self.latency_ms: int = 0
        self._last_heartbeat_received: float = 0.0
        self._heartbeat_miss_count: int = 0
        self._heartbeat_active: bool = False
        self._processed_msg_ids: dict[str, float] = {}

        # Asyncio loop (set when start() is called)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready = threading.Event()

        # Restore previous trusted device session if exists
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
    #  TLS self-signed certificate generation
    # ------------------------------------------------------------------ #
    def _ensure_tls_cert(self):
        if os.path.exists(self.cert_path) and os.path.exists(self.key_path):
            return
        self.logger.info("Generating self-signed TLS certificate...")
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "TypeBridge Local")
            ])
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
                .sign(key, hashes.SHA256())
            )
            with open(self.key_path, "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
            with open(self.cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            self.logger.info("TLS certificate generated successfully.")
        except Exception as e:
            self.logger.error(f"Failed to generate TLS cert: {e}")

    # ------------------------------------------------------------------ #
    #  Client handler
    # ------------------------------------------------------------------ #
    async def _handle_client(self, websocket):
        remote = websocket.remote_address
        self.logger.info(f"New connection from {remote}")
        self.active_websocket = websocket
        try:
            async for raw_msg in websocket:
                await self._process_message(websocket, raw_msg)
        except websockets.ConnectionClosed as e:
            self.logger.info(f"Connection closed: {e.code} {e.reason}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            if self.active_websocket is websocket:
                self.active_websocket = None
                self._heartbeat_active = False
                if self.paired_device_name:
                    self.connection_signal.emit({
                        'status': 'disconnected',
                        'device_name': self.paired_device_name,
                        'latency_ms': 0,
                        'transport': 'wifi',
                    })

    def _decrypt_payload(self, ciphertext_b64: str, iv_b64: str) -> tuple[dict | None, str | None]:
        """Attempt decryption with active session_key or recover from trust_store."""
        if self.session_key:
            try:
                decrypted = CryptoEngine.decrypt(self.session_key, ciphertext_b64, iv_b64)
                return json.loads(decrypted), self.paired_device_name
            except Exception:
                pass

        # Fallback: recover session key from trusted devices in database
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
                    if not self.active_session_id:
                        self.active_session_id = str(uuid.uuid4())
                    self.connection_signal.emit({
                        'status': 'connected',
                        'device_name': dev['device_name'],
                        'latency_ms': 0,
                        'transport': 'wifi',
                    })
                    return json.loads(decrypted), dev['device_name']
            except Exception:
                continue

        return None, None

    # ------------------------------------------------------------------ #
    #  Message processing
    # ------------------------------------------------------------------ #
    async def _process_message(self, websocket, raw_msg: str):
        try:
            msg = MessageParser.parse(raw_msg)
        except Exception as e:
            self.logger.error(f"Failed to parse message: {e}")
            return

        mtype = msg.get('type')
        self.active_websocket = websocket

        # Fix #5: Auto-start heartbeat for reconnecting trusted clients
        if not self._heartbeat_active and self.session_key and mtype != MessageType.PAIR_REQUEST:
            self._heartbeat_active = True
            self.logger.info("Auto-starting heartbeat for reconnected trusted client")
            asyncio.ensure_future(self._heartbeat_loop(websocket))

        # ---- PAIR_REQUEST -------------------------------------------- #
        if mtype == MessageType.PAIR_REQUEST:
            try:
                payload = json.loads(msg.get('payload', '{}'))
                device_name   = payload.get('device_name', 'Android')
                their_pub_b64 = payload.get('public_key', '')
                received_pin  = payload.get('pin', '')

                if received_pin != self.pairing_manager.pin:
                    self.logger.warning("Pairing rejected: wrong PIN")
                    resp = MessageBuilder.build(
                        MessageType.PAIR_RESPONSE, json.dumps({'status': 'rejected'}), '', ''
                    )
                    await websocket.send(resp)
                    self.pairing_signal.emit({'device_name': device_name, 'success': False})
                    return

                # Derive session key
                their_pub = CryptoEngine.deserialize_public_key(their_pub_b64)
                session_key = CryptoEngine.derive_session_key(
                    self.pairing_manager.private_key, their_pub
                )
                session_id = str(uuid.uuid4())
                device_id  = str(uuid.uuid4())

                # Persist trusted device with session key
                session_key_b64 = base64.b64encode(session_key).decode('utf-8')
                self.trust_store.add_device(device_id, device_name, their_pub_b64, session_key_b64)

                # Save session state
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
                await websocket.send(resp)

                self.pairing_signal.emit({'device_name': device_name, 'success': True})
                self.connection_signal.emit({
                    'status': 'connected',
                    'device_name': device_name,
                    'latency_ms': 0,
                    'transport': 'wifi',
                })
                self.logger.info(f"Paired with {device_name}")

                # Start heartbeat loop
                self._heartbeat_active = True
                asyncio.ensure_future(self._heartbeat_loop(websocket))

            except Exception as e:
                self.logger.error(f"Pairing error: {e}")

        # ---- TEXT_PAYLOAD -------------------------------------------- #
        elif mtype == MessageType.TEXT_PAYLOAD:
            ciphertext_b64 = msg.get('payload', '')
            iv_b64         = msg.get('iv', '')
            data, dev_name = self._decrypt_payload(ciphertext_b64, iv_b64)

            if data is None:
                self.logger.warning("Failed to decrypt TEXT_PAYLOAD from untrusted key")
                return

            text   = data.get('text', '')
            msg_id = data.get('msg_id', str(uuid.uuid4()))

            # Deduplication: Never replay an uncertain typing operation if reconnect occurs
            now = time.time()
            self._processed_msg_ids = {k: v for k, v in self._processed_msg_ids.items() if now - v < 900.0}
            if msg_id in self._processed_msg_ids:
                self.logger.info(f"Duplicate msg_id={msg_id[:8]} detected after reconnect. Dropping to prevent duplicate typing.")
                asyncio.ensure_future(self._send_ack(msg_id))
                return
            self._processed_msg_ids[msg_id] = now

            if text:
                self.text_signal.emit({
                    'text':        text,
                    'msg_id':      msg_id,
                    'device_name': dev_name or 'Device',
                })
                self.logger.info(f"Received {len(text)} chars (msg_id={msg_id[:8]}...)")

        # ---- HEARTBEAT ----------------------------------------------- #
        elif mtype == MessageType.HEARTBEAT:
            self._ensure_session()
            is_echo = False
            try:
                payload = json.loads(msg.get('payload', '{}')) if msg.get('payload') else {}
                t_sent = payload.get('t_sent', 0)
                is_echo = bool(payload.get('is_echo', False))
                if is_echo and t_sent > 0:
                    now_ms = int(time.time() * 1000)
                    self.latency_ms = max(1, min(999, now_ms - t_sent))
            except Exception:
                pass

            self._heartbeat_miss_count = 0
            self._last_heartbeat_received = time.time()

            quality = 'excellent' if self.latency_ms < 30 else ('good' if self.latency_ms < 100 else 'fair')

            self.connection_signal.emit({
                'status':      'connected',
                'device_name': self.paired_device_name or 'Android Device',
                'latency_ms':  self.latency_ms,
                'quality':     quality,
                'transport':   'wifi',
            })

            # Auto-start heartbeat if not yet active
            if not self._heartbeat_active:
                self._heartbeat_active = True
                asyncio.ensure_future(self._heartbeat_loop(websocket))

            # If this is not an echo, reply back to Android immediately so it confirms connection & latency
            if not is_echo:
                t_sent_val = payload.get('t_sent', int(time.time() * 1000))
                resp_payload = json.dumps({'t_sent': t_sent_val, 'is_echo': True})
                resp = MessageBuilder.build(
                    MessageType.HEARTBEAT, resp_payload, '', msg.get('session_id', '') or self.active_session_id or ''
                )
                try:
                    await websocket.send(resp)
                except Exception:
                    pass

        # ---- REVOKE -------------------------------------------------- #
        elif mtype == MessageType.REVOKE:
            device_id = msg.get('payload', '')
            if device_id:
                self.trust_store.revoke_device(device_id)
                self.logger.info(f"Device revoked: {device_id}")

        # ---- CONTROL ------------------------------------------------- #
        elif mtype == MessageType.CONTROL:
            ciphertext_b64 = msg.get('payload', '')
            iv_b64         = msg.get('iv', '')
            data, _        = self._decrypt_payload(ciphertext_b64, iv_b64)
            if data:
                cmd = data.get('command', '')
                if cmd:
                    self.control_signal.emit({'command': cmd})
                    self.logger.info(f"Received CONTROL command from phone: {cmd}")

    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    #  Heartbeat loop (runs while connected)
    # ------------------------------------------------------------------ #
    async def _heartbeat_loop(self, websocket):
        try:
            while True:
                await asyncio.sleep(2)
                if self.active_websocket is not websocket:
                    break
                try:
                    t_sent = int(time.time() * 1000)
                    hb_payload = json.dumps({'t_sent': t_sent, 'is_echo': False})
                    hb = MessageBuilder.build(
                        MessageType.HEARTBEAT, hb_payload, '', self.active_session_id or ''
                    )
                    await websocket.send(hb)
                except (websockets.ConnectionClosed, Exception):
                    # Connection lost — stop the heartbeat loop
                    break
        finally:
            self._heartbeat_active = False

    # ------------------------------------------------------------------ #
    #  Send ACK (called from Qt thread via schedule_ack)
    # ------------------------------------------------------------------ #
    async def _send_ack(self, msg_id: str):
        if not self.session_key or not self.active_session_id or not self.active_websocket:
            return
        try:
            payload = json.dumps({'ack_id': msg_id})
            enc, iv = CryptoEngine.encrypt(self.session_key, payload)
            msg = MessageBuilder.build(MessageType.ACK, enc, iv, self.active_session_id)
            await self.active_websocket.send(msg)
            self.logger.info(f"ACK sent for msg_id={msg_id[:8]}...")
        except Exception as e:
            self.logger.error(f"Failed to send ACK: {e}")

    def schedule_ack(self, msg_id: str):
        """Thread-safe: schedule ACK from any thread."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send_ack(msg_id), self._loop)

    # ------------------------------------------------------------------ #
    #  Server startup (blocking — call from daemon thread)
    # ------------------------------------------------------------------ #
    def start(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        port = self.config.get('server_port')
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(self.cert_path, self.key_path)

        self.logger.info(f"TypeBridge WSS server starting on port {port}...")
        async with websockets.serve(
            self._handle_client,
            "0.0.0.0",
            port,
            ssl=ssl_ctx,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=10,
            max_size=20 * 1024 * 1024,
        ):
            self.logger.info(f"WSS server ready on port {port}")
            await asyncio.Future()  # Run forever
