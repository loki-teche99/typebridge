package com.typebridge.mobile.domain.model

sealed class ConnectionState {
    object Disconnected : ConnectionState()
    object Connecting : ConnectionState()
    data class Connected(val deviceName: String, val latencyMs: Long) : ConnectionState()
    data class Reconnecting(val attempt: Int, val maxAttempts: Int) : ConnectionState()
    data class Unstable(val ip: String, val latency: Long) : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}
