import time
from app.storage.database import Database

class TrustStore:
    def __init__(self):
        self.db = Database()
        
    def add_device(self, device_id, device_name, public_key_b64, session_key_b64=""):
        self.db.execute_trust(
            "INSERT OR REPLACE INTO trusted_devices (device_id, device_name, public_key_b64, paired_at, is_trusted, session_key_b64) VALUES (?, ?, ?, ?, ?, ?)",
            (device_id, device_name, public_key_b64, int(time.time()), 1, session_key_b64)
        )
        
    def get_device(self, device_id):
        rows = self.db.execute_trust("SELECT device_id, device_name, public_key_b64, paired_at, is_trusted, session_key_b64 FROM trusted_devices WHERE device_id = ?", (device_id,))
        if rows:
            return {
                'device_id': rows[0][0],
                'device_name': rows[0][1],
                'public_key_b64': rows[0][2],
                'paired_at': rows[0][3],
                'is_trusted': bool(rows[0][4]),
                'session_key_b64': rows[0][5] if len(rows[0]) > 5 else ''
            }
        return None
        
    def list_devices(self):
        rows = self.db.execute_trust("SELECT device_id, device_name, public_key_b64, paired_at, is_trusted, session_key_b64 FROM trusted_devices WHERE is_trusted = 1 ORDER BY paired_at DESC")
        return [{
            'device_id': r[0],
            'device_name': r[1],
            'public_key_b64': r[2],
            'paired_at': r[3],
            'is_trusted': bool(r[4]),
            'session_key_b64': r[5] if len(r) > 5 else ''
        } for r in rows]
        
    def revoke_device(self, device_id):
        self.db.execute_trust("UPDATE trusted_devices SET is_trusted = 0 WHERE device_id = ?", (device_id,))
        
    def is_trusted(self, device_id):
        device = self.get_device(device_id)
        return device is not None and device['is_trusted']
