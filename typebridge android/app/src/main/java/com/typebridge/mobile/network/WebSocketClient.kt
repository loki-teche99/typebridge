package com.typebridge.mobile.network

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.security.CryptoEngine
import com.typebridge.mobile.service.TypeBridgeService
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import com.typebridge.mobile.domain.repository.DeviceRepository
import kotlinx.coroutines.flow.first
import java.util.UUID
import javax.inject.Inject
import javax.inject.Provider
import javax.inject.Singleton

private const val TAG = "WebSocketClient"

@Singleton
class WebSocketClient @Inject constructor(
    @ApplicationContext private val context: Context,
    private val client: OkHttpClient,
    private val cryptoEngine: CryptoEngine,
    private val gson: Gson,
    private val deviceRepositoryProvider: Provider<DeviceRepository>
) {
    @Volatile
    private var webSocket: WebSocket? = null
    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var activeIp: String? = null
    private var activePort: Int = 8765
    private var sessionId: String? = null
    private var sessionKey: ByteArray? = null

    private var heartbeatJob: Job? = null
    private var reconnectJob: Job? = null
    private var isManualDisconnect = false
    private var reconnectAttempt = 0
    private var heartbeatMissCount = 0

    init {
        registerNetworkCallback()
    }

    private fun registerNetworkCallback() {
        try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            val request = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()
            cm?.registerNetworkCallback(request, object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    Log.d(TAG, "Network restored. Triggering self-healing reconnect...")
                    if (!isManualDisconnect && _connectionState.value !is ConnectionState.Connected) {
                        scheduleReconnect()
                    }
                }
            })
        } catch (e: Exception) {
            Log.w(TAG, "Could not register NetworkCallback: ${e.message}")
        }
    }

    /**
     * Connect to paired desktop device.
     */
    @Synchronized
    fun connect(ip: String, port: Int, sId: String, key: ByteArray) {
        val cleanIp = ip.trim()
        if (cleanIp.isEmpty() || key.size != 32) {
            Log.e(TAG, "Invalid connection parameters: ip='$cleanIp', key length=${key.size}")
            _connectionState.value = ConnectionState.Error("Invalid connection parameters")
            return
        }

        isManualDisconnect = false
        reconnectAttempt = 0
        activeIp = cleanIp
        activePort = port
        sessionId = sId
        sessionKey = key

        // If already connected or connecting to this IP, don't duplicate
        val currentState = _connectionState.value
        if ((currentState is ConnectionState.Connected || currentState is ConnectionState.Connecting) && webSocket != null && activeIp == cleanIp) {
            Log.d(TAG, "Already connected or connecting to $cleanIp:$port")
            return
        }

        _connectionState.value = ConnectionState.Connecting

        // Cancel previous socket before opening new one
        try {
            webSocket?.cancel()
        } catch (e: Exception) {
            Log.w(TAG, "Error canceling previous socket", e)
        }
        webSocket = null

        val request = Request.Builder()
            .url("wss://$cleanIp:$port")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected successfully to $cleanIp:$port")
                reconnectAttempt = 0
                heartbeatMissCount = 0
                _connectionState.value = ConnectionState.Connected(cleanIp, 5L)
                startHeartbeat()

                // Keep connection alive via foreground service
                TypeBridgeService.startSafely(context)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed (code=$code, reason=$reason)")
                this@WebSocketClient.webSocket = null
                stopHeartbeat()
                _connectionState.value = ConnectionState.Disconnected
                if (!isManualDisconnect) {
                    scheduleReconnect()
                } else {
                    TypeBridgeService.stopSafely(context)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure: ${t.message}")
                this@WebSocketClient.webSocket = null
                stopHeartbeat()
                if (!isManualDisconnect) {
                    _connectionState.value = ConnectionState.Error(t.message ?: "Connection dropped")
                    scheduleReconnect()
                } else {
                    _connectionState.value = ConnectionState.Disconnected
                    TypeBridgeService.stopSafely(context)
                }
            }
        })
    }

    private fun handleMessage(text: String) {
        try {
            val msg = gson.fromJson(text, ProtocolMessage::class.java) ?: return
            val sKey = sessionKey
            if (msg.type == MessageType.ACK && !msg.payload.isNullOrEmpty() && sKey != null && sKey.size == 32) {
                val iv = msg.iv ?: return
                try {
                    val decrypted = cryptoEngine.decrypt(sKey, msg.payload, iv)
                    Log.d(TAG, "ACK received from Desktop: $decrypted")
                } catch (e: Exception) {
                    Log.w(TAG, "Could not decrypt ACK: ${e.message}")
                }
            } else if (msg.type == MessageType.HEARTBEAT) {
                try {
                    val payload = gson.fromJson(msg.payload, Map::class.java) as? Map<*, *>
                    val tSent = (payload?.get("t_sent") as? Number)?.toLong() ?: 0L
                    val isEcho = (payload?.get("is_echo") as? Boolean) ?: false

                    if (isEcho && tSent > 0) {
                        // Phone sent tSent, desktop echoed it back -> True Round-Trip Time (RTT in ms)
                        val now = System.currentTimeMillis()
                        val latency = (now - tSent).coerceAtLeast(1L).coerceAtMost(999L)
                        _connectionState.value = ConnectionState.Connected(activeIp ?: "Desktop", latency)
                    } else if (!isEcho && msg.payload != null) {
                        // Desktop sent its own heartbeat; reply with echo immediately
                        val echoPayload = gson.toJson(mapOf(
                            "t_sent" to tSent,
                            "is_echo" to true
                        ))
                        val echoMsg = ProtocolMessage(
                            id        = UUID.randomUUID().toString(),
                            type      = MessageType.HEARTBEAT,
                            payload   = echoPayload,
                            iv        = null,
                            sessionId = sessionId,
                            timestamp = System.currentTimeMillis()
                        )
                        webSocket?.send(gson.toJson(echoMsg))
                    }
                } catch (e: Exception) {
                    // ignore
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Message parse error", e)
        }
    }

    /**
     * Encrypt and send text payload to Desktop for immediate typing.
     * With auto-retry buffer if socket is momentarily reconnecting.
     */
    suspend fun sendText(text: String) {
        val sKey = sessionKey ?: throw IllegalStateException("Not paired with Desktop. Please pair first.")
        if (sKey.size != 32) {
            throw IllegalStateException("Invalid encryption key. Please re-pair with desktop.")
        }

        // Resilient socket retrieval (wait up to 5s if temporarily reconnecting)
        var ws = webSocket
        if (ws == null && activeIp != null) {
            val deadline = System.currentTimeMillis() + 5000L
            while (webSocket == null && System.currentTimeMillis() < deadline) {
                if (isManualDisconnect) return  // Don't retry if user disconnected
                delay(100)
            }
            ws = webSocket
        }

        if (ws == null) {
            throw IllegalStateException("Cannot connect to Desktop. Please ensure Desktop app is open.")
        }

        val payloadData = TextPayloadData(text, UUID.randomUUID().toString())
        val payloadJson = gson.toJson(payloadData)
        val encrypted = cryptoEngine.encrypt(sKey, payloadJson)

        val msg = ProtocolMessage(
            id        = UUID.randomUUID().toString(),
            type      = MessageType.TEXT_PAYLOAD,
            payload   = encrypted.first,
            iv        = encrypted.second,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis()
        )
        val jsonMsg = gson.toJson(msg)
        var sent = ws.send(jsonMsg)
        if (!sent) {
            delay(200)
            ws = webSocket
            if (ws != null) {
                sent = ws.send(jsonMsg)
            }
        }
        if (!sent) {
            throw IllegalStateException("Network send buffer busy. Please tap Send again.")
        }
        Log.d(TAG, "Sent text payload: ${text.take(20)}... (${text.length} chars)")
    }

    /**
     * Send control command (PAUSE, RESUME, STOP, MODE_IDE, MODE_RAW) to Desktop.
     */
    suspend fun sendControl(command: String) {
        val sKey = sessionKey ?: throw IllegalStateException("Not paired with Desktop. Please pair first.")
        if (sKey.size != 32) {
            throw IllegalStateException("Invalid encryption key. Please re-pair with desktop.")
        }
        val ws = webSocket ?: throw IllegalStateException("Connection lost. Reconnecting to Desktop...")

        val payloadJson = gson.toJson(mapOf("command" to command))
        val encrypted = cryptoEngine.encrypt(sKey, payloadJson)

        val msg = ProtocolMessage(
            id        = UUID.randomUUID().toString(),
            type      = MessageType.CONTROL,
            payload   = encrypted.first,
            iv        = encrypted.second,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis()
        )
        val sent = ws.send(gson.toJson(msg))
        if (!sent) {
            throw IllegalStateException("Failed to send control command.")
        }
        Log.d(TAG, "Sent control command: $command")
    }

    private fun sendHeartbeatPing(): Boolean {
        val ws = webSocket ?: return false
        return try {
            val payloadJson = gson.toJson(mapOf(
                "t_sent" to System.currentTimeMillis(),
                "is_echo" to false
            ))
            val msg = ProtocolMessage(
                id        = UUID.randomUUID().toString(),
                type      = MessageType.HEARTBEAT,
                payload   = payloadJson,
                iv        = null,
                sessionId = sessionId,
                timestamp = System.currentTimeMillis()
            )
            ws.send(gson.toJson(msg))
        } catch (e: Exception) {
            Log.w(TAG, "Heartbeat send error: ${e.message}")
            false
        }
    }

    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatJob = scope.launch {
            // Send initial ping immediately on connection to verify RTT instantly
            sendHeartbeatPing()
            while (_connectionState.value is ConnectionState.Connected) {
                delay(1200L) // Real-time 1.2s ping cadence
                if (_connectionState.value !is ConnectionState.Connected) break
                val sent = sendHeartbeatPing()
                if (!sent) {
                    Log.w(TAG, "Heartbeat ping failed to send")
                    break
                }
            }
        }
    }

    private fun stopHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = null
    }

    private fun scheduleReconnect() {
        if (isManualDisconnect) return

        reconnectJob?.cancel()
        
        // Keep foreground service and network wake locks alive during reconnections
        TypeBridgeService.startSafely(context)

        reconnectJob = scope.launch {
            // If activeIp or sessionKey is null, attempt recovery from device repository
            if (activeIp == null || sessionKey == null) {
                try {
                    val devices = deviceRepositoryProvider.get().getDevices().first()
                    val paired = devices.firstOrNull()
                    if (paired != null && paired.sessionKey.isNotEmpty()) {
                        activeIp = paired.ip
                        activePort = paired.port
                        sessionId = paired.sessionId
                        sessionKey = paired.sessionKey
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "Error recovering paired device: ${e.message}")
                }
            }

            val ip = activeIp ?: return@launch
            val sId = sessionId ?: return@launch
            val key = sessionKey ?: return@launch

            reconnectAttempt++
            _connectionState.value = ConnectionState.Reconnecting(reconnectAttempt, 0)
            
            // Ultra-responsive immediate retry on first attempt (50ms), then gentle ramp
            val backoffMs = when {
                reconnectAttempt <= 1 -> 50L
                reconnectAttempt <= 3 -> 300L
                reconnectAttempt <= 6 -> 800L
                reconnectAttempt <= 10 -> 1500L
                else -> 2000L
            }
            Log.d(TAG, "Scheduling self-healing reconnect #$reconnectAttempt in ${backoffMs}ms to $ip:$activePort...")
            delay(backoffMs)

            if (!isManualDisconnect && _connectionState.value !is ConnectionState.Connected) {
                connect(ip, activePort, sId, key)
            }
        }
    }

    fun disconnect() {
        isManualDisconnect = true
        stopHeartbeat()
        reconnectJob?.cancel()
        reconnectJob = null
        try {
            webSocket?.close(1000, "User disconnected")
        } catch (e: Exception) {
            Log.w(TAG, "Error closing websocket", e)
        }
        webSocket = null
        _connectionState.value = ConnectionState.Disconnected
        TypeBridgeService.stopSafely(context)
    }
}
