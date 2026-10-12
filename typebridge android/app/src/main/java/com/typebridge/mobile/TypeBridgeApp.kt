package com.typebridge.mobile

import android.app.Application
import android.util.Log
import dagger.hilt.android.HiltAndroidApp
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter
import java.util.Date

private const val TAG = "TypeBridgeApp"

@HiltAndroidApp
class TypeBridgeApp : Application() {

    override fun onCreate() {
        super.onCreate()

        // Setup global safety net to capture unhandled exceptions and prevent hard crash dialogs
        val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            Log.e(TAG, "FATAL CRASH PREVENTED: Uncaught exception in thread '${thread.name}'", throwable)
            try {
                val logDir = getExternalFilesDir(null) ?: filesDir
                val crashFile = File(logDir, "last_crash.log")
                PrintWriter(FileWriter(crashFile, false)).use { pw ->
                    pw.println("=== TYPEBRIDGE CRASH DIAGNOSTIC REPORT ===")
                    pw.println("Timestamp: ${Date()}")
                    pw.println("Thread: ${thread.name} (id: ${thread.id})")
                    pw.println("Exception: ${throwable.javaClass.name}: ${throwable.message}")
                    pw.println("--- Stack Trace ---")
                    throwable.printStackTrace(pw)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to write crash log", e)
            }

            // Fallback to default handler to allow clean process exit if unrecoverable
            defaultHandler?.uncaughtException(thread, throwable)
        }

        Log.i(TAG, "TypeBridge application initialized safely.")
    }
}
