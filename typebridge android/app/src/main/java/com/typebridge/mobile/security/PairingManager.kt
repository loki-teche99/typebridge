package com.typebridge.mobile.security

import android.net.Uri
import android.util.Log
import com.google.gson.Gson
import com.typebridge.mobile.domain.model.Device
import com.typebridge.mobile.network.MessageProtocol
import com.typebridge.mobile.network.MessageType
import com.typebridge.mobile.network.ProtocolMessage
import com.typebridge.mobile.network.WebSocketClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.bouncycastle.crypto.params.X25519PublicKeyParameters
import java.util.UUID
import javax.inject.Inject
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

private const val TAG = "PairingManager"
private const val PAIR_TIMEOUT_MS = 15000L

/**
 * Handles pairing handshake over WSS:
 * Supports both QR-code scan & manual IP/PIN entry:
 * 1. Generates own X25519 key pair
 * 2. Opens WSS connection to desktop
 * 3. Sends PAIR_REQUEST with public key + PIN
 * 4. Receives PAIR_RESPONSE with desktop public key → derives AES session key
 * 5. Hands off to [WebSocketClient] to keep connection alive
 */
class PairingManager @Inject constructor(
    private val client: OkHttpClient,
    private val cryptoEngine: CryptoEngine,
    private val webSocketClient: WebSocketClient,
    private val gson: Gson
) {
    suspend fun pairFromQr(qrData: String): Device {
        val trimmed = qrData.trim()
        val uri = try {
            Uri.parse(trimmed)
        } catch (e: Exception) {
            throw IllegalArgumentException("Invalid QR code format. Please scan a TypeBridge QR code.")
        }

        val ip = uri.getQueryParameter("ip")
            ?: throw IllegalArgumentException("QR code missing IP address. Ensure desktop app is open.")
        val port = uri.getQueryParameter("port")?.toIntOrNull() ?: 8765
        val pin = uri.getQueryParameter("pin")
            ?: throw IllegalArgumentException("QR code missing PIN.")

        return pair(ip, port, pin)
    }

    suspend fun pair(ip: String, port: Int, pin: String): Device = withContext(Dispatchers.IO) {
        val cleanIp = ip.trim()
        val cleanPin = pin.trim()

        if (cleanIp.isEmpty()) {
            throw IllegalArgumentException("IP address cannot be empty.")
        }
        if (cleanPin.length != 6 || !cleanPin.all { it.isDigit() }) {
            throw IllegalArgumentException("PIN must be a 6-digit number.")
        }

        withTimeout(PAIR_TIMEOUT_MS) {
            val myKeyPair = cryptoEngine.generateKeyPair()
            val myPubB64 = cryptoEngine.serializePublicKey(myKeyPair.publicKey)
            val deviceName = "Android Device"

            val pairPayload = gson.toJson(mapOf(
                "device_name" to deviceName,
                "public_key" to myPubB64,
                "pin" to cleanPin
            ))
            val pairMsg = MessageProtocol.build(
                type = MessageType.PAIR_REQUEST,
                payload = pairPayload,
                iv = "",
                sessionId = ""
            )

            suspendCancellableCoroutine<Device> { cont ->
                val request = Request.Builder()
                    .url("wss://$cleanIp:$port")
                    .build()

                val ws = client.newWebSocket(request, object : WebSocketListener() {
                    override fun onOpen(webSocket: WebSocket, response: Response) {
                        Log.d(TAG, "Connected to desktop WSS ($cleanIp:$port), sending PAIR_REQUEST...")
                        webSocket.send(pairMsg)
                    }

                    override fun onMessage(webSocket: WebSocket, text: String) {
                        try {
                            val msg = gson.fromJson(text, ProtocolMessage::class.java)
                            if (msg.type == MessageType.PAIR_RESPONSE) {
                                val respData = gson.fromJson(msg.payload, Map::class.java) as? Map<*, *>
                                val status = respData?.get("status") as? String
                                if (status == "accepted") {
                                    val desktopPubB64 = respData["public_key"] as? String
                                        ?: error("No public_key in PAIR_RESPONSE")
                                    val sessionId = respData["session_id"] as? String
                                        ?: UUID.randomUUID().toString()

                                    val desktopPubKey: X25519PublicKeyParameters =
                                        cryptoEngine.deserializePublicKey(desktopPubB64)
                                    val sessionKey = cryptoEngine.deriveSessionKey(
                                        myKeyPair.privateKey, desktopPubKey
                                    )

                                    Log.d(TAG, "Pairing accepted! Establishing persistent session.")

                                    try {
                                        webSocket.close(1000, "Pairing complete")
                                    } catch (e: Exception) {
                                        Log.w(TAG, "Error closing initial pairing socket", e)
                                    }

                                    webSocketClient.connect(
                                        cleanIp, port, sessionId, sessionKey
                                    )

                                    val device = Device(
                                        id = UUID.randomUUID().toString(),
                                        name = "Desktop ($cleanIp)",
                                        publicKey = desktopPubB64,
                                        ip = cleanIp,
                                        port = port,
                                        isConnected = true,
                                        sessionId = sessionId,
                                        sessionKey = sessionKey
                                    )
                                    if (cont.isActive) {
                                        cont.resume(device)
                                    }
                                } else {
                                    try {
                                        webSocket.close(1000, "Rejected")
                                    } catch (e: Exception) {
                                        // ignore
                                    }
                                    if (cont.isActive) {
                                        cont.resumeWithException(
                                            Exception("Pairing rejected: Incorrect PIN. Please verify the PIN on your PC.")
                                        )
                                    }
                                }
                            }
                        } catch (e: Exception) {
                            Log.e(TAG, "Error parsing pairing response: ${e.message}", e)
                            try {
                                webSocket.close(1000, "Error")
                            } catch (ex: Exception) {
                                // ignore
                            }
                            if (cont.isActive) {
                                cont.resumeWithException(e)
                            }
                        }
                    }

                    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                        Log.e(TAG, "WebSocket failure during pairing with $cleanIp:$port: ${t.message}", t)
                        if (cont.isActive) {
                            cont.resumeWithException(
                                Exception("Cannot reach Desktop at $cleanIp:$port. Check that both devices are on the same Wi-Fi network and firewall allows port $port.")
                            )
                        }
                    }
                })

                cont.invokeOnCancellation {
                    try {
                        ws.cancel()
                    } catch (e: Exception) {
                        // ignore
                    }
                }
            }
        }
    }
}
