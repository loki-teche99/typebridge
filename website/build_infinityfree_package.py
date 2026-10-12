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
    core_files = ["index.html", "styles.css", "config.js", ".htaccess", "robots.txt", "sitemap.xml"]
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

    # 4. Copy Android APK (under 10MB for direct InfinityFree hosting)
    apk_candidates = [f for f in os.listdir(os.path.join(WEBSITE_DIR, "downloads")) if f.startswith("TypeBridge-Android-") and f.endswith(".apk")]
    apk_file = "TypeBridge-Android-v1.0.1.apk" if "TypeBridge-Android-v1.0.1.apk" in apk_candidates else (apk_candidates[0] if apk_candidates else None)
    if apk_file:
        apk_src = os.path.join(WEBSITE_DIR, "downloads", apk_file)
        shutil.copy2(apk_src, os.path.join(HTDOCS_DIR, "downloads", apk_file))
        apk_mb = os.path.getsize(apk_src) / (1024 * 1024)
        print(f"  [+] Added: downloads/{apk_file} ({apk_mb:.2f} MB)")

    # 5. Note: Windows Setup is directly downloaded via GitHub Official Release direct link:
    # https://github.com/loki-teche99/typebridge/releases/download/v1.0.0/TypeBridgeSetup-v1.0.0.exe
    print("  [+] Configured: Windows Setup link -> GitHub Official Release Direct Download")

    # 6. Create ZIP file
    if os.path.exists(ZIP_OUTPUT):
        os.remove(ZIP_OUTPUT)

    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(HTDOCS_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, HTDOCS_DIR)
                zf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print("=" * 60)
    print(f"  SUCCESS! InfinityFree Upload Package Ready:")
    print(f"  File : {ZIP_OUTPUT}")
    print(f"  Size : {zip_size_mb:.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    build_package()
