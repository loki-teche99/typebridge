package com.typebridge.mobile.network

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.security.CryptoEngine
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
import kotlinx.coroutines.withContext
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.IOException
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "BluetoothClient"

// Standard SPP (Serial Port Profile) UUID
private val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

@Singleton
class BluetoothClient @Inject constructor(
    @ApplicationContext private val context: Context,
    private val cryptoEngine: CryptoEngine,
    private val gson: Gson
) {
    private var socket: BluetoothSocket? = null
    private var inputStream: DataInputStream? = null
    private var outputStream: DataOutputStream? = null

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var readJob: Job? = null
    private var heartbeatJob: Job? = null
    private var reconnectJob: Job? = null
    private var reconnectAttempt = 0
    private var isManualDisconnect = false

    private var sessionId: String? = null
    private var sessionKey: ByteArray? = null
    private var targetDevice: BluetoothDevice? = null

    /**
     * Get list of paired Bluetooth devices that might be TypeBridge Desktop.
     */
    @SuppressLint("MissingPermission")
    fun getPairedDevices(): List<BluetoothDevice> {
        val btManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = btManager?.adapter ?: return emptyList()
        if (!adapter.isEnabled) return emptyList()
        return try {
            adapter.bondedDevices?.filter { device ->
                val name = device.name?.lowercase() ?: ""
                // Match devices likely to be a PC running TypeBridge
                name.contains("typebridge") ||
                name.contains("desktop") ||
                name.contains("laptop") ||
                name.contains("pc") ||
                device.bluetoothClass?.majorDeviceClass == android.bluetooth.BluetoothClass.Device.Major.COMPUTER
            }?.toList() ?: emptyList()
        } catch (e: SecurityException) {
            Log.w(TAG, "Bluetooth permission denied: ${e.message}")
            emptyList()
        }
    }

    /**
     * Connect to a specific Bluetooth device via RFCOMM SPP.
     */
    @SuppressLint("MissingPermission")
    fun connect(device: BluetoothDevice, sId: String, key: ByteArray) {
        if (key.size != 32) {
            _connectionState.value = ConnectionState.Error("Invalid encryption key")
            return
        }

        isManualDisconnect = false
        targetDevice = device
        sessionId = sId
        sessionKey = key
        _connectionState.value = ConnectionState.Connecting

        scope.launch {
            try {
                // Cancel discovery to speed up connection
                val btManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
                try {
                    btManager?.adapter?.cancelDiscovery()
                } catch (_: SecurityException) {}

                // Create RFCOMM socket and connect
                val btSocket = device.createRfcommSocketToServiceRecord(SPP_UUID)
                socket = btSocket

                withContext(Dispatchers.IO) {
                    btSocket.connect()
                }

                inputStream = DataInputStream(btSocket.inputStream)
                outputStream = DataOutputStream(btSocket.outputStream)

                Log.d(TAG, "Bluetooth connected to ${device.name}")
                reconnectAttempt = 0
                _connectionState.value = ConnectionState.Connected(device.name ?: "Desktop", 5L)

                // Start heartbeat
                startHeartbeat()

                // Start read loop
                startReadLoop()

            } catch (e: IOException) {
                Log.e(TAG, "Bluetooth connection failed: ${e.message}")
                cleanup()
                if (!isManualDisconnect) {
                    _connectionState.value = ConnectionState.Error("Bluetooth connection failed: ${e.message}")
                    scheduleReconnect()
                } else {
                    _connectionState.value = ConnectionState.Disconnected
                }
            } catch (e: SecurityException) {
                Log.e(TAG, "Bluetooth permission error: ${e.message}")
                cleanup()
                _connectionState.value = ConnectionState.Error("Bluetooth permission denied")
            }
        }
    }

    private fun startReadLoop() {
        readJob?.cancel()
        readJob = scope.launch {
            try {
                while (_connectionState.value is ConnectionState.Connected) {
                    val frame = readFrame() ?: break
                    handleMessage(frame)
                }
            } catch (e: IOException) {
                if (!isManualDisconnect) {
                    Log.e(TAG, "BT read error: ${e.message}")
                    _connectionState.value = ConnectionState.Error("Bluetooth disconnected")
                }
            } finally {
                cleanup()
                if (!isManualDisconnect) {
                    scheduleReconnect()
                }
            }
        }
    }

    /**
     * Read a length-prefixed frame (4-byte big-endian length + JSON).
     */
    private fun readFrame(): String? {
        val dis = inputStream ?: return null
        return try {
            val length = dis.readInt()
            if (length <= 0 || length > 10 * 1024 * 1024) return null
            val data = ByteArray(length)
            dis.readFully(data)
            String(data, Charsets.UTF_8)
        } catch (e: Exception) {
            if (!isManualDisconnect) throw e
            null
        }
    }

    /**
     * Send a length-prefixed frame.
     */
    @Synchronized
    private fun sendFrame(data: String): Boolean {
        val dos = outputStream ?: return false
        return try {
            val bytes = data.toByteArray(Charsets.UTF_8)
            dos.writeInt(bytes.size)
            dos.write(bytes)
            dos.flush()
            true
        } catch (e: IOException) {
            Log.e(TAG, "BT send error: ${e.message}")
            false
        }
    }

    private fun handleMessage(text: String) {
        try {
            val msg = gson.fromJson(text, ProtocolMessage::class.java) ?: return
            val sKey = sessionKey

            if (msg.type == MessageType.ACK && !msg.payload.isNullOrEmpty() && sKey != null && sKey.size == 32) {
                try {
                    val iv = msg.iv ?: return
                    val decrypted = cryptoEngine.decrypt(sKey, msg.payload, iv)
                    Log.d(TAG, "BT ACK received: $decrypted")
                } catch (e: Exception) {
                    Log.w(TAG, "BT ACK decrypt error: ${e.message}")
                }
            } else if (msg.type == MessageType.HEARTBEAT) {
                try {
                    val payload = gson.fromJson(msg.payload, Map::class.java) as? Map<*, *>
                    val tSent = (payload?.get("t_sent") as? Number)?.toLong() ?: 0L
                    if (tSent > 0) {
                        val latency = (System.currentTimeMillis() - tSent).coerceAtLeast(1L).coerceAtMost(999L)
                        _connectionState.value = ConnectionState.Connected(targetDevice?.name ?: "Desktop", latency)
                    }
                } catch (_: Exception) {}

                // Echo heartbeat back
                val echoMsg = ProtocolMessage(
                    id = UUID.randomUUID().toString(),
                    type = MessageType.HEARTBEAT,
                    payload = msg.payload,
                    iv = null,
                    sessionId = sessionId,
                    timestamp = System.currentTimeMillis()
                )
                sendFrame(gson.toJson(echoMsg))
            }
        } catch (e: Exception) {
            Log.e(TAG, "BT message parse error", e)
        }
    }

    /**
     * Send text payload over Bluetooth.
     */
    suspend fun sendText(text: String) {
        val sKey = sessionKey ?: throw IllegalStateException("Not paired. Please pair first.")
        if (sKey.size != 32) throw IllegalStateException("Invalid key. Please re-pair.")

        val payloadData = TextPayloadData(text, UUID.randomUUID().toString())
        val payloadJson = gson.toJson(payloadData)
        val encrypted = cryptoEngine.encrypt(sKey, payloadJson)

        val msg = ProtocolMessage(
            id = UUID.randomUUID().toString(),
            type = MessageType.TEXT_PAYLOAD,
            payload = encrypted.first,
            iv = encrypted.second,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis()
        )

        val sent = sendFrame(gson.toJson(msg))
        if (!sent) throw IllegalStateException("Bluetooth send failed")
        Log.d(TAG, "BT sent text: ${text.take(20)}...")
    }

    /**
     * Send control command over Bluetooth.
     */
    suspend fun sendControl(command: String) {
        val sKey = sessionKey ?: throw IllegalStateException("Not paired.")
        if (sKey.size != 32) throw IllegalStateException("Invalid key.")

        val payloadJson = gson.toJson(mapOf("command" to command))
        val encrypted = cryptoEngine.encrypt(sKey, payloadJson)

        val msg = ProtocolMessage(
            id = UUID.randomUUID().toString(),
            type = MessageType.CONTROL,
            payload = encrypted.first,
            iv = encrypted.second,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis()
        )

        val sent = sendFrame(gson.toJson(msg))
        if (!sent) throw IllegalStateException("Bluetooth send failed")
        Log.d(TAG, "BT sent control: $command")
    }

    private fun sendHeartbeatPing(): Boolean {
        return try {
            val payloadJson = gson.toJson(mapOf("t_sent" to System.currentTimeMillis()))
            val msg = ProtocolMessage(
                id = UUID.randomUUID().toString(),
                type = MessageType.HEARTBEAT,
                payload = payloadJson,
                iv = null,
                sessionId = sessionId,
                timestamp = System.currentTimeMillis()
            )
            sendFrame(gson.toJson(msg))
        } catch (e: Exception) {
            Log.e(TAG, "BT heartbeat error", e)
            false
        }
    }

    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = scope.launch {
            // Send initial ping immediately
            sendHeartbeatPing()
            while (_connectionState.value is ConnectionState.Connected) {
                delay(3000)
                if (_connectionState.value !is ConnectionState.Connected) break
                val sent = sendHeartbeatPing()
                if (!sent) break
            }
        }
    }

    private fun scheduleReconnect() {
        if (isManualDisconnect) return
        val dev = targetDevice ?: return
        val sId = sessionId ?: return
        val key = sessionKey ?: return

        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            reconnectAttempt++
            _connectionState.value = ConnectionState.Reconnecting(reconnectAttempt, 0)
            val backoffMs = when {
                reconnectAttempt <= 1 -> 500L
                reconnectAttempt <= 3 -> 1500L
                else -> 3000L
            }
            Log.d(TAG, "Scheduling Bluetooth auto-reconnect #$reconnectAttempt in ${backoffMs}ms...")
            delay(backoffMs)

            if (!isManualDisconnect && _connectionState.value !is ConnectionState.Connected) {
                connect(dev, sId, key)
            }
        }
    }

    fun disconnect() {
        isManualDisconnect = true
        heartbeatJob?.cancel()
        readJob?.cancel()
        reconnectJob?.cancel()
        reconnectJob = null
        cleanup()
        _connectionState.value = ConnectionState.Disconnected
    }

    private fun cleanup() {
        try { inputStream?.close() } catch (_: Exception) {}
        try { outputStream?.close() } catch (_: Exception) {}
        try { socket?.close() } catch (_: Exception) {}
        inputStream = null
        outputStream = null
        socket = null
    }

    val isConnected: Boolean
        get() = _connectionState.value is ConnectionState.Connected && socket?.isConnected == true
}
