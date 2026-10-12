package com.typebridge.mobile.domain.usecase

import com.typebridge.mobile.network.WebSocketClient
import javax.inject.Inject

class SendControlUseCase @Inject constructor(
    private val webSocketClient: WebSocketClient
) {
    suspend operator fun invoke(command: String): Result<Unit> {
        return try {
            webSocketClient.sendControl(command)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
