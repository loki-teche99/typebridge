from collections import defaultdict
from PyQt6.QtCore import QObject, pyqtSignal

class EventBusSignals(QObject):
    connection_changed = pyqtSignal(dict)
    text_received = pyqtSignal(dict)
    typing_progress = pyqtSignal(dict)
    typing_complete = pyqtSignal(dict)
    pairing_request = pyqtSignal(dict)
    pairing_complete = pyqtSignal(dict)
    log_line = pyqtSignal(str)
    ack_needed = pyqtSignal(str)

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.signals = EventBusSignals()
        return cls._instance
        
    def publish(self, event_name, payload):
        if hasattr(self.signals, event_name):
            getattr(self.signals, event_name).emit(payload)
            
    def subscribe(self, event_name, callback):
        if hasattr(self.signals, event_name):
            getattr(self.signals, event_name).connect(callback)
