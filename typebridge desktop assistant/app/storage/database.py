import sqlite3
import os
from app.core.config import ConfigManager

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance
        
    def _init_db(self):
        config = ConfigManager()
        self.db_path = os.path.join(config.appdata_dir, 'trust.db')
        self.queue_db_path = os.path.join(config.appdata_dir, 'queue.db')
        
        self.execute_trust('''
            CREATE TABLE IF NOT EXISTS trusted_devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT,
                public_key_b64 TEXT,
                paired_at INTEGER,
                is_trusted INTEGER,
                session_key_b64 TEXT DEFAULT ''
            )
        ''')
        try:
            self.execute_trust('ALTER TABLE trusted_devices ADD COLUMN session_key_b64 TEXT DEFAULT ""')
        except Exception:
            pass
        
        self.execute_queue('''
            CREATE TABLE IF NOT EXISTS typing_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT UNIQUE,
                text TEXT,
                status TEXT,
                received_at INTEGER,
                completed_at INTEGER
            )
        ''')
        
        self.execute_trust('''
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                timestamp INTEGER
            )
        ''')
        
    def execute_trust(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
            
    def execute_queue(self, query, params=()):
        with sqlite3.connect(self.queue_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
