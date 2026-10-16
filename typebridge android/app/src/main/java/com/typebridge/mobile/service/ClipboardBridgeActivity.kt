package com.typebridge.mobile.service

import android.app.Activity
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast

/**
 * Transparent, zero-flicker trampoline Activity.
 * Solves the Android 10+ (API 29+) background clipboard access restriction.
 * Because this Activity runs in the foreground with window focus, Android
 * grants 100% legal access to ClipboardManager.getPrimaryClip().
 * Completes and dismisses itself in ~15ms with no animation.
 */
class ClipboardBridgeActivity : Activity() {

    companion object {
        const val ACTION_PASTE = "com.typebridge.mobile.ACTION_OVERLAY_PASTE"
        const val ACTION_SEND_AND_TYPE = "com.typebridge.mobile.ACTION_OVERLAY_SEND_AND_TYPE"

        fun launch(context: Context, action: String) {
            val intent = Intent(context, ClipboardBridgeActivity::class.java).apply {
                this.action = action
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION or Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS)
            }
            context.startActivity(intent)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        overridePendingTransition(0, 0)

        try {
            val text = readClipboard()
            when (intent?.action) {
                ACTION_PASTE -> {
                    if (!text.isNullOrEmpty()) {
                        FloatingOverlayService.onTextPasted(this, text)
                    } else {
                        Toast.makeText(this, "⚠️ Clipboard is empty! Copy text first.", Toast.LENGTH_SHORT).show()
                    }
                }
                ACTION_SEND_AND_TYPE -> {
                    val candidate = FloatingOverlayService.lastPastedText ?: text
                    if (!candidate.isNullOrEmpty()) {
                        FloatingOverlayService.onSendAndTypeTriggered(this, candidate)
                    } else {
                        Toast.makeText(this, "⚠️ No text to send. Copy some text first!", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        } catch (e: Exception) {
            Toast.makeText(this, "Error accessing clipboard: ${e.message}", Toast.LENGTH_SHORT).show()
        } finally {
            finish()
            overridePendingTransition(0, 0)
        }
    }

    private fun readClipboard(): String? {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return null
        val clip = clipboard.primaryClip ?: return null
        if (clip.itemCount > 0) {
            return clip.getItemAt(0)?.coerceToText(this)?.toString()
        }
        return null
    }

    override fun finish() {
        super.finish()
        overridePendingTransition(0, 0)
    }
}
