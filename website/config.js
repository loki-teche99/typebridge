/**
 * TypeBridge Website Configuration v1.0.2
 * ==============================================================================
 * Official Download Endpoints & Metadata
 * - Windows Store: Official Microsoft Store Product URL
 * - Windows Standalone: GitHub Releases Direct (.exe)
 * - Android APK: High-speed direct release CDN (100% guaranteed delivery)
 * ==============================================================================
 */

const TYPEBRIDGE_CONFIG = {
  // 1. Primary Windows Download: Microsoft Store Official Product Page
  windowsStoreUrl: "https://apps.microsoft.com/detail/9PL56S4CL4NW?hl=en-us&gl=IN&ocid=pdpshare",
  windowsStoreProtocolUrl: "ms-windows-store://pdp/?ProductId=9PL56S4CL4NW",
  microsoftStoreId: "9PL56S4CL4NW",

  // 2. Secondary Windows Download: Direct Standalone Installer (.exe)
  windowsDirectUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridgeSetup-v1.0.2.exe",

  // 3. Official GitHub Releases Mirror
  windowsMirrorUrl: "https://github.com/loki-teche99/typebridge/releases/latest",

  // 4. Google Drive Mirror
  windowsGoogleDriveUrl: "https://drive.google.com/file/d/1MS4w9QSdMCanvwc0j7m4Q3BCf1WsxjFa/view?usp=sharing",

  // 5. Official Website Canonical URL
  websiteUrl: "https://typebridge.42web.io/",

  // 6. Android APK Direct Download URL (Official High-Speed GitHub Releases CDN — 100% Reliable, Instant 1-Click)
  androidApkUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridge-Android-v1.0.2.apk",
  androidLocalApkUrl: "downloads/TypeBridge-Android-v1.0.2.apk",
  androidGitHubApkUrl: "https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridge-Android-v1.0.2.apk",

  // 7. Version Metadata
  version: "v1.0.2",
  windowsSize: "36.86 MB",
  androidSize: "9.44 MB",
  bluetooth: true,
  connectionModes: "WiFi + Bluetooth SPP"
};
