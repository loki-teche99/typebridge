# TypeBridge Release Management Guide

This document defines the official release process for TypeBridge across Android, Windows Desktop, and the official website.

---

## 1. Canonical Repository

The canonical production repository for TypeBridge is:
[https://github.com/loki-teche99/typebridge](https://github.com/loki-teche99/typebridge)

---

## 2. Versioning Strategy

TypeBridge strictly adheres to [Semantic Versioning 2.0.0](https://semver.org/):
`MAJOR.MINOR.PATCH` (e.g., `1.0.0` → `1.0.1` → `1.1.0`)

When bumping versions, synchronize the version across all components:
1. **Android**: `versionCode` (integer) and `versionName` (string) in `typebridge android/app/build.gradle.kts`.
2. **Windows Desktop**: `CURRENT_VERSION` in `app/core/updater.py` and `app_version` in `app/core/config.py`.
3. **Inno Setup**: `#define MyAppVersion "X.Y.Z"` in `installer.iss`.
4. **Website**: `version` in `website/config.js`.

---

## 3. Automated GitHub Actions Release Workflow

The automated release pipeline is configured in `.github/workflows/release.yml`.

### How to Trigger a Release:
1. Commit all validated changes to `main`:
   ```bash
   git add .
   git commit -m "chore(release): prepare v1.0.0 release"
   git push origin main
   ```
2. Create and push an annotated Git tag:
   ```bash
   git tag -a v1.0.0 -m "TypeBridge v1.0.0 Production Release"
   git push origin v1.0.0
   ```
3. GitHub Actions will automatically:
   - Build the signed Android APK (`TypeBridge-Android-v1.0.0.apk`) using the release keystore.
   - Compile the standalone Windows executable and Inno Setup installer (`TypeBridgeSetup-v1.0.0.exe`).
   - Calculate cryptographic SHA-256 hashes (`sha256sums.txt`).
   - Generate `release-manifest.json` adhering to the TypeBridge update schema.
   - Create a GitHub Release with all production assets attached.

---

## 4. Local Build Commands

If you need to produce release packages locally on your development machine:

### Android APK Build:
```bash
cd "typebridge android"
cmd /c "gradlew.bat assembleRelease --no-daemon"
# Output located at: app/build/outputs/apk/release/app-release.apk
```

### Windows Desktop Executable & Installer Build:
```bash
cd "typebridge desktop assistant"
python build_desktop.py
# Output located at: installer_output/TypeBridgeSetup-v1.0.0.exe
```

### Website InfinityFree Package Build (<10 MB):
```bash
cd "website"
python build_infinityfree_package.py
# Output located at: infinityfree_htdocs.zip
```

---

## 5. Post-Release Verification Checklist

- [ ] Download `TypeBridgeSetup-v1.0.0.exe` from GitHub Releases and verify installation on Windows 10/11.
- [ ] Download `TypeBridge-Android-v1.0.0.apk` and install on a physical phone.
- [ ] Open Desktop Assistant → Click **Check for Updates** → Verify it reports "Up to date".
- [ ] Open Android App → Go to **Settings** → Click **Check for Updates** → Verify it reports "Up to date".
- [ ] Test pairing via QR code scan and manual PIN.
