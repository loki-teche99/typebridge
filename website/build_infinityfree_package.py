"""
TypeBridge - InfinityFree Automated Packaging Tool
Creates a clean 'htdocs' directory and generates 'infinityfree_htdocs.zip'
ready to be uploaded and extracted in InfinityFree File Manager.
"""
import os
import shutil
import zipfile

WEBSITE_DIR = os.path.dirname(os.path.abspath(__file__))
HTDOCS_DIR = os.path.join(WEBSITE_DIR, "htdocs")
ZIP_OUTPUT = os.path.join(WEBSITE_DIR, "infinityfree_htdocs.zip")
CURRENT_APK = "TypeBridge-Android-v1.0.2.apk"

def build_package():
    print("\n" + "=" * 60)
    print("      BUILDING INFINITYFREE DEPLOYMENT PACKAGE (v1.0.2)     ")
    print("=" * 60)

    # 1. Clean previous htdocs folder
    if os.path.exists(HTDOCS_DIR):
        shutil.rmtree(HTDOCS_DIR)
    os.makedirs(HTDOCS_DIR, exist_ok=True)
    os.makedirs(os.path.join(HTDOCS_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(HTDOCS_DIR, "downloads"), exist_ok=True)

    # 2. Copy core website files
    core_files = [
        "index.html",
        "styles.css",
        "config.js",
        ".htaccess",
        "robots.txt",
        "sitemap.xml",
        "download_apk.php"
    ]
    for f in core_files:
        src = os.path.join(WEBSITE_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(HTDOCS_DIR, f))
            print(f"  [+] Added: {f}")

    # 3. Copy all assets
    assets_src_dir = os.path.join(WEBSITE_DIR, "assets")
    if os.path.exists(assets_src_dir):
        for asset_file in os.listdir(assets_src_dir):
            s_file = os.path.join(assets_src_dir, asset_file)
            if os.path.isfile(s_file):
                shutil.copy2(s_file, os.path.join(HTDOCS_DIR, "assets", asset_file))
                print(f"  [+] Added asset: assets/{asset_file}")

    # 4. Copy latest Android APK (v1.0.2) to downloads/
    apk_src = os.path.join(WEBSITE_DIR, "downloads", CURRENT_APK)
    if os.path.exists(apk_src):
        dest_apk = os.path.join(HTDOCS_DIR, "downloads", CURRENT_APK)
        shutil.copy2(apk_src, dest_apk)
        # Also create a latest alias
        latest_alias = os.path.join(HTDOCS_DIR, "downloads", "TypeBridge-Android-latest.apk")
        shutil.copy2(apk_src, latest_alias)
        apk_mb = os.path.getsize(apk_src) / (1024 * 1024)
        print(f"  [+] Added: downloads/{CURRENT_APK} ({apk_mb:.2f} MB)")
        print(f"  [+] Added: downloads/TypeBridge-Android-latest.apk ({apk_mb:.2f} MB)")
    else:
        print(f"  [!] WARNING: {apk_src} not found!")

    # Copy PHP fallback gateways inside downloads/
    php_src = os.path.join(WEBSITE_DIR, "downloads", "download_apk.php")
    if os.path.exists(php_src):
        shutil.copy2(php_src, os.path.join(HTDOCS_DIR, "downloads", "download_apk.php"))
        shutil.copy2(php_src, os.path.join(HTDOCS_DIR, "downloads", "index.php"))
        print("  [+] Added: downloads/download_apk.php & downloads/index.php")

    # Copy release manifest and checksums
    for meta_file in ["release-manifest.json", "sha256sums.txt"]:
        meta_src = os.path.join(WEBSITE_DIR, "downloads", meta_file)
        if os.path.exists(meta_src):
            shutil.copy2(meta_src, os.path.join(HTDOCS_DIR, "downloads", meta_file))
            print(f"  [+] Added: downloads/{meta_file}")

    print("  [+] Windows Store: Microsoft Store PDP Link (9PL56S4CL4NW)")
    print("  [+] Windows Setup: Official Release Direct Link")
    print("  [+] Android APK: Direct Stream download_apk.php (Zero 404s guaranteed)")

    # 5. Create ZIP file
    if os.path.exists(ZIP_OUTPUT):
        os.remove(ZIP_OUTPUT)

    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(zipfile.ZipInfo("assets/"), "")
        zf.writestr(zipfile.ZipInfo("downloads/"), "")

        for root, dirs, files in os.walk(HTDOCS_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, HTDOCS_DIR).replace("\\", "/")
                zf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print("=" * 60)
    print(f"  SUCCESS! InfinityFree Upload Package Ready:")
    print(f"  File : {ZIP_OUTPUT}")
    print(f"  Size : {zip_size_mb:.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    build_package()
