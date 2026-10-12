"""
TypeBridge Desktop - Typing Worker
===========================================
QThread that dequeues (text, msg_id) items and injects them
character-by-character using the keyboard injector.

INJECTION LOGIC:
- For each character, CharMapper returns a CharMapping with either:
    - vk_path=True  → KeyboardInjector.type_character(vk_code, needs_shift)
    - use_unicode=True → KeyboardInjector.type_character_unicode(char)
- Characters not in the whitelist are silently skipped (never injected)
- Pausing is instant — blocks after the current character completes
- Stopping drains the current item cleanly before exiting

DELAY:
- Default 30ms between characters (configurable 5–200ms in Settings)
- Human-like mode adds Gaussian noise: ±30% variation, clamped to [5ms, 3×delay]
"""
import queue
import random
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.config import ConfigManager
from app.typing_engine.char_mapper import CharMapper
from app.typing_engine.java_formatter import JavaCodeFormatter
from app.typing_engine.keyboard_injector import KeyboardInjector


class TypingWorker(QThread):
    # chars_done, total_chars, msg_id
    progress_signal = pyqtSignal(int, int, str)
    # msg_id — fired when a complete text item is finished
    complete_signal = pyqtSignal(str)
    # msg_id — fired when ACK should be sent back to Android
    ack_needed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue        = queue.Queue()
        self._running      = True
        self._skip_current = False
        self._paused       = threading.Event()
        self._paused.set()          # Initially NOT paused (event is set = unblocked)
        self.config        = ConfigManager()
        self.injector      = KeyboardInjector()

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def enqueue(self, text: str, msg_id: str):
        """Thread-safe: add a text item to the typing queue."""
        self._queue.put((text, msg_id))

    def pause(self):
        """Pause typing after the current character completes."""
        self._paused.clear()

    def resume(self):
        """Resume typing from where it paused."""
        self._paused.set()

    def stop(self):
        """Signal the worker to finish current character and exit."""
        self._running = False
        self._paused.set()  # Unblock if currently paused

    def clear_queue(self):
        """Clear queued items and immediately abort current typing."""
        self._skip_current = True
        with self._queue.mutex:
            self._queue.queue.clear()
        self._paused.set()  # Unblock if paused so current item aborts

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        while self._running:
            # Wait up to 50ms for a new text item
            try:
                text, msg_id = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                self._type_text(text, msg_id)
            except Exception as e:
                print(f"[TypingWorker] Error typing text: {e}")

    def _prepare_text_for_typing(self, text: str) -> str:
        """
        Preprocesses text payload using JavaCodeFormatter:
        1. Sanitizes non-breaking spaces (\u00A0), smart quotes, and CRLF line endings.
        2. Considers line 1 extra spaces and normalizes common leading margins.
        3. Formats blocks ({ ... }) with exact 4-space syntax and structure.
        """
        mode = self.config.get('code_mode', 'java_perfect')
        if mode == 'raw':
            return JavaCodeFormatter.sanitize(text)
        elif mode == 'ide':
            return JavaCodeFormatter.prepare_for_ide_mode(text)
        else:
            # 'java_perfect': Full mathematical 4-space Java syntax & indentation
            return JavaCodeFormatter.format_java_structure(text)

    def _type_text(self, text: str, msg_id: str):
        """Type every character in text, respecting pause/stop signals."""
        self._skip_current = False
        prepared_text = self._prepare_text_for_typing(text)
        if '\t' in prepared_text:
            prepared_text = prepared_text.expandtabs(4)
        total  = len(prepared_text)
        typed  = 0

        for idx, char in enumerate(prepared_text):
            if not self._running or self._skip_current:
                return

            # Block here if the user paused
            self._paused.wait()
            if not self._running or self._skip_current:
                return

            try:
                # Map the character
                mapping = CharMapper.map_char(char)

                if mapping is not None:
                    if mapping.use_unicode:
                        # KEYEVENTF_UNICODE path — layout-independent, works on all sites
                        self.injector.type_character_unicode(char)
                    else:
                        # VK code path — fast and produces correct KeyboardEvent.key/.code
                        self.injector.type_character(mapping.vk_code, mapping.needs_shift)
            except Exception as e:
                pass  # Skip character safely without killing the typing loop

            # Only count characters that were actually typed
            # (includes skipped-whitelist chars to keep progress accurate)
            typed += 1
            self.progress_signal.emit(typed, total, msg_id)

            # Per-character delay
            base_delay = float(self.config.get('typing_delay_ms'))
            delay_ms   = base_delay
            if self.config.get('human_like_delay'):
                sigma    = max(2.0, base_delay * 0.3)
                delay_ms = random.gauss(base_delay, sigma)
                # Clamp: never faster than 5 ms, never slower than 3× the base
                delay_ms = max(5.0, min(delay_ms, base_delay * 3.0))

            time.sleep(delay_ms / 1000.0)

        # All characters done
        if self._running and not self._skip_current:
            self.complete_signal.emit(msg_id)
            self.ack_needed.emit(msg_id)
