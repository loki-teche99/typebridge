package com.typebridge.mobile.updater

/**
 * Metadata for a detected remote update from GitHub Releases.
 */
data class UpdateInfo(
    val versionName: String,
    val tagName: String,
    val releaseName: String,
    val changelog: String,
    val apkDownloadUrl: String,
    val apkFileName: String,
    val apkSize: Long,
    val publishedAt: String,
    val sha256: String? = null
)
