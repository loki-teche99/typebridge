# TypeBridge — Windows Microsoft Store & MSIX Release Guide

This document provides the complete, production-grade guide for publishing and maintaining **TypeBridge** on the **Microsoft Store** using modern MSIX packaging, as well as preserving data migration for existing Win32 Inno Setup users.

---

## 1. Locked Store Identity (Microsoft Partner Center)

TypeBridge is locked to the official product registration in Microsoft Partner Center:

| Identity Field | Value |
|---|---|
| **Package Name (`Name`)** | `MadeByLokesh.Typebridge` |
| **Publisher (`Publisher`)** | `CN=9E9E696E-AFB3-4245-B9D4-E5822F2EDB0A` |
| **Publisher Display Name** | `MadeByLokesh` |
| **Package Family Name (PFN)** | `MadeByLokesh.Typebridge_d4xnygzcj6ts8` |
| **Store Product ID** | `9PL56S4CL4NW` |
| **Direct Store Protocol Link** | `ms-windows-store://pdp/?ProductId=9PL56S4CL4NW` |
| **Target Architecture** | `x64` |
| **Minimum Windows OS** | `Windows 10 Build 17763 (Version 1809)` |

> [!IMPORTANT]
> Never modify the `Name`, `Publisher`, or `PublisherDisplayName` fields. Changing any of these values breaks Store updates and identity continuity.

---

## 2. Release Artifacts Generated

In `Release_Packages/`:
- **`TypeBridge-1.0.1-x64.msix`**: Production MSIX package built with Windows SDK `makeappx.exe`.
- **`TypeBridge-1.0.1-x64.msixupload`**: Production submission bundle for Microsoft Partner Center.
- **`TypeBridge_TestCert.cer`** (in `typebridge desktop assistant/msix/`): Public certificate for local sideloading / testing.

---

## 3. Step-by-Step Microsoft Partner Center Submission

1. Go to the [Microsoft Partner Center Dashboard](https://partner.microsoft.com/dashboard).
2. Navigate to **Apps and games** &rarr; select **TypeBridge** (`9PL56S4CL4NW`).
3. Click **Start submission** (or **Update submission** for updates).
4. On the **Packages** page:
   - Drag and drop `Release_Packages/TypeBridge-1.0.1-x64.msixupload` (or `TypeBridge-1.0.1-x64.msix`).
   - Partner Center will validate the package identity, version (`1.0.1.0`), capabilities (`runFullTrust`), and architecture (`x64`).
5. On the **Properties** page:
   - Category: *Utilities & tools* &rarr; *Productivity*
   - Display mode: *Standard*
6. On the **Age ratings** page:
   - Complete the IARC questionnaire (typically rated for all ages / PEGI 3 / ESRB Everyone).
7. On the **Store listings** page:
   - Provide description, features list, release notes, and high-resolution screenshots.
8. Click **Submit to the Store**.
   - Microsoft will perform automated certification and publish the app to the Microsoft Store worldwide.

---

## 4. How Future Updates Work

When publishing a future update (e.g. `1.0.2`):

1. **Update Version**:
   - In `typebridge desktop assistant/app/core/config.py`: Set `APP_VERSION = "1.0.2"`
   - In `typebridge desktop assistant/msix/AppxManifest.xml`: Set `<Identity ... Version="1.0.2.0" ... />`
2. **Build Packages**:
   ```powershell
   cd "typebridge desktop assistant"
   python build_msix.py
   ```
3. **Submit to Partner Center**:
   - Create a new submission under `TypeBridge`.
   - Upload the new `TypeBridge-1.0.2-x64.msixupload`.
   - Add release notes for users.
   - Click **Submit to the Store**.
4. **Automatic Client Delivery**:
   - The Microsoft Store automatically distributes the update silently to all installed Windows users worldwide in the background.
   - Users who click **Check for Updates** in TypeBridge will be directed directly to the TypeBridge Microsoft Store page: `ms-windows-store://pdp/?ProductId=9PL56S4CL4NW`.

---

## 5. Migration from Legacy Inno Setup / EXE Edition

Existing users who installed TypeBridge via the traditional Inno Setup installer will not lose any data when installing the Microsoft Store edition:

- **Automatic Configuration Migration**:
  When TypeBridge launches under an MSIX container, `config.py` detects if it is running packaged via `is_packaged_msix()`.
  If the local MSIX config directory is empty, it automatically detects `%APPDATA%\TypeBridge` (the legacy storage path) and migrates:
  - `config.json` (device name, preferences, pairing status)
  - `known_devices.db` / `typebridge.db` (trusted phone pairings)
  - TLS encryption keys & certificates (`cert.pem`, `key.pem`)
- **Safety**: The legacy `%APPDATA%\TypeBridge` directory is never deleted, ensuring safe rollback if ever required.

---

## 6. Local Sideloading / Testing (Before Store Release)

To test installation of the MSIX on a local Windows machine without uploading to the Store:

1. **Install Test Certificate**:
   - Double-click `typebridge desktop assistant\msix\TypeBridge_TestCert.cer`.
   - Click **Install Certificate...** &rarr; Select **Local Machine** &rarr; Next.
   - Select **Place all certificates in the following store** &rarr; Browse &rarr; **Trusted Root Certification Authorities** &rarr; Finish.
2. **Install MSIX Package**:
   ```powershell
   Add-AppxPackage -Path "Release_Packages\TypeBridge-1.0.1-x64.msix"
   ```
3. **Launch**:
   Search for "TypeBridge" in Windows Start Menu and launch.

---

## 7. Windows App Certification Kit (WACK) Validation

To run WACK locally:
1. Open an **Administrator PowerShell prompt** (WACK requires elevation to test isolation policies).
2. Execute:
   ```powershell
   & "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "C:\Users\lokes\Music\typeanywhere\Release_Packages\TypeBridge-1.0.1-x64.msix" -reportoutputpath "C:\Users\lokes\Music\typeanywhere\wack_report.xml"
   ```
3. Review `wack_report.xml` for certification test results.
