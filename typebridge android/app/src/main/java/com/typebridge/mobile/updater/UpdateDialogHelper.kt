package com.typebridge.mobile.updater

import android.app.Activity
import android.app.Dialog
import android.content.Intent
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.typebridge.mobile.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

/**
 * UI helper to present modern update modals, live download progress dialogs,
 * and seamlessly trigger the Android Package Installer.
 */
object UpdateDialogHelper {

    var pendingInstallApk: File? = null

    /**
     * Presents the Update Available dialog with release notes.
     */
    fun showUpdateAvailableDialog(
        activity: Activity,
        updateInfo: UpdateInfo,
        onDismiss: (() -> Unit)? = null
    ) {
        if (activity.isFinishing || activity.isDestroyed) return

        val sizeMb = if (updateInfo.apkSize > 0) {
            String.format(Locale.US, "%.1f MB", updateInfo.apkSize / (1024f * 1024f))
        } else {
            "~9.3 MB"
        }

        val message = buildString {
            append("A new release of TypeBridge is available!\n\n")
            append("📦 Version: v${updateInfo.versionName}\n")
            append("💾 Package Size: $sizeMb\n\n")
            append("Changelog:\n")
            val cleanNotes = updateInfo.changelog.trim().ifEmpty { "Performance optimizations and stability fixes." }
            // Truncate if excessively long
            if (cleanNotes.length > 500) {
                append(cleanNotes.take(500)).append("...")
            } else {
                append(cleanNotes)
            }
        }

        MaterialAlertDialogBuilder(activity)
            .setTitle("✨ TypeBridge Update: v${updateInfo.versionName}")
            .setMessage(message)
            .setCancelable(true)
            .setPositiveButton("⚡ Update Now") { dialog, _ ->
                dialog.dismiss()
                startDownloadAndInstall(activity, updateInfo)
            }
            .setNegativeButton("Later") { dialog, _ ->
                dialog.dismiss()
                onDismiss?.invoke()
            }
            .setNeutralButton("View on GitHub") { _, _ ->
                try {
                    val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(updateInfo.apkDownloadUrl))
                    activity.startActivity(browserIntent)
                } catch (e: Exception) {
                    Toast.makeText(activity, "Could not open browser", Toast.LENGTH_SHORT).show()
                }
            }
            .show()
    }

    /**
     * Downloads APK with live progress dialog and launches installer.
     */
    fun startDownloadAndInstall(
        activity: Activity,
        updateInfo: UpdateInfo
    ) {
        if (activity.isFinishing || activity.isDestroyed) return

        // Build custom dialog with ProgressBar
        val layout = LayoutInflater.from(activity).inflate(
            activity.resources.getIdentifier("dialog_update_progress", "layout", activity.packageName).let { id ->
                if (id != 0) id else android.R.layout.simple_list_item_1
            },
            null,
            false
        )

        val builder = MaterialAlertDialogBuilder(activity)
            .setTitle("Downloading TypeBridge v${updateInfo.versionName}")
            .setCancelable(false)

        val progressBar = ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal).apply {
            isIndeterminate = false
            max = 100
            progress = 0
            setPadding(48, 24, 48, 12)
        }

        val statusText = TextView(activity).apply {
            text = "Connecting to GitHub Releases..."
            setPadding(48, 0, 48, 36)
            textSize = 13f
        }

        val container = android.widget.LinearLayout(activity).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            addView(progressBar)
            addView(statusText)
        }

        builder.setView(container)

        var downloadJob: Job? = null
        builder.setNegativeButton("Cancel") { dialog, _ ->
            downloadJob?.cancel()
            dialog.dismiss()
        }

        val dialog = builder.create()
        dialog.show()

        val scope = CoroutineScope(Dispatchers.Main)
        downloadJob = scope.launch {
            val result = AppUpdater.downloadApk(activity, updateInfo) { progress, downloaded, total ->
                dialog.runOnUiThread {
                    progressBar.progress = progress
                    if (total > 0) {
                        val downMb = downloaded / (1024f * 1024f)
                        val totMb = total / (1024f * 1024f)
                        statusText.text = String.format(Locale.US, "Downloaded %.1f MB / %.1f MB (%d%%)", downMb, totMb, progress)
                    } else {
                        val downMb = downloaded / (1024f * 1024f)
                        statusText.text = String.format(Locale.US, "Downloaded %.1f MB...", downMb)
                    }
                }
            }

            dialog.dismiss()

            result.fold(
                onSuccess = { apkFile ->
                    pendingInstallApk = apkFile
                    checkPermissionAndInstall(activity, apkFile)
                },
                onFailure = { error ->
                    MaterialAlertDialogBuilder(activity)
                        .setTitle("Download Failed")
                        .setMessage("Could not download update: ${error.message}")
                        .setPositiveButton("Retry") { _, _ ->
                            startDownloadAndInstall(activity, updateInfo)
                        }
                        .setNegativeButton("Dismiss", null)
                        .show()
                }
            )
        }
    }

    /**
     * Checks unknown app installation permission on Android 8.0+ and triggers install.
     */
    fun checkPermissionAndInstall(activity: Activity, apkFile: File) {
        if (!AppUpdater.canInstallPackages(activity)) {
            MaterialAlertDialogBuilder(activity)
                .setTitle("Install Permission Required")
                .setMessage("To install the new TypeBridge update, Android requires permission to install apps from this source. Tap Continue to allow in Settings.")
                .setPositiveButton("Continue") { _, _ ->
                    AppUpdater.requestInstallPermission(activity)
                }
                .setNegativeButton("Cancel", null)
                .show()
        } else {
            AppUpdater.triggerInstall(activity, apkFile)
        }
    }

    private fun Dialog.runOnUiThread(action: () -> Unit) {
        ownerActivity?.runOnUiThread(action) ?: run {
            android.os.Handler(android.os.Looper.getMainLooper()).post(action)
        }
    }
}
