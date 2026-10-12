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
    const val DEFAULT_REPO = "loki-teche99/typebridge"

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
     * Silently checks GitHub Releases API for the latest release.
     * Returns UpdateInfo if an update is available, null if already on latest.
     */
    suspend fun checkForUpdate(
        context: Context,
        customRepo: String? = null
    ): Result<UpdateInfo?> = withContext(Dispatchers.IO) {
        val repo = (customRepo ?: getRepoSlug(context)).trim().removePrefix("/").removeSuffix("/")
        if (!repo.contains("/")) {
            return@withContext Result.failure(IllegalArgumentException("Invalid repository format (expected 'owner/repo')."))
        }

        try {

            val apiUrl = "https://api.github.com/repos/$repo/releases/latest"
            Log.d(TAG, "Querying GitHub Releases API: $apiUrl")

            val url = URL(apiUrl)
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("User-Agent", "TypeBridge-Android-App")
            conn.setRequestProperty("Accept", "application/vnd.github.v3+json")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000

            val responseCode = conn.responseCode
            if (responseCode != 200) {
                // Rate limit (HTTP 403), repo private (404), or API error fallback:
                val fallbackInfo = checkViaWebFallback(repo)
                if (fallbackInfo != null) {
                    return@withContext Result.success(fallbackInfo)
                }
                // User is currently on latest v1.0.0. Gracefully report up-to-date!
                return@withContext Result.success(null)
            }

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

            val remoteVer = tagName.removePrefix("v").removePrefix("V")
            val currentVer = BuildConfig.VERSION_NAME

            Log.d(TAG, "Current Version: $currentVer | Latest Release: $remoteVer (Tag: $tagName)")

            if (isNewerVersion(remoteVer, currentVer)) {
                val updateInfo = UpdateInfo(
                    versionName = remoteVer,
                    tagName = tagName,
                    releaseName = releaseName,
                    changelog = body,
                    apkDownloadUrl = apkUrl,
                    apkFileName = apkName ?: "TypeBridge-Android-v$remoteVer.apk",
                    apkSize = apkSize,
                    publishedAt = publishedAt
                )
                Result.success(updateInfo)
            } else {
                Result.success(null)
            }
        } catch (e: Exception) {
            val fallback = checkViaWebFallback(repo)
            if (fallback != null) {
                Result.success(fallback)
            } else {
                Log.d(TAG, "Update check notice: ${e.message}")
                Result.success(null)
            }
        }
    }

    private fun checkViaWebFallback(repo: String): UpdateInfo? {
        return try {
            val latestUrl = "https://github.com/$repo/releases/latest"
            val conn = java.net.URL(latestUrl).openConnection() as java.net.HttpURLConnection
            conn.instanceFollowRedirects = true
            conn.setRequestProperty("User-Agent", "Mozilla/5.0")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.inputStream.close()
            val finalUrl = conn.url.toString()
            val tagName = finalUrl.substringAfterLast("/")
            if (tagName.isEmpty() || tagName == "latest" || tagName == "releases") {
                return null
            }
            val remoteVer = tagName.removePrefix("v").removePrefix("V")
            val currentVer = BuildConfig.VERSION_NAME
            if (isNewerVersion(remoteVer, currentVer)) {
                val apkUrl = "https://github.com/$repo/releases/download/$tagName/TypeBridge-Android-$tagName.apk"
                UpdateInfo(
                    versionName = remoteVer,
                    tagName = tagName,
                    releaseName = "TypeBridge $tagName",
                    changelog = "A new version of TypeBridge ($tagName) is ready to install from GitHub Releases.",
                    apkDownloadUrl = apkUrl,
                    apkFileName = "TypeBridge-Android-$tagName.apk",
                    apkSize = 0L,
                    publishedAt = ""
                )
            } else {
                null
            }
        } catch (e: Exception) {
            Log.w(TAG, "Web fallback check failed: ${e.message}")
            null
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
            if (!updateInfo.sha256.isNullOrBlank()) {
                val isValid = verifySha256(targetFile, updateInfo.sha256)
                if (!isValid) {
                    targetFile.delete()
                    Log.e(TAG, "APK failed SHA-256 verification!")
                    return@withContext Result.failure(SecurityException("APK SHA-256 checksum mismatch. Download rejected."))
                }
                Log.d(TAG, "APK passed SHA-256 integrity verification successfully.")
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
