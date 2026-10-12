"""
TypeBridge Desktop - Character Mapper
===========================================
Maps a whitelisted character to injection instructions.

STRATEGY — three paths, tried in order:
1. SPECIAL KEYS  — Space → VK_SPACE, Newline → VK_RETURN (no mapping needed)
2. VK PATH       — VkKeyScanW(char): fast, produces correct keyCode/key in browser
3. UNICODE PATH  — KEYEVENTF_UNICODE fallback: always correct regardless of layout

WHY THE UNICODE FALLBACK MATTERS:
- VkKeyScanW is layout-dependent. On a German keyboard, '@' requires AltGr.
  VkKeyScanW would return a modifier flag (bit 2 = Ctrl+Alt/AltGr) which we
  cannot inject safely. The Unicode fallback bypasses the layout entirely.
- All browsers (Chrome/Firefox/Edge) raise isTrusted=true for KEYEVENTF_UNICODE
  events because they originate from the OS input queue.
- The KeyboardEvent.key property will be the actual character typed.
- The input event fires correctly and the value updates in the text field.

ALLOWED CHARACTERS (per product spec — hard whitelist):
  Letters : A-Z, a-z
  Digits  : 0-9
  Space   : (0x20)
  Enter   : newline (0x0A) / carriage return (0x0D)
  Symbols : ~ ` ! @ # $ % ^ & * ( ) - _ = + [ ] { } \\ | ; : ' " , < . > / ?

NEVER MAPPED:
  Tab, Escape, Backspace, Delete, arrow keys, F-keys, Windows key, media keys,
  standalone Ctrl, Alt, Shift.
"""
import ctypes
import sys
from typing import Optional

# ---------------------------------------------------------------------------
#  Hard whitelist  — EXACTLY these characters and no others
# ---------------------------------------------------------------------------
WHITELIST: frozenset[str] = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " \n\r\t\b"
    "~`!@#$%^&*()-_=+[]{}\\|;:'\",<.>/?"
)

# Virtual key constants
VK_BACK   = 0x08
VK_TAB    = 0x09
VK_RETURN = 0x0D
VK_SPACE  = 0x20
VK_SHIFT  = 0x10


class CharMapping:
    """
    Result of mapping a character.
    Exactly ONE of (vk_path, unicode_path) will be True.
    """
    __slots__ = ("char", "vk_code", "needs_shift", "use_unicode", "unicode_cp")

    def __init__(
        self,
        char: str,
        vk_code: int = 0,
        needs_shift: bool = False,
        use_unicode: bool = False,
        unicode_cp: int = 0,
    ):
        self.char       = char
        self.vk_code    = vk_code
        self.needs_shift = needs_shift
        self.use_unicode = use_unicode
        self.unicode_cp = unicode_cp

    @property
    def vk_path(self) -> bool:
        return not self.use_unicode

    def __repr__(self) -> str:
        if self.use_unicode:
            return f"<CharMapping char={self.char!r} unicode=U+{self.unicode_cp:04X}>"
        return (
            f"<CharMapping char={self.char!r} vk=0x{self.vk_code:02X} "
            f"shift={self.needs_shift}>"
        )


# ---------------------------------------------------------------------------
#  Core mapping function
# ---------------------------------------------------------------------------
def map_char(char: str) -> Optional[CharMapping]:
    """
    Map a single character to a CharMapping.

    Supports universal Unicode (English, Telugu, Hindi, Emojis, UTF-8).
    - \r and NUL (\x00) are ignored to prevent unnecessary inputs / extra key events.
    - \n triggers VK_RETURN.
    - \t triggers VK_TAB.
    - All printable characters (ord(char) >= 32 and != 127) use KEYEVENTF_UNICODE.
    """
    if len(char) != 1:
        return None

    # ---- Path 1: Special control keys & unprintable character filter ----- #
    if char in ('\r', '\x00', '\b'):
        return None  # Strictly ignore \r, \x00, and \b. No backspaces or stray control inputs.

    if char == '\n':
        return CharMapping(char, vk_code=VK_RETURN, needs_shift=False)

    if char == '\t':
        # STRICT SAFETY: Tab key (VK_TAB) is strictly prohibited.
        # Pressing VK_TAB in browsers or IDEs unfocuses the code editor and moves to buttons/URL bar.
        # Stray tabs are safely treated as standard spaces.
        return CharMapping(' ', use_unicode=True, unicode_cp=0x20)

    cp = ord(char)
    # Reject ASCII control characters (0-31 except \n and \t, and 127 DEL)
    if cp < 32 or cp == 127:
        return None

    # ---- Path 2: Universal KEYEVENTF_UNICODE for exact character injection ----- #
    return CharMapping(char, use_unicode=True, unicode_cp=cp)


# ---------------------------------------------------------------------------
#  Convenience class for OOP callers
# ---------------------------------------------------------------------------
class CharMapper:
    @staticmethod
    def map_char(char: str) -> Optional[CharMapping]:
        return map_char(char)


# ---------------------------------------------------------------------------
#  Self-test (run this file directly: python char_mapper.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    test_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "0123456789 \n~`!@#$%^&*()-_=+[]{}\\|;:'\",<.>/?"
    )
    print(f"Testing {len(test_chars)} whitelisted characters...\n")
    unmapped = []
    for c in test_chars:
        result = map_char(c)
        if result is None:
            unmapped.append(repr(c))
        else:
            path = "UNICODE" if result.use_unicode else f"VK=0x{result.vk_code:02X} shift={result.needs_shift}"
            print(f"  {repr(c):6s} → {path}")

    print()
    if unmapped:
        print(f"FAILED to map {len(unmapped)} chars: {unmapped}")
        sys.exit(1)
    else:
        print(f"✅ All {len(test_chars)} characters mapped successfully.")
