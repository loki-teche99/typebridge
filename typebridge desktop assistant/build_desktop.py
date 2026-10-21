"""
TypeBridge Desktop - Automated Build & Packaging Pipeline
Compiles the application into a standalone executable via PyInstaller
and packages it into an official Windows Installer (.exe) via Inno Setup.
"""
import os
import sys
import subprocess
import shutil

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg: str):
    print(f"\n======================================================\n{msg}\n======================================================")

def find_iscc() -> str | None:
    # 1. In PATH
    iscc = shutil.which("iscc")
    if iscc:
        return iscc
    # 2. LocalAppData Programs
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    p1 = os.path.join(local_app_data, "Programs", "Inno Setup 6", "iscc.exe")
    if os.path.exists(p1):
        return p1
    # 3. Program Files (x86)
    p2 = r"C:\Program Files (x86)\Inno Setup 6\iscc.exe"
    if os.path.exists(p2):
        return p2
    # 4. Program Files
    p3 = r"C:\Program Files\Inno Setup 6\iscc.exe"
    if os.path.exists(p3):
        return p3
    return None

def main():
    os.chdir(ROOT_DIR)

    # Step 1: Ensure icons exist
    log("[1/3] Generating Application Icons...")
    icon_script = os.path.join(ROOT_DIR, "assets", "icon_generator.py")
    subprocess.run([sys.executable, icon_script], check=True)

    # Step 2: PyInstaller Build
    log("[2/3] Compiling Standalone Executable via PyInstaller...")
    spec_file = os.path.join(ROOT_DIR, "TypeBridge.spec")
    subprocess.run(["pyinstaller", "--clean", spec_file, "-y"], check=True)

    exe_path = os.path.join(ROOT_DIR, "dist", "TypeBridge", "TypeBridge.exe")
    if not os.path.exists(exe_path):
        raise RuntimeError(f"Build failed: {exe_path} not found!")

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"[OK] Standalone binary ready: {exe_path} ({size_mb:.2f} MB)")

    # Step 3: Inno Setup Packaging
    log("[3/3] Building Windows Setup Installer (.exe)...")
    iscc_path = find_iscc()
    if not iscc_path:
        print("[WARNING] Inno Setup compiler (iscc.exe) not found in standard paths.")
        print(f"Standalone executable is ready in {exe_path}")
        return

    iss_file = os.path.join(ROOT_DIR, "installer.iss")
    subprocess.run([iscc_path, iss_file], check=True)

    setup_filename = "TypeBridgeSetup-v1.0.2.exe"
    setup_exe = os.path.join(ROOT_DIR, "installer_output", setup_filename)
    if os.path.exists(setup_exe):
        setup_size_mb = os.path.getsize(setup_exe) / (1024 * 1024)
        log(f"[SUCCESS] Windows Installer Ready:\n{setup_exe}\nSize: {setup_size_mb:.2f} MB")

        # Copy to Release_Packages and website/downloads
        parent_dir = os.path.dirname(ROOT_DIR)
        rel_pkg = os.path.join(parent_dir, "Release_Packages", setup_filename)
        web_pkg = os.path.join(parent_dir, "website", "downloads", setup_filename)
        os.makedirs(os.path.dirname(rel_pkg), exist_ok=True)
        os.makedirs(os.path.dirname(web_pkg), exist_ok=True)
        shutil.copy2(setup_exe, rel_pkg)
        shutil.copy2(setup_exe, web_pkg)
        print(f"[OK] Copied installer to: {rel_pkg}")
        print(f"[OK] Copied installer to: {web_pkg}")
    else:
        print(f"[WARNING] Installer output file not found: {setup_exe}")

if __name__ == "__main__":
    main()
