# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-12

### Added
- **Universal Android Compatibility**:
  - Full APK signature coverage: v1 (JAR signing), v2 (APK Signature Scheme v2), and v3 (APK Signature Scheme v3).
  - Standalone release keystore (`typebridge-release.keystore`) for consistent upgrade signatures.
  - Multi-window and foldable orientation resilience (`configChanges`).
  - Cleartext traffic enabled for local subnet WebSocket communication across Android 9–15.
  - `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` for aggressive OEM task killers (Xiaomi, Samsung, Oppo, Vivo).
- **Self-Healing Connection Engine**:
  - Unified state machine: `STOPPED` → `DISCOVERING` → `CONNECTING` → `CONNECTED` → `RECONNECTING` → `DEGRADED`.
  - Exponential backoff retry with jitter (100ms - 15s) and automatic reset on stable connection.
  - X25519 session key persistence across app restarts.
  - Rapid zero-delay heartbeat handshake on connection.
- **Reliability & Typing Integrity**:
  - 15-minute sliding window deduplication cache preventing duplicate typing on network reconnects.
  - Win32 `SendInput` hardware keystroke injection with exact 4-space tab expansion.
  - Full Unicode support for Indic scripts (Telugu, Hindi), emojis, and UTF-8 symbols.
  - Robust mDNS registration with hostname/PID qualifying and random-UUID collision immunity (`NonUniqueNameException` fix).
- **GitHub Auto-Updates**:
  - Canonical repository configured to `loki-teche99/typebridge`.
  - Automated release pipeline with GitHub Actions (`ci.yml` and `release.yml`).
  - Cryptographic SHA-256 integrity verification before installing updates.
- **Diagnostics & Support**:
  - One-click support diagnostics export on Windows Desktop and Android.
  - "Get Mobile App" quick actions redirecting to official website (`https://typebridge.42web.io/`).
