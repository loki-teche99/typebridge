import base64
import os
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class CryptoEngine:
    @staticmethod
    def generate_keypair():
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key
        
    @staticmethod
    def serialize_public_key(public_key):
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(pub_bytes).decode('utf-8')
        
    @staticmethod
    def deserialize_public_key(pub_b64):
        pub_bytes = base64.b64decode(pub_b64)
        return x25519.X25519PublicKey.from_public_bytes(pub_bytes)

    @staticmethod
    def serialize_private_key(private_key):
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        return base64.b64encode(priv_bytes).decode('utf-8')

    @staticmethod
    def deserialize_private_key(priv_b64):
        priv_bytes = base64.b64decode(priv_b64)
        return x25519.X25519PrivateKey.from_private_bytes(priv_bytes)
        
    @staticmethod
    def derive_session_key(private_key, peer_public_key):
        shared_key = private_key.exchange(peer_public_key)
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'typebridge_handshake',
        ).derive(shared_key)
        return derived_key
        
    @staticmethod
    def encrypt(key: bytes, plaintext: str):
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
        return base64.b64encode(ciphertext).decode('utf-8'), base64.b64encode(iv).decode('utf-8')
        
    @staticmethod
    def decrypt(key: bytes, ciphertext_b64: str, iv_b64: str) -> str:
        aesgcm = AESGCM(key)
        ciphertext = base64.b64decode(ciphertext_b64)
        iv = base64.b64decode(iv_b64)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode('utf-8')
