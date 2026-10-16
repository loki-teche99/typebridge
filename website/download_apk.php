<?php
// ==============================================================================
// TypeBridge Android APK Direct Gateway (v1.0.2)
// High-Speed Direct Stream & Download Handler
// ==============================================================================

// 1. Locate physical APK file
$local_file = __DIR__ . '/downloads/TypeBridge-Android-v1.0.2.apk';
if (!file_exists($local_file)) {
    $local_file = __DIR__ . '/TypeBridge-Android-v1.0.2.apk';
}

if (file_exists($local_file) && is_readable($local_file)) {
    // Clean any prior output buffers
    while (ob_get_level()) {
        ob_end_clean();
    }

    // Set binary transfer headers
    header('Content-Description: File Transfer');
    header('Content-Type: application/vnd.android.package-archive');
    header('Content-Disposition: attachment; filename="TypeBridge-Android-v1.0.2.apk"');
    header('Content-Transfer-Encoding: binary');
    header('Expires: 0');
    header('Cache-Control: must-revalidate, post-check=0, pre-check=0');
    header('Pragma: public');
    header('Content-Length: ' . filesize($local_file));

    // Stream file in 64KB chunks to optimize server memory
    $chunk_size = 1024 * 64;
    $handle = fopen($local_file, 'rb');
    if ($handle !== false) {
        while (!feof($handle)) {
            echo fread($handle, $chunk_size);
            flush();
        }
        fclose($handle);
        exit;
    }
}

// 2. Fallback relative redirect if direct stream fails
if (file_exists(__DIR__ . '/downloads/TypeBridge-Android-v1.0.2.apk')) {
    header("Location: downloads/TypeBridge-Android-v1.0.2.apk", true, 302);
    exit;
}

// 3. Fallback to GitHub Releases project tag
header("Location: https://github.com/loki-teche99/typebridge/releases", true, 302);
exit;
