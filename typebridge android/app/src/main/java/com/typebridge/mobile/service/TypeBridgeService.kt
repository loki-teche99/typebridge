package com.typebridge.mobile.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.typebridge.mobile.network.WebSocketClient
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

private const val TAG = "TypeBridgeService"
private const val CHANNEL_ID = "typebridge_service_channel"
private const val NOTIFICATION_ID = 1001

@AndroidEntryPoint
class TypeBridgeService : Service() {

    @Inject
    lateinit var webSocketClient: WebSocketClient

    private var wifiLock: WifiManager.WifiLock? = null
    private var wakeLock: PowerManager.WakeLock? = null

    companion object {
        const val ACTION_START = "com.typebridge.mobile.service.ACTION_START"
        const val ACTION_STOP = "com.typebridge.mobile.service.ACTION_STOP"

        fun startSafely(context: Context) {
            try {
                val intent = Intent(context, TypeBridgeService::class.java).apply {
                    action = ACTION_START
                }
                ContextCompat.startForegroundService(context, intent)
            } catch (e: Exception) {
                Log.w(TAG, "Could not start TypeBridgeService: ${e.message}")
            }
        }

        fun stopSafely(context: Context) {
            try {
                val intent = Intent(context, TypeBridgeService::class.java).apply {
                    action = ACTION_STOP
                }
                context.stopService(intent)
            } catch (e: Exception) {
                Log.w(TAG, "Could not stop TypeBridgeService: ${e.message}")
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            releaseLocks()
            stopForegroundSafely()
            stopSelf()
            return START_NOT_STICKY
        }

        startForegroundSafely()
        acquireLocks()
        return START_STICKY
    }

    private fun acquireLocks() {
        try {
            if (wifiLock == null) {
                val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                val lockMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                } else {
                    @Suppress("DEPRECATION")
                    WifiManager.WIFI_MODE_FULL_HIGH_PERF
                }
                wifiLock = wifiManager?.createWifiLock(lockMode, "TypeBridge:WifiLock")?.apply {
                    setReferenceCounted(false)
                    acquire()
                    Log.d(TAG, "Wi-Fi lock acquired (mode=$lockMode).")
                }
            }
            if (wakeLock == null) {
                val powerManager = applicationContext.getSystemService(Context.POWER_SERVICE) as? PowerManager
                wakeLock = powerManager?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "TypeBridge:WakeLock")?.apply {
                    setReferenceCounted(false)
                    acquire()
                    Log.d(TAG, "Partial wake lock acquired.")
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Could not acquire network wake locks: ${e.message}")
        }
    }

    private fun releaseLocks() {
        try {
            if (wifiLock?.isHeld == true) {
                wifiLock?.release()
                Log.d(TAG, "Wi-Fi lock released.")
            }
            wifiLock = null

            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
                Log.d(TAG, "Wake lock released.")
            }
            wakeLock = null
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing locks: ${e.message}")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "TypeBridge Background Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps connection alive to desktop typing assistant"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("TypeBridge Active")
            .setContentText("Connected to desktop — Ready to type")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
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
            Log.e(TAG, "Failed to start foreground service safely: ${e.message}", e)
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

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        releaseLocks()
        stopForegroundSafely()
    }
}
