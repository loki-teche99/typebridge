package com.typebridge.mobile.updater

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.content.FileProvider
import com.typebridge.mobile.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

private const val TAG = "AppUpdater"

/**
 * Android GitHub Releases Auto-Updater for TypeBridge.
 * Handles silent background version checks, streaming download with progress,
 * and seamless package installation via FileProvider.
 */
object AppUpdater {

    private const val PREFS_NAME = "typebridge_updater_prefs"
    private const val KEY_GITHUB_REPO = "github_repo"
    private const val KEY_AUTO_CHECK = "auto_check_updates"
    private const val KEY_LAST_CHECK_TS = "last_update_check_ts"
    private const val KEY_UPDATE_ETAG = "update_etag"

    const val DEFAULT_REPO = "loki-teche99/typebridge"
    const val AUTO_CHECK_INTERVAL_MS = 168L * 3600L * 1000L // Exactly 7 days (168 hours)

    @Volatile
    private var isCheckInProgress = false

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun getRepoSlug(context: Context? = null): String {
        return DEFAULT_REPO
    }

    fun setRepoSlug(context: Context, slug: String) {
        // Locked to backend repository
    }

    fun isAutoCheckEnabled(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_AUTO_CHECK, true)
    }

    fun setAutoCheckEnabled(context: Context, enabled: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_AUTO_CHECK, enabled).apply()
    }

    /**
     * Extracts integer list from version string, e.g. "v1.1.0" -> [1, 1, 0]
     */
    fun parseVersion(versionStr: String): List<Int> {
        val cleaned = versionStr.trim().removePrefix("v").removePrefix("V")
        val regex = Regex("\\d+")
        val matches = regex.findAll(cleaned).map { it.value.toIntOrNull() ?: 0 }.toList()
        return if (matches.isNotEmpty()) matches else listOf(0, 0, 0)
    }

    /**
     * Returns true if remote version is strictly newer than local version.
     */
    fun isNewerVersion(remoteVer: String, localVer: String): Boolean {
        val remoteNums = parseVersion(remoteVer)
        val localNums = parseVersion(localVer)
        val maxLen = maxOf(remoteNums.size, localNums.size)

        for (i in 0 until maxLen) {
            val r = remoteNums.getOrElse(i) { 0 }
            val l = localNums.getOrElse(i) { 0 }
            if (r > l) return true
            if (r < l) return false
        }
        return false
    }

    /**
     * Checks GitHub Releases API for the latest release.
     * When isManual is false, enforces 7-day (168 hours) interval.
     * When isManual is true, bypasses interval check immediately.
     * Uses ETag caching (If-None-Match) to avoid exhausting GitHub rate limits.
     */
    suspend fun checkForUpdate(
        context: Context,
        isManual: Boolean = false,
        customRepo: String? = null
    ): Result<UpdateInfo?> = withContext(Dispatchers.IO) {
        val repo = (customRepo ?: getRepoSlug(context)).trim().removePrefix("/").removeSuffix("/")
        if (!repo.contains("/")) {
            return@withContext Result.failure(IllegalArgumentException("Invalid repository format (expected 'owner/repo')."))
        }

        // 1. In-flight request deduplication
        synchronized(AppUpdater) {
            if (isCheckInProgress) {
                Log.d(TAG, "Update check already in progress. Skipping duplicate request.")
                return@withContext Result.success(null)
            }
            isCheckInProgress = true
        }

        try {
            val now = System.currentTimeMillis()

            // 2. 7-Day (168 Hours) Interval Enforcement for Automatic Checks
            if (!isManual) {
                val lastCheckTs = getPrefs(context).getLong(KEY_LAST_CHECK_TS, 0L)
                if ((now - lastCheckTs) < AUTO_CHECK_INTERVAL_MS) {
                    val remainingHours = (AUTO_CHECK_INTERVAL_MS - (now - lastCheckTs)) / (3600 * 1000)
                    Log.d(TAG, "Auto-update check skipped: next check in ${remainingHours}h (7-day interval active).")
                    return@withContext Result.success(null)
                }
            }

            val apiUrl = "https://api.github.com/repos/$repo/releases/latest"
            Log.d(TAG, "Querying GitHub Releases API: $apiUrl (isManual=$isManual)")

            val url = URL(apiUrl)
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("User-Agent", "TypeBridge-Android-App")
            conn.setRequestProperty("Accept", "application/vnd.github.v3+json")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000

            // 3. ETag Caching to Respect GitHub Rate Limits
            val cachedEtag = getPrefs(context).getString(KEY_UPDATE_ETAG, null)
            if (!cachedEtag.isNullOrBlank()) {
                conn.setRequestProperty("If-None-Match", cachedEtag)
            }

            val responseCode = conn.responseCode
            Log.d(TAG, "GitHub Releases API response code: $responseCode")

            // 4. Handle HTTP 304 Not Modified
            if (responseCode == 304) {
                Log.d(TAG, "HTTP 304 Not Modified: release unchanged according to ETag.")
                getPrefs(context).edit().putLong(KEY_LAST_CHECK_TS, now).apply()
                return@withContext Result.success(null)
            }

            // 5. Handle HTTP 404 (No release published yet on repository)
            if (responseCode == 404) {
                Log.d(TAG, "HTTP 404: No releases published yet on $repo.")
                getPrefs(context).edit().putLong(KEY_LAST_CHECK_TS, now).apply()
                return@withContext Result.success(null)
            }

            // 6. Handle HTTP 403 / 429 (Rate limiting with header parsing)
            if (responseCode == 403 || responseCode == 429) {
                val resetHeader = conn.getHeaderField("X-RateLimit-Reset")
                val resetEpochSeconds = resetHeader?.toLongOrNull() ?: ((now / 1000) + 3600)
                val resetDate = java.util.Date(resetEpochSeconds * 1000)
                val timeFormat = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault())
                val formattedTime = timeFormat.format(resetDate)

                Log.w(TAG, "GitHub API rate limit reached ($responseCode). Resets at $formattedTime.")
                getPrefs(context).edit().putLong(KEY_LAST_CHECK_TS, now).apply()

                if (!isManual) {
                    return@withContext Result.success(null)
                }
                return@withContext Result.failure(Exception("GitHub API rate limit exceeded. Resets at $formattedTime. Please try again later."))
            }

            // 7. Handle other unexpected HTTP errors
            if (responseCode != 200) {
                Log.w(TAG, "GitHub API returned HTTP $responseCode.")
                getPrefs(context).edit().putLong(KEY_LAST_CHECK_TS, now).apply()
                if (!isManual) {
                    return@withContext Result.success(null)
                }
                return@withContext Result.failure(java.io.IOException("GitHub API returned HTTP $responseCode"))
            }

            // Store new ETag and timestamp on 200 OK
            val newEtag = conn.getHeaderField("ETag")
            val editor = getPrefs(context).edit().putLong(KEY_LAST_CHECK_TS, now)
            if (!newEtag.isNullOrBlank()) {
                editor.putString(KEY_UPDATE_ETAG, newEtag)
            }
            editor.apply()

            val jsonText = conn.inputStream.bufferedReader().use { it.readText() }
            val releaseObj = JSONObject(jsonText)

            val tagName = releaseObj.optString("tag_name", "")
            val releaseName = releaseObj.optString("name", tagName)
            val body = releaseObj.optString("body", "No release notes provided.")
            val publishedAt = releaseObj.optString("published_at", "")

            var apkUrl: String? = null
            var apkName: String? = null
            var apkSize = 0L

            val assetsArr = releaseObj.optJSONArray("assets")
            if (assetsArr != null) {
                // First pass: look for TypeBridge Android APK
                for (i in 0 until assetsArr.length()) {
                    val asset = assetsArr.getJSONObject(i)
                    val name = asset.optString("name", "")
                    if (name.endsWith(".apk", ignoreCase = true) &&
                        (name.contains("android", ignoreCase = true) || name.contains("typebridge", ignoreCase = true))
                    ) {
                        apkUrl = asset.optString("browser_download_url")
                        apkName = name
                        apkSize = asset.optLong("size", 0L)
                        break
                    }
                }

                // Second pass: any .apk
                if (apkUrl == null) {
                    for (i in 0 until assetsArr.length()) {
                        val asset = assetsArr.getJSONObject(i)
                        val name = asset.optString("name", "")
                        if (name.endsWith(".apk", ignoreCase = true)) {
                            apkUrl = asset.optString("browser_download_url")
                            apkName = name
                            apkSize = asset.optLong("size", 0L)
                            break
                        }
                    }
                }
            }

            if (apkUrl.isNullOrEmpty()) {
                Log.d(TAG, "Release $tagName found, but no .apk asset attached.")
                return@withContext Result.success(null)
            }

                var manifestUrl: String? = null
                var sha256sumsUrl: String? = null
                var expectedSha256: String? = null

                if (assetsArr != null) {
                    for (i in 0 until assetsArr.length()) {
                        val asset = assetsArr.getJSONObject(i)
                        val name = asset.optString("name", "")
                        if (name.equals("release-manifest.json", ignoreCase = true)) {
                            manifestUrl = asset.optString("browser_download_url")
                        } else if (name.equals("sha256sums.txt", ignoreCase = true)) {
                            sha256sumsUrl = asset.optString("browser_download_url")
                        }
                    }
                }

                // If release manifest exists, fetch it to get authoritative SHA-256 and size
                if (!manifestUrl.isNullOrEmpty()) {
                    try {
                        val mConn = URL(manifestUrl).openConnection() as HttpURLConnection
                        mConn.connectTimeout = 5000
                        mConn.readTimeout = 5000
                        if (mConn.responseCode == 200) {
                            val mJson = JSONObject(mConn.inputStream.bufferedReader().use { it.readText() })
                            val androidObj = mJson.optJSONObject("android")
                            val mAssets = androidObj?.optJSONArray("assets")
                            if (mAssets != null && mAssets.length() > 0) {
                                val firstAsset = mAssets.getJSONObject(0)
                                val mSha = firstAsset.optString("sha256")
                                if (mSha.length == 64) expectedSha256 = mSha
                                val mSize = firstAsset.optLong("size", 0L)
                                if (mSize > 0) apkSize = mSize
                            }
                        }
                    } catch (e: Exception) {
                        Log.d(TAG, "Manifest fetch notice: ${e.message}")
                    }
                }

                // Fallback to sha256sums.txt
                if (expectedSha256.isNullOrBlank() && !sha256sumsUrl.isNullOrEmpty()) {
                    try {
                        val sConn = URL(sha256sumsUrl).openConnection() as HttpURLConnection
                        sConn.connectTimeout = 5000
                        sConn.readTimeout = 5000
                        if (sConn.responseCode == 200) {
                            val lines = sConn.inputStream.bufferedReader().readLines()
                            for (line in lines) {
                                if (line.contains(".apk", ignoreCase = true)) {
                                    val parts = line.trim().split(Regex("\\s+"))
                                    if (parts.isNotEmpty() && parts[0].length == 64) {
                                        expectedSha256 = parts[0]
                                        break
                                    }
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.d(TAG, "sha256sums fetch notice: ${e.message}")
                    }
                }

                val remoteVer = tagName.removePrefix("v").removePrefix("V")
                val currentVer = BuildConfig.VERSION_NAME

                Log.d(TAG, "Current Version: $currentVer | Latest Release: $remoteVer (Tag: $tagName)")

                if (isNewerVersion(remoteVer, currentVer)) {
                    // Fail closed: enforce valid 64-char SHA-256 digest from release-manifest or sha256sums
                    if (expectedSha256.isNullOrBlank() || expectedSha256.length != 64) {
                        Log.e(TAG, "Fail closed: release $tagName lacks trusted SHA-256 digest.")
                        return@withContext Result.failure(SecurityException("Untrusted release: release-manifest.json or sha256sums.txt is missing a valid SHA-256 digest."))
                    }

                    val updateInfo = UpdateInfo(
                        versionName = remoteVer,
                        tagName = tagName,
                        releaseName = releaseName,
                        changelog = body,
                        apkDownloadUrl = apkUrl,
                        apkFileName = apkName ?: "TypeBridge-Android-v$remoteVer.apk",
                        apkSize = apkSize,
                        publishedAt = publishedAt,
                        sha256 = expectedSha256
                    )
                    Result.success(updateInfo)
                } else {
                    Result.success(null)
                }
        } catch (e: Exception) {
            Log.e(TAG, "Update check failed: ${e.message}", e)
            if (!isManual) {
                Result.success(null)
            } else {
                Result.failure(e)
            }
        } finally {
            synchronized(AppUpdater) {
                isCheckInProgress = false
            }
        }
    }

    /**
     * Downloads APK from GitHub Releases with live progress reporting.
     */
    suspend fun downloadApk(
        context: Context,
        updateInfo: UpdateInfo,
        onProgress: (progress: Int, downloadedBytes: Long, totalBytes: Long) -> Unit
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            val cacheDir = context.externalCacheDir ?: context.cacheDir
            val targetFile = File(cacheDir, updateInfo.apkFileName)
            if (targetFile.exists()) {
                targetFile.delete()
            }

            Log.d(TAG, "Downloading APK from: ${updateInfo.apkDownloadUrl} -> ${targetFile.absolutePath}")

            var downloadUrl = updateInfo.apkDownloadUrl
            var conn = URL(downloadUrl).openConnection() as HttpURLConnection
            conn.instanceFollowRedirects = true
            conn.setRequestProperty("User-Agent", "TypeBridge-Android-App")
            conn.connectTimeout = 15000
            conn.readTimeout = 30000

            // Handle HTTP redirects (GitHub Releases redirect to AWS S3)
            var redirects = 0
            while (conn.responseCode in 301..308 && redirects < 5) {
                val newUrl = conn.getHeaderField("Location")
                if (!newUrl.isNullOrEmpty()) {
                    downloadUrl = newUrl
                    conn.disconnect()
                    conn = URL(downloadUrl).openConnection() as HttpURLConnection
                    conn.setRequestProperty("User-Agent", "TypeBridge-Android-App")
                    conn.connectTimeout = 15000
                    conn.readTimeout = 30000
                    redirects++
                } else {
                    break
                }
            }

            val totalLength = if (conn.contentLengthLong > 0) conn.contentLengthLong else updateInfo.apkSize

            var inputStream: InputStream? = null
            var outputStream: FileOutputStream? = null

            try {
                inputStream = conn.inputStream
                outputStream = FileOutputStream(targetFile)

                val buffer = ByteArray(8192)
                var bytesRead: Int
                var downloaded: Long = 0
                var lastProgress = -1

                while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                    outputStream.write(buffer, 0, bytesRead)
                    downloaded += bytesRead

                    if (totalLength > 0) {
                        val progress = ((downloaded * 100) / totalLength).toInt()
                        if (progress != lastProgress) {
                            lastProgress = progress
                            onProgress(progress, downloaded, totalLength)
                        }
                    } else {
                        onProgress(0, downloaded, 0)
                    }
                }
                outputStream.flush()
            } finally {
                outputStream?.close()
                inputStream?.close()
                conn.disconnect()
            }

            Log.d(TAG, "APK download complete: ${targetFile.length()} bytes")

            // Strict fail-closed integrity verification
            // 1. Mandatory SHA-256 digest
            if (updateInfo.sha256.isNullOrBlank() || updateInfo.sha256.length != 64) {
                targetFile.delete()
                Log.e(TAG, "Fail closed: update missing trusted 64-character SHA-256 digest.")
                return@withContext Result.failure(SecurityException("APK installation rejected: missing trusted SHA-256 digest."))
            }

            // 2. Verify file size if known
            if (updateInfo.apkSize > 0 && targetFile.length() != updateInfo.apkSize) {
                targetFile.delete()
                Log.e(TAG, "APK size mismatch! Expected: ${updateInfo.apkSize}, got: ${targetFile.length()}")
                return@withContext Result.failure(java.io.IOException("APK file size mismatch (truncated download). File removed."))
            }

            // 3. Cryptographic SHA-256 hash match
            val isValid = verifySha256(targetFile, updateInfo.sha256)
            if (!isValid) {
                targetFile.delete()
                Log.e(TAG, "APK failed SHA-256 verification!")
                return@withContext Result.failure(SecurityException("APK SHA-256 checksum mismatch. Download rejected."))
            }
            Log.d(TAG, "APK passed SHA-256 integrity verification successfully.")

            // 4. Verify package archive integrity and application ID
            val pm = context.packageManager
            val archiveInfo = pm.getPackageArchiveInfo(targetFile.absolutePath, 0)
            if (archiveInfo == null || archiveInfo.packageName != context.packageName) {
                targetFile.delete()
                Log.e(TAG, "Downloaded package invalid or packageName does not match ${context.packageName}")
                return@withContext Result.failure(SecurityException("Downloaded package is invalid or does not match application ID."))
            }

            Result.success(targetFile)
        } catch (e: Exception) {
            Log.e(TAG, "Download APK failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    fun verifySha256(file: File, expectedSha256: String?): Boolean {
        if (expectedSha256.isNullOrBlank()) return true
        return try {
            val digest = java.security.MessageDigest.getInstance("SHA-256")
            file.inputStream().use { input ->
                val buffer = ByteArray(8192)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    digest.update(buffer, 0, bytesRead)
                }
            }
            val hex = digest.digest().joinToString("") { "%02x".format(it) }
            hex.equals(expectedSha256.trim(), ignoreCase = true)
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Checks whether the app has permission to request package installations on Android 8.0+.
     */
    fun canInstallPackages(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.packageManager.canRequestPackageInstalls()
        } else {
            true
        }
    }

    /**
     * Navigates user to system settings to grant "Install unknown apps" permission.
     */
    fun requestInstallPermission(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to launch ACTION_MANAGE_UNKNOWN_APP_SOURCES: ${e.message}")
            }
        }
    }

    /**
     * Launches Android's native package installer via FileProvider.
     */
    fun triggerInstall(context: Context, apkFile: File): Boolean {
        try {
            if (!apkFile.exists() || apkFile.length() == 0L) {
                Log.e(TAG, "APK file does not exist or is empty: ${apkFile.absolutePath}")
                return false
            }

            val apkUri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                apkFile
            )

            val installIntent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(apkUri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            context.startActivity(installIntent)
            Log.d(TAG, "Triggered package installer successfully with URI: $apkUri")
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch package installer: ${e.message}", e)
            return false
        }
    }
}
