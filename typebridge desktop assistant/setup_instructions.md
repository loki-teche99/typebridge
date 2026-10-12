# TypeBridge Desktop — Setup & Usage Guide

## What is TypeBridge Desktop?

TypeBridge Desktop receives text from the TypeBridge Mobile Android app and **types it
character-by-character as real keyboard input** into whatever window is currently focused on
your Windows PC — including browsers, IDEs, terminals, text editors, and any application
that accepts keyboard typing.

This is **NOT clipboard paste (Ctrl+V)**. It generates genuine OS-level keyboard events
via the Win32 `SendInput` API, identical to a human typing on a physical keyboard.

---

## Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.11 or newer — https://www.python.org/downloads/
- Both your Android phone and this PC must be on the **same Wi-Fi network** (or hotspot)

---

## Installation

### Step 1 — Install Python 3.11+

Download from https://www.python.org/downloads/windows/

During installation, tick **"Add Python to PATH"**.

Verify:
```powershell
python --version
# Should print Python 3.11.x or newer
```

### Step 2 — Install dependencies

Open PowerShell in the `typebridge desktop assistant` folder and run:

```powershell
pip install -r requirements.txt
```

This installs:
- `PyQt6` — UI framework
- `websockets` — async WebSocket server
- `cryptography` — TLS cert generation, X25519, AES-256-GCM
- `qrcode[pil]` — QR code generation for pairing
- `Pillow` — image support
- `zeroconf` — mDNS/LAN discovery

---

## Running the App

```powershell
python main.py
```

The app will:
1. Start in the system tray (bottom-right of taskbar)
2. Open the main window
3. Generate a self-signed TLS certificate (first run only, stored in `%APPDATA%\TypeBridge\tls\`)
4. Start the WebSocket server on port **8765**
5. Advertise itself via mDNS on the local network

---

## Firewall Setup (Required!)

Windows Firewall will block port 8765 by default. You must allow it:

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="TypeBridge WSS" dir=in action=allow protocol=TCP localport=8765
```

Or via Windows Defender Firewall UI:
1. Open Windows Defender Firewall → Advanced Settings
2. Inbound Rules → New Rule → Port → TCP → 8765 → Allow

---

## Pairing with the Android App

1. Open the desktop app. Click **"Pair Device"**.
2. A QR code will appear along with a 6-digit PIN.
3. On the Android phone, open TypeBridge Mobile → tap **"Pair Device"** → tap **"Scan QR Code"**.
4. Scan the QR code on screen.
5. The Android app will show the PIN — verify it matches the one on the desktop.
6. Tap **Confirm** on both devices.
7. The connection status will turn green: ✅ Connected.

---

## Usage

1. On your Android phone, open TypeBridge Mobile.
2. Paste or type your text in the large text field.
3. Tap **"Send & Type"**.
4. **Click into the target field on your PC** (browser text box, IDE, terminal, etc.).
5. TypeBridge will type each character one by one into that focused window.

### Important
- **Click into the target field BEFORE or immediately after tapping Send.**
- Typing begins approximately 0–1 second after the text is received.
- You can adjust the typing speed in Settings (default: 30ms per character).

---

## Settings

| Setting | Default | Description |
|---|---|---|
| Typing delay | 30 ms | Milliseconds between each character |
| Human-like delay | Off | Adds random ±30% variation to delay |
| Auto-type | On | Start typing immediately when text arrives |
| Theme | Dark | Dark or light UI |
| Start with Windows | Off | Launch on Windows login (uses registry) |
| Server port | 8765 | WebSocket port |

---

## Allowed Characters

TypeBridge Desktop only types:
- Letters: `A-Z`, `a-z`
- Digits: `0-9`
- Space (` `)
- Enter / newline (`↵`)
- Symbols: `` ~ ` ! @ # $ % ^ & * ( ) - _ = + [ ] { } \ | ; : ' " , < . > / ? ``

**Never injected**: Tab, Escape, Backspace, Delete, arrow keys, F1–F12, Windows key, media keys.

---

## Building a Standalone `.exe`

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name TypeBridgeDesktop --icon assets/icon.ico main.py
```

The executable will be in the `dist/` folder.

---

## Data Storage

All data is stored in `%APPDATA%\TypeBridge\`:
- `config.json` — settings
- `tls/` — self-signed TLS certificate
- `trust.db` — paired device records
- `queue.db` — persistent typing queue
- `logs/typebridge.log` — rotating log file

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Cannot connect from Android | Check firewall — allow port 8765 TCP |
| QR code not scanning | Ensure both devices on same Wi-Fi / hotspot |
| Text not appearing | Click into the target field first |
| Wrong characters typed | Check keyboard layout matches (US QWERTY assumed) |
| App doesn't start | Check Python version ≥ 3.11, run `pip install -r requirements.txt` again |
