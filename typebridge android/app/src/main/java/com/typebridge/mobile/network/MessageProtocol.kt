package com.typebridge.mobile.network

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.util.UUID

// ---------------------------------------------------------------------------
//  Wire message (matches TypeBridge Desktop protocol exactly)
// ---------------------------------------------------------------------------

data class ProtocolMessage(
    @SerializedName("id")         val id: String,
    @SerializedName("type")       val type: String,
    @SerializedName("payload")    val payload: String,
    @SerializedName("iv")         val iv: String? = null,
    @SerializedName("session_id") val sessionId: String? = null,
    @SerializedName("timestamp")  val timestamp: Long = System.currentTimeMillis()
)

// ---------------------------------------------------------------------------
//  Payload data classes
// ---------------------------------------------------------------------------

data class TextPayloadData(
    @SerializedName("text")   val text: String,
    @SerializedName("msg_id") val msgId: String
)

data class AckPayload(
    @SerializedName("ack_id") val ackId: String
)

data class PairRequestPayload(
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("public_key")  val publicKey: String,
    @SerializedName("pin")         val pin: String
)

data class PairResponsePayload(
    @SerializedName("status")     val status: String,
    @SerializedName("public_key") val publicKey: String?,
    @SerializedName("session_id") val sessionId: String?
)

// ---------------------------------------------------------------------------
//  Message builder (mirrors Python MessageBuilder.build())
// ---------------------------------------------------------------------------

object MessageProtocol {
    private val gson = Gson()

    /**
     * Serialize a TypeBridge message to a JSON string ready to send over WebSocket.
     * Matches the Python desktop's MessageBuilder.build() output exactly.
     */
    fun build(
        type: String,
        payload: String,
        iv: String,
        sessionId: String
    ): String {
        val msg = ProtocolMessage(
            id        = UUID.randomUUID().toString(),
            type      = type,
            payload   = payload,
            iv        = iv,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis()
        )
        return gson.toJson(msg)
    }

    fun parse(json: String): ProtocolMessage = gson.fromJson(json, ProtocolMessage::class.java)
}

// Message type constants
object MessageType {
    const val TEXT_PAYLOAD  = "TEXT_PAYLOAD"
    const val ACK           = "ACK"
    const val HEARTBEAT     = "HEARTBEAT"
    const val PAIR_REQUEST  = "PAIR_REQUEST"
    const val PAIR_RESPONSE = "PAIR_RESPONSE"
    const val REVOKE        = "REVOKE"
    const val CONTROL       = "CONTROL"
}
