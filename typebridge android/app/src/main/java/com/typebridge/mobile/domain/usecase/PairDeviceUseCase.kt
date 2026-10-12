package com.typebridge.mobile.domain.usecase

import com.typebridge.mobile.domain.model.Device
import com.typebridge.mobile.domain.repository.DeviceRepository
import com.typebridge.mobile.security.PairingManager
import javax.inject.Inject

class PairDeviceUseCase @Inject constructor(
    private val deviceRepository: DeviceRepository,
    private val pairingManager: PairingManager
) {
    suspend operator fun invoke(qrData: String): Result<Device> {
        return try {
            val device = pairingManager.pairFromQr(qrData)
            deviceRepository.addDevice(device)
            Result.success(device)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun pairManual(ip: String, port: Int, pin: String): Result<Device> {
        return try {
            val device = pairingManager.pair(ip, port, pin)
            deviceRepository.addDevice(device)
            Result.success(device)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
