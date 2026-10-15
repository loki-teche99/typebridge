<?php
// TypeBridge Android APK Direct Gateway
// Automatically redirects to the official high-speed GitHub Releases CDN
$apk_url = "https://github.com/loki-teche99/typebridge/releases/download/v1.0.2/TypeBridge-Android-v1.0.2.apk";
header("Location: " . $apk_url, true, 302);
header("Cache-Control: no-cache, must-revalidate");
exit();
