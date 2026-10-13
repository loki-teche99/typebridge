import os
import json
import shutil
import ctypes

APP_VERSION = "1.0.1"


def is_packaged_msix() -> bool:
    """Check if the application is currently running as a packaged MSIX / Store app."""
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        length = ctypes.c_uint32(0)
        # 15700 = APPMODEL_ERROR_NO_PACKAGE
        rc = kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), None)
        return rc != 15700
    except Exception:
        return bool(os.environ.get('PACKAGE_FAMILY_NAME'))


class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance
        
    def _init_config(self):
        self.is_msix = is_packaged_msix()
        self.appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'TypeBridge')
        os.makedirs(self.appdata_dir, exist_ok=True)
        self.config_path = os.path.join(self.appdata_dir, 'config.json')

        # Check for legacy Inno Setup data migration if running inside MSIX
        self._check_legacy_migration()

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
            'app_version': APP_VERSION,
            'github_repo': 'loki-teche99/typebridge',
            'auto_check_updates': not self.is_msix, # Microsoft Store manages updates for MSIX edition
            'last_update_check_ts': 0,
            'update_etag': '',
        }
        self.config = self.defaults.copy()
        self.load()

    def _check_legacy_migration(self):
        """
        Safely preserve configuration and paired-device trust tokens when migrating
        from the legacy Inno Setup edition to Microsoft Store MSIX.
        """
        if not self.is_msix:
            return
        # If current package appdata is empty, check common legacy paths
        user_profile = os.environ.get('USERPROFILE', '')
        legacy_roaming = os.path.join(user_profile, 'AppData', 'Roaming', 'TypeBridge')
        if os.path.exists(legacy_roaming) and not os.path.exists(self.config_path):
            try:
                for item in os.listdir(legacy_roaming):
                    s = os.path.join(legacy_roaming, item)
                    d = os.path.join(self.appdata_dir, item)
                    if os.path.isfile(s) and not os.path.exists(d):
                        shutil.copy2(s, d)
            except Exception:
                pass

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception:
                pass

        # Always enforce canonical app_version of running binary
        self.config['app_version'] = APP_VERSION

        # Migrate any stale repository slug
        if self.config.get('github_repo') == 'v4358137-lang/typebridge':
            self.config['github_repo'] = 'loki-teche99/typebridge'
            self.save()
                
    def save(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def get(self, key, default=None):
        if key == 'app_version':
            return APP_VERSION
        fallback = self.defaults.get(key, default)
        return self.config.get(key, fallback)
        
    def set(self, key, value):
        self.config[key] = value
        self.save()

