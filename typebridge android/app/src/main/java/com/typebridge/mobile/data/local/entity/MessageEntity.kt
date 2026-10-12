package com.typebridge.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.typebridge.mobile.domain.model.Message

@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey val id: String,
    val type: String,
    val payload: String,
    val timestamp: Long,
    val isSent: Boolean
) {
    fun toDomain() = Message(id, type, payload, timestamp, isSent)
}

fun Message.toEntity() = MessageEntity(id, type, payload, timestamp, isSent)
