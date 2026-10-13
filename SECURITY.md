# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Security Architecture & Assumptions

TypeBridge is designed for local peer-to-peer productivity between a trusted mobile device and a personal workstation.

### Cryptographic Protections:
1. **End-to-End Encryption**: All transmitted text and control signals are encrypted using **AES-256-GCM** with unique 12-byte initialization vectors (IVs) per message.
2. **Key Agreement**: Session keys are derived using **X25519 Elliptic Curve Diffie-Hellman (ECDH)** combined with HKDF-SHA256.
3. **Authentication**: Peer authorization requires a physical 6-digit one-time PIN or QR code scanned from the local desktop display. Discovery of a device does NOT grant access without mutual cryptographic key exchange.
4. **Transport Layer Security**: Wi-Fi WebSocket communication uses TLS encryption over port 8765.
5. **Integrity Validation**: Automated software updates verify SHA-256 hashes against trusted release manifests before execution.
6. **Zero Cloud Storage**: Source code and keystroke data are streamed exclusively across the local subnet / Bluetooth link and are never stored on external cloud servers or remote databases.
7. **Secrets & Keystore Protection**: Release keystores, passwords, and private certificates are strictly excluded from source control via `.gitignore`. Production release signing in CI is powered exclusively by encrypted GitHub Actions repository secrets (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`). Local developer signing uses gitignored `keystore.properties`.

---

## Reporting a Vulnerability


- Do **not** open public issues for sensitive security vulnerabilities.
- Please include reproduction steps, environment details, and proof of concept where possible.
