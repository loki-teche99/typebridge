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

def build_package():
    print("\n" + "=" * 60)
    print("      BUILDING INFINITYFREE DEPLOYMENT PACKAGE       ")
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

    # 3. Copy all assets (logo and realistic showcase images)
    assets_src_dir = os.path.join(WEBSITE_DIR, "assets")
    if os.path.exists(assets_src_dir):
        for asset_file in os.listdir(assets_src_dir):
            s_file = os.path.join(assets_src_dir, asset_file)
            if os.path.isfile(s_file):
                shutil.copy2(s_file, os.path.join(HTDOCS_DIR, "assets", asset_file))
                print(f"  [+] Added asset: assets/{asset_file}")

    # 4. Copy Android APK and gateway scripts to downloads/
    apk_candidates = [f for f in os.listdir(os.path.join(WEBSITE_DIR, "downloads")) if f.startswith("TypeBridge-Android-") and f.endswith(".apk")]
    for apk_file in apk_candidates:
        apk_src = os.path.join(WEBSITE_DIR, "downloads", apk_file)
        shutil.copy2(apk_src, os.path.join(HTDOCS_DIR, "downloads", apk_file))
        apk_mb = os.path.getsize(apk_src) / (1024 * 1024)
        print(f"  [+] Added: downloads/{apk_file} ({apk_mb:.2f} MB)")

    # Copy PHP fallback gateways inside downloads/
    php_src = os.path.join(WEBSITE_DIR, "download_apk.php")
    if os.path.exists(php_src):
        shutil.copy2(php_src, os.path.join(HTDOCS_DIR, "downloads", "download_apk.php"))
        shutil.copy2(php_src, os.path.join(HTDOCS_DIR, "downloads", "index.php"))
        print("  [+] Added: downloads/download_apk.php & downloads/index.php")

    # Copy release manifest and checksums if present
    for meta_file in ["release-manifest.json", "sha256sums.txt"]:
        meta_src = os.path.join(WEBSITE_DIR, "downloads", meta_file)
        if os.path.exists(meta_src):
            shutil.copy2(meta_src, os.path.join(HTDOCS_DIR, "downloads", meta_file))
            print(f"  [+] Added: downloads/{meta_file}")

    # 5. Note: Downloads route directly to high-speed verified endpoints
    print("  [+] Configured: Windows Store -> Official Microsoft Store Direct PDP Link")
    print("  [+] Configured: Windows Setup -> GitHub Official Release Direct Download")
    print("  [+] Configured: Android APK   -> GitHub Official Release Direct Download CDN")

    # 6. Create ZIP file with explicit directory entries and normalized Unix forward slashes
    if os.path.exists(ZIP_OUTPUT):
        os.remove(ZIP_OUTPUT)

    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        # Explicit directory records
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
