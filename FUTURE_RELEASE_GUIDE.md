# TypeBridge — Complete Future Update Release Process

This document is your exact step-by-step Standard Operating Procedure (SOP) for shipping future TypeBridge updates (e.g. `v1.0.2`, `v1.0.3`, `v1.1.0`) to Android and Windows desktop users.

Because **v1.0.1** is your permanent foundation, any update shipped following this process will be detected and installed over-the-air across all user devices with **zero loss of pairing data or settings**.

---

## The 4 Standard Release Assets

Every GitHub Release **must** contain these 4 files:
1. `TypeBridge-Android-v<VERSION>.apk`
2. `TypeBridgeSetup-v<VERSION>.exe`
3. `release-manifest.json`
4. `sha256sums.txt`

---

## Complete Release Walkthrough (Example: Releasing `v1.0.2`)

### STEP 1: Update Version Numbers in the Code (3 Files)

Before building, update the version in the following 3 locations:

#### 1. Android Gradle Configuration
**File:** `typebridge android/app/build.gradle.kts`
```kotlin
defaultConfig {
    applicationId = "com.typebridge.mobile"
    minSdk = 24
    targetSdk = 35
    versionCode = 3             // <-- Increment by 1 (v1.0.1 was 2, v1.0.2 is 3)
    versionName = "1.0.2"       // <-- Set new version string
    ...
}
```

#### 2. Desktop Updater Constant
**File:** `typebridge desktop assistant/app/core/updater.py`
```python
CURRENT_VERSION = "1.0.2"      # <-- Set new version string (around line 21)
```

#### 3. Inno Setup Compiler Config
**File:** `typebridge desktop assistant/installer.iss`
```ini
#define MyAppVersion "1.0.2"   ; <-- Set new version string (around line 4)
```

---

### STEP 2: Build the Production Binaries

Open your PowerShell terminal in the project root: `c:\Users\lokes\Music\typeanywhere`

#### 1. Build Signed Android APK
```powershell
cd "typebridge android"
.\gradlew assembleRelease
cd ..
```
*Output produced:* `typebridge android/app/build/outputs/apk/release/app-release.apk`  
*Signed automatically with:* `typebridge-release.keystore`

#### 2. Build Windows Setup Installer
```powershell
cd "typebridge desktop assistant"
python build_desktop.py
cd ..
```
*Output produced:* `typebridge desktop assistant/installer_output/TypeBridgeSetup-v1.0.2.exe`

---

### STEP 3: Auto-Generate Manifest and Checksums (1 Command)

In the root directory `c:\Users\lokes\Music\typeanywhere`, run:

```powershell
python generate_release_manifest.py v1.0.2
```

**What this does automatically:**
- Copies the `.apk` and `.exe` into `Release_Packages\v1.0.2\`
- Renames them to canonical names: `TypeBridge-Android-v1.0.2.apk` and `TypeBridgeSetup-v1.0.2.exe`
- Computes SHA-256 hashes and exact file sizes
- Generates `sha256sums.txt`
- Generates `release-manifest.json`

---

### STEP 4: Publish on GitHub Releases

1. Open your browser and navigate to:  
   **`https://github.com/loki-teche99/typebridge/releases/new`**

2. Fill in the release fields:
   - **Choose a tag / Tag version:** `v1.0.2` *(Type `v1.0.2` and select "Create new tag on publish")*
   - **Target:** `main`
   - **Release title:** `TypeBridge v1.0.2`
   - **Description:** Enter your changelog / release notes (e.g., bug fixes, performance improvements)

3. **Attach binaries:**
   Drag and drop the **4 files** from `Release_Packages\v1.0.2\` into the upload box:
   - `TypeBridge-Android-v1.0.2.apk`
   - `TypeBridgeSetup-v1.0.2.exe`
   - `release-manifest.json`
   - `sha256sums.txt`

4. Click **Publish release**.

---

### STEP 5: Verification (What Happens Automatically)

Once published on GitHub:

1. **On Android Phone (Running v1.0.1):**
   - User opens TypeBridge -> Settings -> Tap **Check for Updates** (or waits for the 7-day auto-check).
   - The app detects `v1.0.2`, checks SHA-256 integrity, downloads the APK, and prompts to Update.
   - Tap **Update** -> Installs in-place with zero data or pairing loss.

2. **On Windows Laptop (Running v1.0.1):**
   - User clicks **Check for Updates** (or launches the app).
   - Update Dialog pops up: **"🚀 TypeBridge Update Available - Version 1.0.2 is ready to install"**.
   - User clicks **Update & Restart Now**.
   - The app downloads `TypeBridgeSetup-v1.0.2.exe`, validates SHA-256 against `release-manifest.json`, executes silent upgrade, and restarts running **v1.0.2**.

---

### Quick Cheat-Sheet Summary

```powershell
# 1. Update version numbers in build.gradle.kts, updater.py, installer.iss
# 2. Build Android:
cd "typebridge android"; .\gradlew assembleRelease; cd ..
# 3. Build Windows:
cd "typebridge desktop assistant"; python build_desktop.py; cd ..
# 4. Generate package bundle:
python generate_release_manifest.py v1.0.2
# 5. Upload all 4 files from Release_Packages/v1.0.2/ to GitHub Releases!
```
