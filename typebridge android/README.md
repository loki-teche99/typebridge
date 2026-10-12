# TypeBridge Android — Build & Usage Guide

## What is TypeBridge Mobile?

TypeBridge Mobile is the Android companion app that sends text to the paired
**TypeBridge Desktop** Windows app, which then types it character-by-character
as real keyboard input into the focused window.

**You paste text → it appears typed on your PC.**

---

## Requirements

- Android 8.0+ (API 26+)
- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Both devices on same Wi-Fi or hotspot

---

## Build Instructions

### Step 1 — Open in Android Studio

1. Open Android Studio
2. File → Open → select the `typebridge android` folder
3. Wait for Gradle sync to complete (~2 minutes on first run)

### Step 2 — Build and Run

**Debug APK (run on connected phone):**
```bash
./gradlew installDebug
```
Or press the green ▶ Run button in Android Studio.

**Release APK:**
```bash
./gradlew assembleRelease
```

### Step 3 — Allow Permissions

On first launch, grant:
- **Camera** — required for QR code scanning
- **Notifications** — for the foreground service notification

---

## Pairing with Desktop

1. Start TypeBridge Desktop on your PC first.
2. Click **"Pair Device"** on the desktop — a QR code and PIN appear.
3. Open TypeBridge Mobile → tap **"Pair Device"**.
4. Tap **"Scan QR Code"** — scan the desktop's QR code.
5. Verify the 6-digit PIN matches on both screens.
6. Tap **Confirm**.
7. Connection turns 🟢 Green — you're ready.

---

## Usage

1. Make sure TypeBridge Desktop is running and connected (green dot).
2. Open TypeBridge Mobile → Home screen.
3. **Paste or type your Java code** (or any text) into the large text field.
4. Tap **"Send & Type"**.
5. On your PC, **click into the target field** (browser, IDE, etc.).
6. Watch it type every character, one by one.

---

## Architecture

```
presentation/     ← Fragments + ViewModels (MVVM)
domain/           ← Models, UseCases, Repository interfaces
data/             ← Room DB, DataStore, Repository impls
network/          ← OkHttp WebSocket client, Protocol
security/         ← X25519 + AES-256-GCM + TrustManager
service/          ← TypeBridgeService (Foreground Service)
di/               ← Hilt dependency injection modules
```

## Key Dependencies

| Library | Purpose |
|---|---|
| Hilt | Dependency injection |
| Room | Local database (device store, message queue) |
| DataStore | Settings persistence |
| OkHttp | WebSocket client (WSS) |
| BouncyCastle | X25519 ECDH key exchange |
| ZXing Embedded | QR code scanning |
| Gson | JSON serialization |

---

## Protocol

Messages sent over WSS:
```json
{
  "id": "uuid",
  "type": "TEXT_PAYLOAD",
  "payload": "<AES-256-GCM ciphertext, base64>",
  "iv": "<12-byte nonce, base64>",
  "session_id": "uuid",
  "timestamp": 1234567890123
}
```

Encrypted payload for TEXT_PAYLOAD:
```json
{"text": "your text here", "msg_id": "uuid"}
```

---

## Security

- **Transport**: WSS (WebSocket + TLS, self-signed cert)
- **App layer**: AES-256-GCM with session key derived via HKDF-SHA256
- **Key exchange**: X25519 ECDH (raw 32-byte keys via BouncyCastle)
- **Pairing**: 6-digit PIN confirmation prevents MITM

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Gradle sync fails | Check JDK 17 is configured in Android Studio |
| Build fails | Run `./gradlew clean` then retry |
| Can't scan QR | Grant camera permission to the app |
| Connection fails | Check PC firewall allows port 8765 |
| Text not typed | Click into the target field on the PC first |
