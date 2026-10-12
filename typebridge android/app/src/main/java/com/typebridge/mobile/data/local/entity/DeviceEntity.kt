package com.typebridge.mobile.data.local.entity

import android.util.Base64
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.typebridge.mobile.domain.model.Device

@Entity(tableName = "devices")
data class DeviceEntity(
    @PrimaryKey val id: String,
    val name: String,
    val publicKey: String,
    val ip: String,
    val port: Int,
    val sessionId: String = "",
    val sessionKeyB64: String = ""
) {
    fun toDomain(): Device {
        val key = if (sessionKeyB64.isNotEmpty()) {
            try {
                Base64.decode(sessionKeyB64, Base64.DEFAULT)
            } catch (e: Exception) {
                ByteArray(0)
            }
        } else {
            ByteArray(0)
        }
        return Device(
            id = id,
            name = name,
            publicKey = publicKey,
            ip = ip,
            port = port,
            isConnected = false,
            sessionId = sessionId,
            sessionKey = key
        )
    }
}

fun Device.toEntity(): DeviceEntity {
    val keyB64 = if (sessionKey.isNotEmpty()) {
        Base64.encodeToString(sessionKey, Base64.NO_WRAP)
    } else {
        ""
    }
    return DeviceEntity(
        id = id,
        name = name,
        publicKey = publicKey,
        ip = ip,
        port = port,
        sessionId = sessionId,
        sessionKeyB64 = keyB64
    )
}
