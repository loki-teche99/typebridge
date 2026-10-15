package com.typebridge.mobile.service

import android.app.Service
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.util.DisplayMetrics
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.typebridge.mobile.R
import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.domain.repository.DeviceRepository
import com.typebridge.mobile.network.WebSocketClient
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject
import kotlin.math.hypot

private const val TAG = "FloatingOverlayService"

/**
 * Floating Screen Overlay Service for TypeBridge.
 * Shows a compact draggable circular TypeBridge bubble on top of all apps.
 * Tapping the bubble expands an action pill with:
 *  - [PASTE]: Pulls clipboard text into active buffer
 *  - [SEND & TYPE]: Instantly streams clipboard/buffer to PC for direct typing
 */
@AndroidEntryPoint
class FloatingOverlayService : Service() {

    companion object {
        const val ACTION_START = "com.typebridge.mobile.service.OVERLAY_START"
        const val ACTION_STOP = "com.typebridge.mobile.service.OVERLAY_STOP"

        var isRunning = false
            private set

        @Volatile
        var lastPastedText: String? = null

        fun start(context: Context) {
            try {
                val intent = Intent(context, FloatingOverlayService::class.java).apply {
                    action = ACTION_START
                }
                context.startService(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Error starting FloatingOverlayService: ${e.message}")
            }
        }

        fun stop(context: Context) {
            try {
                val intent = Intent(context, FloatingOverlayService::class.java).apply {
                    action = ACTION_STOP
                }
                context.stopService(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping FloatingOverlayService: ${e.message}")
            }
        }
    }

    @Inject
    lateinit var webSocketClient: WebSocketClient

    @Inject
    lateinit var deviceRepository: DeviceRepository

    private var windowManager: WindowManager? = null
    private var overlayView: View? = null
    private var windowParams: WindowManager.LayoutParams? = null

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var stateObservationJob: Job? = null

    private var cachedPastedText: String? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            Log.w(TAG, "Cannot create overlay: SYSTEM_ALERT_WINDOW permission not granted")
            stopSelf()
            return
        }

        isRunning = true
        setupOverlayView()
        observeConnectionState()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    private fun setupOverlayView() {
        try {
            windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val inflater = LayoutInflater.from(this)
            overlayView = inflater.inflate(R.layout.layout_floating_overlay, null)

            val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            }

            val params = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                layoutType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = 24
                y = 400
            }
            windowParams = params

            val bubbleLayout = overlayView?.findViewById<FrameLayout>(R.id.bubbleLayout)
            val menuLayout = overlayView?.findViewById<LinearLayout>(R.id.menuLayout)
            val btnPaste = overlayView?.findViewById<TextView>(R.id.btnOverlayPaste)
            val btnSend = overlayView?.findViewById<TextView>(R.id.btnOverlaySend)
            val btnClose = overlayView?.findViewById<ImageView>(R.id.btnOverlayClose)

            val touchSlop = ViewConfiguration.get(this).scaledTouchSlop

            // Drag and Tap detection on the circular bubble
            bubbleLayout?.setOnTouchListener(object : View.OnTouchListener {
                private var initialX = 0
                private var initialY = 0
                private var initialTouchX = 0f
                private var initialTouchY = 0f
                private var isDragging = false
                private var touchStartTime = 0L

                override fun onTouch(v: View, event: MotionEvent): Boolean {
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            initialX = params.x
                            initialY = params.y
                            initialTouchX = event.rawX
                            initialTouchY = event.rawY
                            touchStartTime = System.currentTimeMillis()
                            isDragging = false
                            return true
                        }
                        MotionEvent.ACTION_MOVE -> {
                            val dx = event.rawX - initialTouchX
                            val dy = event.rawY - initialTouchY
                            if (!isDragging && hypot(dx.toDouble(), dy.toDouble()) > touchSlop) {
                                isDragging = true
                            }
                            if (isDragging) {
                                params.x = (initialX + dx).toInt()
                                params.y = (initialY + dy).toInt()
                                windowManager?.updateViewLayout(overlayView, params)
                            }
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            val duration = System.currentTimeMillis() - touchStartTime
                            if (!isDragging && duration < 600) {
                                // Tap event -> toggle action menu
                                toggleMenu(menuLayout)
                            }
                            return true
                        }
                    }
                    return false
                }
            })

            // PASTE Action
            btnPaste?.setOnClickListener {
                handlePasteAction()
            }

            // SEND & TYPE Action
            btnSend?.setOnClickListener {
                handleSendAndTypeAction(menuLayout)
            }

            // Close / Minimize button
            btnClose?.setOnClickListener {
                menuLayout?.visibility = View.GONE
            }

            windowManager?.addView(overlayView, params)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create overlay view: ${e.message}", e)
        }
    }

    private fun toggleMenu(menuLayout: LinearLayout?) {
        if (menuLayout == null) return
        if (menuLayout.visibility == View.VISIBLE) {
            menuLayout.visibility = View.GONE
        } else {
            menuLayout.visibility = View.VISIBLE
            // Update button texts if text is already cached
            val btnPaste = overlayView?.findViewById<TextView>(R.id.btnOverlayPaste)
            if (cachedPastedText != null) {
                btnPaste?.text = "📋 READY (${cachedPastedText?.length})"
            } else {
                btnPaste?.text = "📋 PASTE"
            }
        }
    }

    private fun getClipboardText(): String? {
        return try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clipData = clipboard?.primaryClip
            if (clipData != null && clipData.itemCount > 0) {
                clipData.getItemAt(0).coerceToText(this).toString()
            } else null
        } catch (e: Exception) {
            Log.w(TAG, "Error reading clipboard: ${e.message}")
            null
        }
    }

    private fun handlePasteAction() {
        val text = getClipboardText()
        if (!text.isNullOrEmpty()) {
            cachedPastedText = text
            lastPastedText = text
            val btnPaste = overlayView?.findViewById<TextView>(R.id.btnOverlayPaste)
            btnPaste?.text = "📋 READY (${text.length})"
            Toast.makeText(this, "📋 Pasted! (${text.length} chars ready to send)", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "⚠️ Clipboard is empty", Toast.LENGTH_SHORT).show()
        }
    }

    private fun handleSendAndTypeAction(menuLayout: LinearLayout?) {
        val textToSend = cachedPastedText ?: getClipboardText()
        if (textToSend.isNullOrEmpty()) {
            Toast.makeText(this, "⚠️ No text found. Copy text first!", Toast.LENGTH_SHORT).show()
            return
        }

        Toast.makeText(this, "⚡ Sending to PC...", Toast.LENGTH_SHORT).show()

        serviceScope.launch {
            try {
                // Ensure connection is active
                if (webSocketClient.connectionState.value !is ConnectionState.Connected) {
                    val devices = deviceRepository.getDevices().first()
                    val paired = devices.firstOrNull()
                    if (paired != null && paired.sessionKey.isNotEmpty()) {
                        webSocketClient.connect(paired.ip, paired.port, paired.sessionId, paired.sessionKey)
                        // Await connection up to 3s
                        val deadline = System.currentTimeMillis() + 3000L
                        while (webSocketClient.connectionState.value !is ConnectionState.Connected && System.currentTimeMillis() < deadline) {
                            delay(100)
                        }
                    }
                }

                webSocketClient.sendText(textToSend)

                withContext(Dispatchers.Main) {
                    Toast.makeText(this@FloatingOverlayService, "✅ Sent! PC is typing...", Toast.LENGTH_SHORT).show()
                    cachedPastedText = null
                    menuLayout?.visibility = View.GONE
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@FloatingOverlayService, "❌ Send failed: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun observeConnectionState() {
        stateObservationJob = serviceScope.launch {
            webSocketClient.connectionState.collect { state ->
                val dot = overlayView?.findViewById<View>(R.id.overlayStatusDot) ?: return@collect
                when (state) {
                    is ConnectionState.Connected -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_connected)
                        )
                    }
                    is ConnectionState.Connecting, is ConnectionState.Reconnecting -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_connecting)
                        )
                    }
                    is ConnectionState.Disconnected, is ConnectionState.Error -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_disconnected)
                        )
                    }
                    is ConnectionState.Unstable -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_connecting)
                        )
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isRunning = false
        stateObservationJob?.cancel()
        serviceScope.cancel()

        try {
            if (overlayView != null && windowManager != null) {
                windowManager?.removeView(overlayView)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error removing overlay view: ${e.message}")
        }
        overlayView = null
        windowManager = null
    }
}
