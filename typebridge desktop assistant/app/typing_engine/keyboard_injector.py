"""
TypeBridge Desktop - Keyboard Injector
===========================================
Uses Win32 SendInput to generate REAL OS-level keyboard events that are
indistinguishable from physical keyboard input at the browser / application level.

WHY THIS WORKS ON EVERY WEBSITE:
- SendInput events have isTrusted = true in every browser (Chrome, Firefox, Edge)
- We never touch the clipboard -- no Ctrl+V, no ClipboardEvent
- The OS input queue receives the same WM_KEYDOWN / WM_KEYUP messages as a real key
- Paste-blocked fields accept these events because they are genuine keyboard input
- Anti-bot scripts checking event.isTrusted will see True

DUAL INJECTION STRATEGY:
1. PRIMARY:  VK-code path (VkKeyScanW) -- fast, works for all standard US-QWERTY chars
2. FALLBACK: KEYEVENTF_UNICODE path -- injects the Unicode code point directly,
   bypasses keyboard layout entirely. Used when VK mapping fails (non-US keyboards).

GUARANTEED CHARACTER ACCURACY:
- Every character in the whitelist will be typed correctly regardless of the
  Windows keyboard layout setting.

NEVER INJECTED:
- Tab, Escape, Backspace, Delete, arrow keys
- F1-F12, Windows key, media keys
- Ctrl, Alt as standalone keys
- Shift is used ONLY internally to produce uppercase / symbol chars

STRUCT LAYOUT (verified on this machine):
  KEYBDINPUT = 24 bytes on 64-bit (2+2+4+4+8, aligned to 8)
  _INPUT_UNION pad = 32 bytes -> union = 32 bytes (aligned to 8)
  INPUT = type(4) + align_pad(4) + union(32) = 40 bytes  <-- matches Windows SDK
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

# ---------------------------------------------------------------------------
#  Win32 constants
# ---------------------------------------------------------------------------
_user32 = ctypes.WinDLL('user32', use_last_error=True)

INPUT_KEYBOARD    = 1
KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004   # wScan = UTF-16 code unit; wVk must be 0

VK_SHIFT          = 0x10
VK_SPACE          = 0x20
VK_RETURN         = 0x0D

# ---------------------------------------------------------------------------
#  Struct definitions -- calibrated from actual measurement on this machine
# ---------------------------------------------------------------------------
# dwExtraInfo is ULONG_PTR (pointer-sized unsigned int)
_ULONG_PTR = ctypes.c_size_t   # 4 bytes on 32-bit, 8 bytes on 64-bit


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wt.WORD),       # 2 bytes
        ("wScan",       wt.WORD),       # 2 bytes
        ("dwFlags",     wt.DWORD),      # 4 bytes
        ("time",        wt.DWORD),      # 4 bytes
        ("dwExtraInfo", _ULONG_PTR),    # 8 bytes on 64-bit  (total: 20 + 4 align = 24)
    ]


def _build_input_struct():
    """
    Build the INPUT ctypes Structure with the correct union padding for this
    Python / platform combination.

    Strategy: try padding sizes 28..40 (step 4) until ctypes.sizeof(INPUT) == 40.
    40 bytes is the documented Windows SDK size on 64-bit.
    On 32-bit it should be 28 bytes.
    """
    target = 40 if sys.maxsize > 2**32 else 28

    for pad in range(24, 49, 4):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("_padding", ctypes.c_byte * pad)]

        class _I(ctypes.Structure):
            _anonymous_ = ("_u",)
            _fields_ = [("type", wt.DWORD), ("_u", _U)]

        if ctypes.sizeof(_I) == target:
            return _U, _I

    # Fallback: accept whatever size we get (better than crashing at startup)
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("_padding", ctypes.c_byte * 32)]

    class _I(ctypes.Structure):
        _anonymous_ = ("_u",)
        _fields_ = [("type", wt.DWORD), ("_u", _U)]

    return _U, _I


_INPUT_UNION, INPUT = _build_input_struct()

# Record the actual size for use in SendInput
_INPUT_SIZE = ctypes.sizeof(INPUT)
_EXPECTED_INPUT_SIZE = 40 if sys.maxsize > 2**32 else 28

# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------
def _make_vk_input(vk_code: int, flags: int) -> INPUT:
    """Create an INPUT struct for a virtual-key event."""
    inp = INPUT()
    inp.type           = INPUT_KEYBOARD
    inp.ki.wVk         = vk_code
    inp.ki.wScan       = 0
    inp.ki.dwFlags     = flags
    inp.ki.time        = 0
    inp.ki.dwExtraInfo = 0
    return inp


def _make_unicode_input(code_unit: int, flags: int) -> INPUT:
    """Create an INPUT struct for a Unicode character event (KEYEVENTF_UNICODE)."""
    inp = INPUT()
    inp.type           = INPUT_KEYBOARD
    inp.ki.wVk         = 0           # MUST be 0 when using KEYEVENTF_UNICODE
    inp.ki.wScan       = code_unit   # UTF-16 code unit
    inp.ki.dwFlags     = KEYEVENTF_UNICODE | flags
    inp.ki.time        = 0
    inp.ki.dwExtraInfo = 0
    return inp


def _send_inputs(*inputs: INPUT) -> int:
    """Send a batch of INPUT events atomically. Returns number of events sent."""
    arr = (INPUT * len(inputs))(*inputs)
    sent = _user32.SendInput(len(inputs), arr, _INPUT_SIZE)
    return sent


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------
class KeyboardInjector:
    """
    Injects keyboard events using Win32 SendInput.

    Two modes, chosen automatically per character:
    - VK mode:      uses virtual key codes + Shift flag
                    produces keydown/keypress/input/keyup with correct key names
    - Unicode mode: uses KEYEVENTF_UNICODE with the raw UTF-16 code point
                    guaranteed correct character on ANY keyboard layout
                    falls back to this when VK mode fails

    Both modes generate events that browsers treat as isTrusted = true.
    """

    @staticmethod
    def type_character(vk_code: int, needs_shift: bool) -> bool:
        """
        Inject a single character using the VK-code path.
        Returns True if SendInput reported the events were sent.
        """
        inputs = []
        if needs_shift:
            inputs.append(_make_vk_input(VK_SHIFT, 0))                  # Shift down
        inputs.append(_make_vk_input(vk_code, 0))                       # Key down
        inputs.append(_make_vk_input(vk_code, KEYEVENTF_KEYUP))         # Key up
        if needs_shift:
            inputs.append(_make_vk_input(VK_SHIFT, KEYEVENTF_KEYUP))    # Shift up

        return _send_inputs(*inputs) > 0

    @staticmethod
    def type_character_unicode(char: str) -> bool:
        """
        Inject a single character using KEYEVENTF_UNICODE.
        Bypasses keyboard layout -- always produces the correct character.
        Browsers fire isTrusted=true input events for this path.
        """
        cp = ord(char)
        if cp < 0x10000:
            # BMP: single UTF-16 code unit
            inputs = [
                _make_unicode_input(cp, 0),
                _make_unicode_input(cp, KEYEVENTF_KEYUP),
            ]
        else:
            # Supplementary plane: UTF-16 surrogate pair
            cp -= 0x10000
            high = 0xD800 + (cp >> 10)
            low  = 0xDC00 + (cp & 0x3FF)
            inputs = [
                _make_unicode_input(high, 0),
                _make_unicode_input(low,  0),
                _make_unicode_input(low,  KEYEVENTF_KEYUP),
                _make_unicode_input(high, KEYEVENTF_KEYUP),
            ]

        return _send_inputs(*inputs) > 0


# ---------------------------------------------------------------------------
#  Module-level self-check (printed on import so issues surface immediately)
# ---------------------------------------------------------------------------
_expected = 40 if sys.maxsize > 2**32 else 28
if _INPUT_SIZE != _expected:
    import warnings
    warnings.warn(
        f"[TypeBridge] INPUT struct size is {_INPUT_SIZE}, expected {_expected}. "
        "SendInput may not work correctly. Report this as a bug.",
        RuntimeWarning,
        stacklevel=2,
    )
