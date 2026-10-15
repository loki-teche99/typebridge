"""
Fix Android APK Download URL in index.html
Replaces local downloads/ link with high-speed direct GitHub Releases URL
"""
import os

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

def fix_download():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. Update button
    old_btn = '<a id="btnDownloadAndroid" href="downloads/TypeBridge-Android-v1.0.1.apk" download="TypeBridge-Android-v1.0.1.apk" class="btn btn-download-android">'
    new_btn = '<a id="btnDownloadAndroid" href="https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridge-Android-v1.0.1.apk" class="btn btn-download-android" title="Download TypeBridge Android APK">'
    if old_btn in text:
        text = text.replace(old_btn, new_btn, 1)
        print("[+] Fixed btnDownloadAndroid href")
    else:
        print("[!] Warning: old_btn not found")

    # 2. Update initPage fallback
    old_cfg = 'androidApkUrl: "downloads/TypeBridge-Android-v1.0.1.apk",'
    new_cfg = 'androidApkUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridge-Android-v1.0.1.apk",'
    if old_cfg in text:
        text = text.replace(old_cfg, new_cfg, 1)
        print("[+] Fixed androidApkUrl in initPage")
    else:
        print("[!] Warning: old_cfg not found")

    # 3. Update QR code logic in initPage
    old_qr = """        let apkUrl = cfg.androidApkUrl || "downloads/TypeBridge-Android-v1.0.1.apk";
        if (!apkUrl.startsWith('http://') && !apkUrl.startsWith('https://')) {
          if (window.location.protocol.startsWith('http') && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            apkUrl = window.location.origin + window.location.pathname.replace(/index\\.html$/, '').replace(/\\/$/, '') + '/' + apkUrl;
          } else {
            apkUrl = "https://typebridge.42web.io/" + apkUrl.replace(/^\\//, '');
          }
        }"""
    new_qr = '        let apkUrl = cfg.androidApkUrl || "https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridge-Android-v1.0.1.apk";'
    if old_qr in text:
        text = text.replace(old_qr, new_qr, 1)
        print("[+] Fixed QR code generation url")
    else:
        print("[!] Warning: old_qr not found")

    # 4. Update defaultProdUrl for QR constructor
    old_default = 'const defaultProdUrl = "https://typebridge.42web.io/downloads/TypeBridge-Android-v1.0.1.apk";'
    new_default = 'const defaultProdUrl = "https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridge-Android-v1.0.1.apk";'
    if old_default in text:
        text = text.replace(old_default, new_default, 1)
        print("[+] Fixed defaultProdUrl")
    else:
        print("[!] Warning: old_default not found")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print("[SUCCESS] All Android download links updated to direct GitHub Releases CDN!")

if __name__ == "__main__":
    fix_download()
