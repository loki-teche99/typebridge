"""
Update Website SEO, Microsoft Store Primary Download, and Android v1.0.1 Links
"""
import os
import re

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

def update_website():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update Title and SEO Meta
    old_title_meta = """  <!-- Primary High-Intent Brand & SEO Title -->
  <title>TypeBridge™ — #1 Best Auto Typer Software for PC &amp; Mobile | Hardware Keystroke Streamer</title>
  
  <!-- High CTR & High-Density Entity SEO Description -->
  <meta name="description" content="TypeBridge is the world's #1 auto typing software for Windows PC and Android. Emulates genuine OS hardware keystrokes (Win32 SendInput), bypasses paste restrictions, eliminates clipboard detection, and streams code from phone to PC with 100% exact indentation. 100% Free, undetectable, and offline-capable.">
  
  <!-- Keyword Tags for Global Search Engines -->
  <meta name="keywords" content="best auto typer, auto typing software, best auto typing software, auto typer for pc, phone to pc auto typer, bypass paste restrictions, undetectable auto typer, code auto typer, leetcode autotyper, hackerearth autotyper, hardware keystroke simulator, sendinput auto typer, auto typing tool for coding, free auto typer windows 11, android auto typer, auto clicker and typer, bluetooth auto typer, wifi keystroke streamer, typebridge, typebridge auto typer">"""

    new_title_meta = """  <!-- Primary High-Intent Brand & SEO Title -->
  <title>Typebridge™ — Official Website | #1 Auto Typer for PC &amp; Mobile | TypeBridge</title>
  
  <!-- High CTR & High-Density Entity SEO Description -->
  <meta name="description" content="Official website of Typebridge (TypeBridge) — the world's #1 hardware-level auto typer software for Windows PC and Android. Download Typebridge on Microsoft Store or direct APK. Emulates genuine Win32 SendInput keystrokes, bypasses paste blockers, zero clipboard detection, and streams code with 100% exact indentation. 100% Free, secure, and offline.">
  
  <!-- Keyword Tags for Global Search Engines -->
  <meta name="keywords" content="typebridge, Typebridge, TypeBridge, Type Bridge, Typebridge app, Typebridge download, Typebridge official website, Typebridge for pc, Typebridge android, Typebridge apk, Typebridge microsoft store, Typebridge auto typer, MadeByLokesh Typebridge, 9PL56S4CL4NW, best auto typer, auto typing software, best auto typing software, auto typer for pc, phone to pc auto typer, bypass paste restrictions, undetectable auto typer, code auto typer, leetcode autotyper, hackerearth autotyper, hardware keystroke simulator, sendinput auto typer, auto typing tool for coding, free auto typer windows 11, android auto typer, auto clicker and typer, bluetooth auto typer, wifi keystroke streamer, typing assistant, mobile to pc keyboard">
  <meta name="google-site-verification" content="GSC_VERIFICATION_PLACEHOLDER">"""

    if old_title_meta in content:
        content = content.replace(old_title_meta, new_title_meta, 1)
        print("[+] Updated Title and Meta tags")
    else:
        print("[!] Warning: old_title_meta not found exactly")

    # 2. Update OG and Twitter metadata
    content = content.replace(
        '<meta property="og:title" content="TypeBridge™ — #1 Best Auto Typer &amp; Keystroke Streamer for PC &amp; Android">',
        '<meta property="og:title" content="Typebridge™ — Official Website | #1 Auto Typer for Windows &amp; Android">'
    )
    content = content.replace(
        '<meta property="og:site_name" content="TypeBridge">',
        '<meta property="og:site_name" content="Typebridge">'
    )
    content = content.replace(
        '<meta name="twitter:title" content="TypeBridge™ — #1 Best Auto Typer &amp; Hardware Keystroke Streamer">',
        '<meta name="twitter:title" content="Typebridge™ — Official Website | #1 Auto Typer for PC &amp; Mobile">'
    )
    print("[+] Updated OpenGraph and Twitter tags")

    # 3. Update Schema.org
    old_schema_ver = '"softwareVersion": "1.0.0",'
    new_schema_ver = """"softwareVersion": "1.0.1",
        "installUrl": "https://apps.microsoft.com/detail/9PL56S4CL4NW?hl=en-us&gl=IN&ocid=pdpshare",
        "sameAs": [
          "https://apps.microsoft.com/detail/9PL56S4CL4NW",
          "https://github.com/loki-teche99/typebridge"
        ],"""
    if old_schema_ver in content:
        content = content.replace(old_schema_ver, new_schema_ver, 1)
        print("[+] Updated Schema.org softwareVersion and Store installUrl")

    # 4. Update Download Section (Dual Cards Grid)
    old_downloads_box = """            <div class="card-action-box">
              <!-- PRIMARY DIRECT DOWNLOAD BUTTON -->
              <a id="btnDownloadWindows" href="https://github.com/loki-teche99/typebridge/releases/download/v1.0.0/TypeBridgeSetup-v1.0.0.exe" download="TypeBridgeSetup-v1.0.0.exe" class="btn btn-download-primary">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                <span>⚡ 1-Click Download (.exe)</span>
              </a>
              
              <!-- ALTERNATIVE SHARE LINKS & MIRRORS -->
              <div class="download-mirror-row">
                <span class="direct-link-hint">🚀 Direct high-speed download active</span>
                <div class="mirror-links-group">
                  <span>Mirrors:</span>
                  <a id="lnkWindowsMirror" href="https://github.com/loki-teche99/typebridge/releases/latest" target="_blank" rel="noopener" class="direct-link-btn" title="GitHub Official Releases">GitHub Releases &nearr;</a>
                  <span class="mirror-sep">&bull;</span>
                  <a id="lnkGoogleDrive" href="https://drive.google.com/file/d/1MS4w9QSdMCanvwc0j7m4Q3BCf1WsxjFa/view?usp=sharing" target="_blank" rel="noopener" class="direct-link-btn" title="Open Google Drive">Google Drive &nearr;</a>
                </div>
              </div>
            </div>"""

    new_downloads_box = """            <div class="card-action-box">
              <!-- PRIMARY MICROSOFT STORE BUTTON -->
              <a id="btnDownloadWindowsStore" href="https://apps.microsoft.com/detail/9PL56S4CL4NW?hl=en-us&gl=IN&ocid=pdpshare" target="_blank" rel="noopener" class="btn btn-ms-store" title="Get Typebridge from Microsoft Store">
                <svg class="ms-logo-svg" width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path fill="#F25022" d="M1 1h10v10H1z"/>
                  <path fill="#7FBA00" d="M13 1h10v10H13z"/>
                  <path fill="#00A4EF" d="M1 13h10v10H1z"/>
                  <path fill="#FFB900" d="M13 13h10v10H13z"/>
                </svg>
                <span>Get from Microsoft Store</span>
              </a>

              <!-- ALTERNATIVE STANDALONE INSTALLER BUTTON -->
              <a id="btnDownloadWindowsExe" href="https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridgeSetup-v1.0.1.exe" class="btn btn-download-secondary" title="Download standalone Windows Setup installer (.exe)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                <span>Download Standalone Setup (.exe) — v1.0.1</span>
              </a>
              
              <!-- ALTERNATIVE MIRRORS -->
              <div class="download-mirror-row">
                <span class="direct-link-hint">🛡️ Certified Store &amp; Standalone options active</span>
                <div class="mirror-links-group">
                  <span>Mirrors:</span>
                  <a id="lnkWindowsMirror" href="https://github.com/loki-teche99/typebridge/releases/latest" target="_blank" rel="noopener" class="direct-link-btn" title="GitHub Official Releases">GitHub Releases &nearr;</a>
                  <span class="mirror-sep">&bull;</span>
                  <a id="lnkGoogleDrive" href="https://drive.google.com/file/d/1MS4w9QSdMCanvwc0j7m4Q3BCf1WsxjFa/view?usp=sharing" target="_blank" rel="noopener" class="direct-link-btn" title="Open Google Drive">Google Drive &nearr;</a>
                </div>
              </div>
            </div>"""

    if old_downloads_box in content:
        content = content.replace(old_downloads_box, new_downloads_box, 1)
        print("[+] Updated Windows Download Card with Microsoft Store Primary")
    else:
        print("[!] Warning: old_downloads_box not found exactly")

    # Update Windows Card pills and category
    content = content.replace(
        '<div class="card-category">WINDOWS DESKTOP ASSISTANT</div>',
        '<div class="card-category">MICROSOFT STORE CERTIFIED • WINDOWS 10 &amp; 11</div>'
    )
    content = content.replace(
        '<span class="pill pill-cyan">⚡ 1-Click Direct Download</span>\n              <span class="pill pill-indigo">v1.0.0</span>\n              <span class="pill pill-purple">34.9 MB</span>',
        '<span class="pill pill-cyan">⚡ Microsoft Store (Primary)</span>\n              <span class="pill pill-indigo">v1.0.1</span>\n              <span class="pill pill-purple">Store ID: 9PL56S4CL4NW</span>'
    )

    # 5. Update Android Card
    content = content.replace(
        '<span class="pill pill-emerald">✓ Anti-Sleep WifiLock</span>\n              <span class="pill pill-indigo">v1.0.0</span>\n              <span class="pill pill-amber">9.3 MB</span>\n              <span class="pill">Android 8.0 to 14+</span>',
        '<span class="pill pill-emerald">✓ Portrait QR Scanner Fix</span>\n              <span class="pill pill-indigo">v1.0.1</span>\n              <span class="pill pill-amber">9.42 MB</span>\n              <span class="pill">Android 8.0 to 15+</span>'
    )
    content = content.replace(
        'href="downloads/TypeBridge-Android-v1.0.0.apk" download="TypeBridge-Android-v1.0.0.apk" class="btn btn-download-android">\n                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>\n                <span>📲 1-Click Download APK (.apk)</span>',
        'href="downloads/TypeBridge-Android-v1.0.1.apk" download="TypeBridge-Android-v1.0.1.apk" class="btn btn-download-android">\n                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>\n                <span>📲 1-Click Download APK (v1.0.1)</span>'
    )

    # Add mirror row inside Android Card right before closing of card-action-box
    old_android_card_close = """                <div class="qr-micro-text">
                  <strong>📱 Scan on Phone to Install APK</strong>
                  <span>Point your phone camera to download APK directly without USB cables.</span>
                </div>
              </div>
            </div>"""

    new_android_card_close = """                <div class="qr-micro-text">
                  <strong>📱 Scan on Phone to Install APK</strong>
                  <span>Point your phone camera to download APK directly without USB cables.</span>
                </div>
              </div>

              <!-- ANDROID ALTERNATIVE MIRRORS -->
              <div class="download-mirror-row">
                <span class="direct-link-hint" style="color: var(--accent-emerald);">🛡️ Signed Release APK • Remote Updatable • Floating Screen Button Included</span>
                <div class="mirror-links-group">
                  <span>Direct:</span>
                  <a id="lnkAndroidDirect" href="downloads/TypeBridge-Android-v1.0.2.apk" class="direct-link-btn" title="Download APK directly from server">Direct File Link &nearr;</a>
                  <span class="mirror-sep">&bull;</span>
                  <a id="lnkAndroidGitHub" href="https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridge-Android-v1.0.2.apk" target="_blank" rel="noopener" class="direct-link-btn" title="Download latest v1.0.2 APK with Screen Overlay directly from GitHub Releases">GitHub Direct APK (v1.0.2) &nearr;</a>
                </div>
              </div>
            </div>"""

    if old_android_card_close in content:
        content = content.replace(old_android_card_close, new_android_card_close, 1)
        print("[+] Added Android alternative mirror row")
    else:
        print("[!] Warning: old_android_card_close not found exactly")

    # 6. Update JavaScript initPage()
    old_init_page = """    // Page initialization
    function initPage() {
      renderSimulator('typebridge');

      const cfg = typeof TYPEBRIDGE_CONFIG !== 'undefined' ? TYPEBRIDGE_CONFIG : {
        windowsDirectUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.0/TypeBridgeSetup-v1.0.0.exe",
        windowsMirrorUrl: "https://github.com/loki-teche99/typebridge/releases/latest",
        windowsGoogleDriveUrl: "https://drive.google.com/file/d/1MS4w9QSdMCanvwc0j7m4Q3BCf1WsxjFa/view?usp=sharing",
        androidApkUrl: "downloads/TypeBridge-Android-v1.0.0.apk"
      };

      const btnWin = document.getElementById('btnDownloadWindows');
      const lnkMirror = document.getElementById('lnkWindowsMirror');
      const lnkGDrive = document.getElementById('lnkGoogleDrive');
      const btnAnd = document.getElementById('btnDownloadAndroid');

      if (btnWin && cfg.windowsDirectUrl) btnWin.href = cfg.windowsDirectUrl;
      if (lnkMirror && cfg.windowsMirrorUrl) lnkMirror.href = cfg.windowsMirrorUrl;
      if (lnkGDrive && cfg.windowsGoogleDriveUrl) lnkGDrive.href = cfg.windowsGoogleDriveUrl;
      if (btnAnd && cfg.androidApkUrl) btnAnd.href = cfg.androidApkUrl;

      // Render / Update QR Code with 100% Reliability
      const qrTarget = document.getElementById('qrCanvas');
      if (qrTarget) {
        let apkUrl = cfg.androidApkUrl || "downloads/TypeBridge-Android-v1.0.0.apk";
        if (!apkUrl.startsWith('http://') && !apkUrl.startsWith('https://')) {
          if (window.location.protocol.startsWith('http') && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            apkUrl = window.location.origin + window.location.pathname.replace(/index\\.html$/, '').replace(/\\/$/, '') + '/' + apkUrl;
          } else {
            apkUrl = "https://typebridge.42web.io/" + apkUrl.replace(/^\\//, '');
          }
        }

        // Enable click-to-download on QR holder for desktop convenience
        qrTarget.style.cursor = 'pointer';
        qrTarget.onclick = () => { window.location.href = cfg.androidApkUrl; };

        // Dynamic re-render only if URL is non-standard and QRCode constructor is present
        const defaultProdUrl = "https://typebridge.42web.io/downloads/TypeBridge-Android-v1.0.0.apk";
        if (apkUrl !== defaultProdUrl && typeof QRCode === 'function') {
          try {
            qrTarget.innerHTML = '';
            new QRCode(qrTarget, {
              text: apkUrl,
              width: 94,
              height: 94,
              colorDark: '#06080f',
              colorLight: '#ffffff',
              correctLevel: typeof QRCode.CorrectLevel !== 'undefined' ? QRCode.CorrectLevel.M : 0
            });
          } catch (e) {
            console.warn('Dynamic QR generation skipped, maintaining high-res image:', e);
          }
        }
      }
    }"""

    new_init_page = """    // Page initialization
    function initPage() {
      renderSimulator('typebridge');

      const cfg = typeof TYPEBRIDGE_CONFIG !== 'undefined' ? TYPEBRIDGE_CONFIG : {
        windowsStoreUrl: "https://apps.microsoft.com/detail/9PL56S4CL4NW?hl=en-us&gl=IN&ocid=pdpshare",
        windowsDirectUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.1/TypeBridgeSetup-v1.0.1.exe",
        windowsMirrorUrl: "https://github.com/loki-teche99/typebridge/releases/latest",
        androidApkUrl: "download_apk.php",
        androidLocalApkUrl: "downloads/TypeBridge-Android-v1.0.2.apk",
        androidGitHubApkUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridge-Android-v1.0.2.apk"
      };

      const btnWinStore = document.getElementById('btnDownloadWindowsStore');
      const btnWinExe = document.getElementById('btnDownloadWindowsExe');
      const lnkMirror = document.getElementById('lnkWindowsMirror');
      const lnkGDrive = document.getElementById('lnkGoogleDrive');
      const btnAnd = document.getElementById('btnDownloadAndroid');
      const lnkAndGh = document.getElementById('lnkAndroidGitHub');
      const lnkAndDir = document.getElementById('lnkAndroidDirect');

      if (btnWinStore && cfg.windowsStoreUrl) btnWinStore.href = cfg.windowsStoreUrl;
      if (btnWinExe && cfg.windowsDirectUrl) btnWinExe.href = cfg.windowsDirectUrl;
      if (lnkMirror && cfg.windowsMirrorUrl) lnkMirror.href = cfg.windowsMirrorUrl;
      if (lnkGDrive && cfg.windowsGoogleDriveUrl) lnkGDrive.href = cfg.windowsGoogleDriveUrl;
      if (btnAnd && cfg.androidApkUrl) btnAnd.href = cfg.androidApkUrl;
      if (lnkAndGh && cfg.androidGitHubApkUrl) lnkAndGh.href = cfg.androidGitHubApkUrl;
      if (lnkAndDir && cfg.androidLocalApkUrl) lnkAndDir.href = cfg.androidLocalApkUrl;

      // Render / Update QR Code with 100% Reliability
      const qrTarget = document.getElementById('qrCanvas');
      if (qrTarget) {
        const rawApk = cfg.androidApkUrl || "download_apk.php";
        const fullApkUrl = rawApk.startsWith('http') ? rawApk : (window.location.origin.includes('http') ? window.location.origin + '/' + rawApk : "https://typebridge.42web.io/download_apk.php");

        // Enable click-to-download on QR holder for desktop convenience
        qrTarget.style.cursor = 'pointer';
        qrTarget.onclick = () => { window.location.href = rawApk; };

        // Dynamic re-render only if URL is non-standard and QRCode constructor is present
        const defaultProdUrl = "https://typebridge.42web.io/downloads/TypeBridge-Android-v1.0.2.apk";
        if (apkUrl !== defaultProdUrl && typeof QRCode === 'function') {
          try {
            qrTarget.innerHTML = '';
            new QRCode(qrTarget, {
              text: apkUrl,
              width: 94,
              height: 94,
              colorDark: '#06080f',
              colorLight: '#ffffff',
              correctLevel: typeof QRCode.CorrectLevel !== 'undefined' ? QRCode.CorrectLevel.M : 0
            });
          } catch (e) {
            console.warn('Dynamic QR generation skipped, maintaining high-res image:', e);
          }
        }
      }
    }"""

    if old_init_page in content:
        content = content.replace(old_init_page, new_init_page, 1)
        print("[+] Updated initPage() script")
    else:
        print("[!] Warning: old_init_page not found exactly")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("[SUCCESS] index.html updated successfully!")

if __name__ == "__main__":
    update_website()
