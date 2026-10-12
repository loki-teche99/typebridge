"""
TypeBridge - Automatic Release Manifest & Checksum Generator
Usage:
    python generate_release_manifest.py v1.0.2
"""
import sys
import os
import json
import hashlib
import re

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest(), os.path.getsize(path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_release_manifest.py <tag> (e.g. v1.0.2)")
        sys.exit(1)

    tag = sys.argv[1].strip()
    if not tag.startswith("v"):
        tag = f"v{tag}"
    version = tag.lstrip("v")

    root = os.path.dirname(os.path.abspath(__file__))
    pkg_dir = os.path.join(root, "Release_Packages", tag)
    os.makedirs(pkg_dir, exist_ok=True)

    apk_name = f"TypeBridge-Android-{tag}.apk"
    exe_name = f"TypeBridgeSetup-{tag}.exe"

    apk_path = os.path.join(pkg_dir, apk_name)
    exe_path = os.path.join(pkg_dir, exe_name)

    # Check if files exist in pkg_dir, otherwise check source build locations
    if not os.path.exists(apk_path):
        src_apk = os.path.join(root, "typebridge android", "app", "build", "outputs", "apk", "release", "app-release.apk")
        if os.path.exists(src_apk):
            import shutil
            shutil.copy2(src_apk, apk_path)
            print(f"[OK] Copied Android APK -> {apk_path}")

    if not os.path.exists(exe_path):
        src_exe = os.path.join(root, "typebridge desktop assistant", "installer_output", exe_name)
        if os.path.exists(src_exe):
            import shutil
            shutil.copy2(src_exe, exe_path)
            print(f"[OK] Copied Windows EXE -> {exe_path}")

    if not os.path.exists(apk_path) or not os.path.exists(exe_path):
        print(f"[ERROR] Both {apk_name} and {exe_name} must exist in {pkg_dir} to generate checksums.")
        sys.exit(1)

    apk_sha, apk_size = compute_sha256(apk_path)
    exe_sha, exe_size = compute_sha256(exe_path)

    # 1. Generate sha256sums.txt
    sha_file = os.path.join(pkg_dir, "sha256sums.txt")
    with open(sha_file, "w", encoding="utf-8") as f:
        f.write(f"{apk_sha}  {apk_name}\n")
        f.write(f"{exe_sha}  {exe_name}\n")
    print(f"[SUCCESS] Generated: {sha_file}")

    # Extract versionCode from build.gradle.kts if possible
    gradle_file = os.path.join(root, "typebridge android", "app", "build.gradle.kts")
    version_code = 2
    if os.path.exists(gradle_file):
        try:
            with open(gradle_file, "r", encoding="utf-8") as gf:
                m = re.search(r'versionCode\s*=\s*(\d+)', gf.read())
                if m:
                    version_code = int(m.group(1))
        except Exception:
            pass

    # 2. Generate release-manifest.json
    manifest = {
        "schemaVersion": 1,
        "version": version,
        "channel": "stable",
        "minimumSupportedVersion": "1.0.0",
        "android": {
            "versionCode": version_code,
            "assets": [
                {
                    "name": apk_name,
                    "url": f"https://github.com/loki-teche99/typebridge/releases/download/{tag}/{apk_name}",
                    "size": apk_size,
                    "sha256": apk_sha
                }
            ]
        },
        "windows": {
            "version": version,
            "assets": [
                {
                    "name": exe_name,
                    "url": f"https://github.com/loki-teche99/typebridge/releases/download/{tag}/{exe_name}",
                    "size": exe_size,
                    "sha256": exe_sha
                }
            ]
        }
    }

    manifest_file = os.path.join(pkg_dir, "release-manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[SUCCESS] Generated: {manifest_file}")

    print("\nSummary of Generated Assets:")
    print(f"  - {apk_name} (Size: {apk_size} bytes | SHA256: {apk_sha})")
    print(f"  - {exe_name} (Size: {exe_size} bytes | SHA256: {exe_sha})")
    print(f"\nAll 4 files in '{pkg_dir}' are ready to upload to GitHub Releases under tag '{tag}'!")

if __name__ == "__main__":
    main()
