"""
TypeBridge Desktop - Microsoft Store MSIX Packaging Pipeline
Builds the PyInstaller distribution, structures the MSIX layout, validates identity locking,
and packages it using Windows SDK makeappx.exe.
"""
import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
SDK_BIN_PATHS = [
    Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"),
    Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64"),
    Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64"),
    Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64"),
]

def log(msg: str):
    print(f"\n======================================================\n{msg}\n======================================================")

def find_sdk_tool(tool_name: str) -> Path:
    # 1. In PATH
    found = shutil.which(tool_name)
    if found:
        return Path(found)

    # 2. In known Windows SDK paths
    for sdk_path in SDK_BIN_PATHS:
        candidate = sdk_path / tool_name
        if candidate.exists():
            return candidate

    # 3. Search Windows Kits directory recursively
    base_kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if base_kits.exists():
        matches = list(base_kits.glob(f"**/{tool_name}"))
        for m in matches:
            if "x64" in str(m):
                return m
        if matches:
            return matches[0]

    raise FileNotFoundError(f"Could not find Windows SDK tool '{tool_name}'! Ensure Windows SDK is installed.")

def main():
    os.chdir(ROOT_DIR)

    log("[1/5] Validating MSIX Identity & Generating Visual Assets...")
    manifest_src = ROOT_DIR / "msix" / "AppxManifest.xml"
    if not manifest_src.exists():
        raise FileNotFoundError(f"Missing {manifest_src}")

    # Run validation
    subprocess.run([sys.executable, str(ROOT_DIR / "validate_msix_identity.py"), str(manifest_src)], check=True)

    # Generate assets
    subprocess.run([sys.executable, str(ROOT_DIR / "msix" / "generate_msix_assets.py")], check=True)

    log("[2/5] Compiling Desktop Application via PyInstaller...")
    spec_file = ROOT_DIR / "TypeBridge.spec"
    subprocess.run(["pyinstaller", "--clean", str(spec_file), "-y"], check=True)

    dist_app_dir = ROOT_DIR / "dist" / "TypeBridge"
    exe_file = dist_app_dir / "TypeBridge.exe"
    if not exe_file.exists():
        raise RuntimeError(f"PyInstaller build failed: {exe_file} does not exist.")

    log("[3/5] Assembling MSIX Layout Directory...")
    layout_dir = ROOT_DIR / "build" / "msix_layout"
    if layout_dir.exists():
        shutil.rmtree(layout_dir)
    layout_dir.mkdir(parents=True, exist_ok=True)

    # Copy PyInstaller files into layout root
    print(f"[*] Copying runtime files from {dist_app_dir} to {layout_dir}...")
    for item in dist_app_dir.iterdir():
        dest = layout_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Copy AppxManifest.xml
    shutil.copy2(manifest_src, layout_dir / "AppxManifest.xml")
    print(f"[*] Copied AppxManifest.xml to layout root.")

    # Copy Assets directory
    assets_src = ROOT_DIR / "msix" / "Assets"
    assets_dest = layout_dir / "Assets"
    if assets_dest.exists():
        shutil.rmtree(assets_dest)
    shutil.copytree(assets_src, assets_dest)
    print(f"[*] Copied visual assets to layout Assets/.")

    log("[4/5] Packaging MSIX using Windows SDK makeappx.exe...")
    makeappx = find_sdk_tool("makeappx.exe")
    print(f"[*] Using makeappx: {makeappx}")

    output_dir = ROOT_DIR / "msix_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    msix_package = output_dir / "TypeBridge-1.0.1-x64.msix"
    if msix_package.exists():
        msix_package.unlink()

    cmd = [
        str(makeappx),
        "pack",
        "/d", str(layout_dir),
        "/p", str(msix_package),
        "/o"  # Overwrite
    ]
    subprocess.run(cmd, check=True)

    msix_size_mb = msix_package.stat().st_size / (1024 * 1024)
    print(f"[OK] Generated MSIX package: {msix_package} ({msix_size_mb:.2f} MB)")

    log("[5/5] Creating Microsoft Store Upload Bundle (.msixupload)...")
    msixupload_package = output_dir / "TypeBridge-1.0.1-x64.msixupload"
    if msixupload_package.exists():
        msixupload_package.unlink()

    with zipfile.ZipFile(msixupload_package, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(msix_package, arcname=msix_package.name)

    upload_size_mb = msixupload_package.stat().st_size / (1024 * 1024)
    print(f"[OK] Generated Store Upload artifact: {msixupload_package} ({upload_size_mb:.2f} MB)")

    # Copy to Release_Packages directory
    rel_packages_dir = ROOT_DIR.parent / "Release_Packages"
    rel_packages_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(msix_package, rel_packages_dir / msix_package.name)
    shutil.copy2(msixupload_package, rel_packages_dir / msixupload_package.name)

    log(f"[SUCCESS] MSIX PACKAGING COMPLETE!\n"
        f"1. Store Submission Package: {msix_package}\n"
        f"2. Store Upload Bundle:     {msixupload_package}\n"
        f"3. Copied to:               {rel_packages_dir}")

if __name__ == "__main__":
    main()
