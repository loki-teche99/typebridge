package com.typebridge.mobile.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
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
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.typebridge.mobile.MainActivity
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
import kotlin.math.abs
import kotlin.math.hypot

private const val TAG = "FloatingOverlayService"
private const val CHANNEL_ID = "typebridge_overlay_channel"
private const val NOTIFICATION_ID = 2002

/**
 * Production-ready Floating Screen Overlay Service for TypeBridge.
 * Runs as a reliable Foreground Service so it stays permanently active over all apps.
 * Features:
 *  - Draggable circular TypeBridge logo bubble
 *  - Live connection status dot (Green / Amber / Red)
 *  - Touch-slop drag detection (move anywhere on screen)
 *  - Tap to expand instant shortcuts:
 *      * [PASTE]: Pulls clipboard text into active buffer with char counter
 *      * [SEND & TYPE]: Direct 1-tap stream to PC for immediate keystroke typing
 */
@AndroidEntryPoint
class FloatingOverlayService : Service() {

    companion object {
        const val ACTION_START = "com.typebridge.mobile.service.OVERLAY_START"
        const val ACTION_STOP = "com.typebridge.mobile.service.OVERLAY_STOP"

        @Volatile
        var isRunning = false
            private set

        @Volatile
        var lastPastedText: String? = null

        fun start(context: Context) {
            try {
                val intent = Intent(context, FloatingOverlayService::class.java).apply {
                    action = ACTION_START
                }
                ContextCompat.startForegroundService(context, intent)
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
        createNotificationChannel()
        startForegroundSafely()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            Log.w(TAG, "Cannot show overlay: SYSTEM_ALERT_WINDOW permission not granted")
            Toast.makeText(this, "Enable 'Display over other apps' to use TypeBridge floating button", Toast.LENGTH_LONG).show()
            stopSelf()
            return
        }

        isRunning = true
        setupOverlayView()
        observeConnectionState()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopForegroundSafely()
            stopSelf()
            return START_NOT_STICKY
        }
        startForegroundSafely()
        return START_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "TypeBridge Floating Button",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the TypeBridge floating screen button active over all apps"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val appIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, appIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("TypeBridge Screen Button Active")
            .setContentText("Tap circular button on screen to Paste & Type into PC")
            .setSmallIcon(android.R.drawable.ic_menu_edit)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
    }

