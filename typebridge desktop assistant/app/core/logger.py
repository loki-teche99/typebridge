import os
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from PyQt6.QtCore import QObject, pyqtSignal

class LoggerSignals(QObject):
    log_line = pyqtSignal(str)

class StructuredLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StructuredLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance
        
    def _init_logger(self):
        from app.core.config import ConfigManager
        self.config = ConfigManager()
        self.signals = LoggerSignals()
        self.log_deque = deque(maxlen=1000)
        
        log_dir = os.path.join(self.config.appdata_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, 'typebridge.log')
        
        self.logger = logging.getLogger('TypeBridge')
        level_str = self.config.get('log_level').upper()
        level = getattr(logging, level_str, logging.INFO)
        self.logger.setLevel(level)
        self.logger.handlers = []
        
        handler = RotatingFileHandler(self.log_file, maxBytes=5*1024*1024, backupCount=1)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def _emit(self, level, message):
        line = f"[{level}] {message}"
        self.log_deque.append(line)
        self.signals.log_line.emit(line)
        
    def info(self, message):
        self.logger.info(message)
        self._emit('INFO', message)
        
    def warning(self, message):
        self.logger.warning(message)
        self._emit('WARNING', message)
        
    def error(self, message):
        self.logger.error(message)
        self._emit('ERROR', message)
        
    def debug(self, message):
        self.logger.debug(message)
        self._emit('DEBUG', message)
