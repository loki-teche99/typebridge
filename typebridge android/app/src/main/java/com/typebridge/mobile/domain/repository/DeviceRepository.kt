package com.typebridge.mobile.domain.repository

import com.typebridge.mobile.domain.model.Device
import kotlinx.coroutines.flow.Flow

interface DeviceRepository {
    fun getDevices(): Flow<List<Device>>
    suspend fun getDevice(id: String): Device?
    suspend fun addDevice(device: Device)
    suspend fun updateDevice(device: Device)
    suspend fun deleteDevice(id: String)
}