    private fun startForegroundSafely() {
        try {
            val notification = buildNotification()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceCompat.startForeground(
                    this,
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start foreground safely: ${e.message}", e)
        }
    }

    private fun stopForegroundSafely() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_REMOVE)
            } else {
                @Suppress("DEPRECATION")
                stopForeground(true)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping foreground: ${e.message}")
        }
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
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = 24
                y = 350
            }
            windowParams = params

            val bubbleLayout = overlayView?.findViewById<FrameLayout>(R.id.bubbleLayout)
            val btnPaste = overlayView?.findViewById<TextView>(R.id.btnOverlayPaste)
            val btnSend = overlayView?.findViewById<TextView>(R.id.btnOverlaySend)
            val btnClose = overlayView?.findViewById<ImageView>(R.id.btnOverlayClose)

            val touchSlop = ViewConfiguration.get(this).scaledTouchSlop

            // Touch Listener on Circular Bubble for moving anywhere on screen or tapping to expand
            bubbleLayout?.setOnTouchListener(object : View.OnTouchListener {
                private var initialX = 0
                private var initialY = 0
                private var initialTouchX = 0f
                private var initialTouchY = 0f
                private var isDragging = false
                private var touchStartTime = 0L

                override fun onTouch(v: View, event: MotionEvent): Boolean {
                    val p = windowParams ?: return false
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            initialX = p.x
                            initialY = p.y
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
                                val metrics = resources.displayMetrics
                                val maxX = metrics.widthPixels - 120
                                val maxY = metrics.heightPixels - 120
                                p.x = (initialX + dx).toInt().coerceIn(0, maxX)
                                p.y = (initialY + dy).toInt().coerceIn(0, maxY)
                                try {
                                    windowManager?.updateViewLayout(overlayView, p)
                                } catch (e: Exception) {
                                    // ignore layout update race conditions
                                }
                            }
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            val duration = System.currentTimeMillis() - touchStartTime
                            val dx = abs(event.rawX - initialTouchX)
                            val dy = abs(event.rawY - initialTouchY)
                            if (!isDragging && dx < touchSlop && dy < touchSlop && duration < 600) {
                                // Tap event -> toggle action menu
                                toggleMenu()
                            }
                            return true
                        }
                    }
                    return false
                }
            })

            // Shortcut: [ PASTE ]
            btnPaste?.setOnClickListener {
                handlePasteAction()
            }

            // Shortcut: [ SEND & TYPE ]
            btnSend?.setOnClickListener {
                handleSendAndTypeAction()
            }

            // Close button
            btnClose?.setOnClickListener {
                closeMenu()
            }

            windowManager?.addView(overlayView, params)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create overlay view: ${e.message}", e)
        }
    }

    private fun toggleMenu() {
        val menu = overlayView?.findViewById<LinearLayout>(R.id.menuLayout) ?: return
        val params = windowParams ?: return
        if (menu.visibility == View.VISIBLE) {
            menu.visibility = View.GONE
        } else {
            menu.visibility = View.VISIBLE
            val btnPaste = overlayView?.findViewById<TextView>(R.id.btnOverlayPaste)
            if (cachedPastedText != null) {
                btnPaste?.text = "📋 READY (${cachedPastedText?.length})"
            } else {
                btnPaste?.text = "📋 PASTE"
            }
        }
        try {
            windowManager?.updateViewLayout(overlayView, params)
        } catch (e: Exception) {
            Log.w(TAG, "Error updating overlay layout: ${e.message}")
        }
    }

    private fun closeMenu() {
        val menu = overlayView?.findViewById<LinearLayout>(R.id.menuLayout) ?: return
        val params = windowParams ?: return
        menu.visibility = View.GONE
        try {
            windowManager?.updateViewLayout(overlayView, params)
        } catch (e: Exception) {
            Log.w(TAG, "Error updating overlay layout: ${e.message}")
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
            val preview = if (text.length > 25) text.take(25) + "..." else text
            Toast.makeText(this, "📋 Pasted: \"$preview\" (${text.length} chars ready to Send)", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "⚠️ Clipboard is empty! Copy text first.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun handleSendAndTypeAction() {
        val textToSend = cachedPastedText ?: getClipboardText()
        if (textToSend.isNullOrEmpty()) {
            Toast.makeText(this, "⚠️ No text to send. Copy some text first!", Toast.LENGTH_SHORT).show()
            return
        }

        Toast.makeText(this, "⚡ Sending to PC... Typing started!", Toast.LENGTH_SHORT).show()
        closeMenu()

        serviceScope.launch(Dispatchers.IO) {
            try {
                // Ensure connection is established
                if (webSocketClient.connectionState.value !is ConnectionState.Connected) {
                    val devices = deviceRepository.getDevices().first()
                    val paired = devices.firstOrNull()
                    if (paired != null && paired.sessionKey.isNotEmpty()) {
                        webSocketClient.connect(paired.ip, paired.port, paired.sessionId, paired.sessionKey)
                        // Await connection up to 3 seconds
                        val deadline = System.currentTimeMillis() + 3000L
                        while (webSocketClient.connectionState.value !is ConnectionState.Connected && System.currentTimeMillis() < deadline) {
                            delay(100)
                        }
                    }
                }

                webSocketClient.sendText(textToSend)

                withContext(Dispatchers.Main) {
                    Toast.makeText(this@FloatingOverlayService, "✅ Sent! PC is actively typing.", Toast.LENGTH_SHORT).show()
                    cachedPastedText = null
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
                    is ConnectionState.Connecting, is ConnectionState.Reconnecting, is ConnectionState.Unstable -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_connecting)
                        )
                    }
                    is ConnectionState.Disconnected, is ConnectionState.Error -> {
                        dot.backgroundTintList = ColorStateList.valueOf(
                            ContextCompat.getColor(this@FloatingOverlayService, R.color.tb_disconnected)
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
        stopForegroundSafely()
    }
}
