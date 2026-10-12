package com.typebridge.mobile.data.repository

import com.typebridge.mobile.data.local.dao.DeviceDao
import com.typebridge.mobile.data.local.entity.toEntity
import com.typebridge.mobile.domain.model.Device
import com.typebridge.mobile.domain.repository.DeviceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class DeviceRepositoryImpl @Inject constructor(
    private val deviceDao: DeviceDao
) : DeviceRepository {
    override fun getDevices(): Flow<List<Device>> {
        return deviceDao.getDevices().map { list -> list.map { it.toDomain() } }
    }

    override suspend fun getDevice(id: String): Device? {
        return deviceDao.getDevice(id)?.toDomain()
    }

    override suspend fun addDevice(device: Device) {
        deviceDao.insertDevice(device.toEntity())
    }

    override suspend fun updateDevice(device: Device) {
        deviceDao.updateDevice(device.toEntity())
    }

    override suspend fun deleteDevice(id: String) {
        deviceDao.deleteDevice(id)
    }
}
