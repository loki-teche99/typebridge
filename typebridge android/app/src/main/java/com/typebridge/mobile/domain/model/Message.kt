package com.typebridge.mobile.domain.model

data class Message(
    val id: String,
    val type: String,
    val payload: String,
    val timestamp: Long,
    val isSent: Boolean
)
