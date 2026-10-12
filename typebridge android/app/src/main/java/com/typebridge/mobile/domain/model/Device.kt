package com.typebridge.mobile.domain.model

/**
 * Represents a paired TypeBridge Desktop device.
 * [sessionKey] and [sessionId] are populated after successful ECDH pairing
 * and are kept in memory only (never written to plain storage).
 */
data class Device(
    val id: String,
    val name: String,
    val publicKey: String,
    val ip: String,
    val port: Int,
    val isConnected: Boolean = false,
    val sessionId: String = "",
    @Transient val sessionKey: ByteArray = ByteArray(0)
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Device) return false
        return id == other.id
    }
    override fun hashCode(): Int = id.hashCode()
}
