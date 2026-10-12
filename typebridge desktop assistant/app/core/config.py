import os
import json

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance
        
    def _init_config(self):
        self.appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'TypeBridge')
        os.makedirs(self.appdata_dir, exist_ok=True)
        self.config_path = os.path.join(self.appdata_dir, 'config.json')
        self.defaults = {
            'typing_delay_ms': 30,
            'human_like_delay': False,
            'auto_type': True,
            'code_mode': 'raw',
            'theme': 'dark',
            'server_port': 8765,
            'start_with_windows': False,
            'log_level': 'INFO',
            'bluetooth_enabled': True,
            'bluetooth_com_port': 'auto',
            'connection_mode': 'auto',
            'app_version': '1.0.0',
            'github_repo': 'loki-teche99/typebridge',
            'auto_check_updates': True,
            'last_update_check_ts': 0,
            'update_etag': '',
        }
        self.config = self.defaults.copy()
        self.load()
        
    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception:
                pass
                
    def save(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def get(self, key, default=None):
        fallback = self.defaults.get(key, default)
        return self.config.get(key, fallback)
        
    def set(self, key, value):
        self.config[key] = value
        self.save()
