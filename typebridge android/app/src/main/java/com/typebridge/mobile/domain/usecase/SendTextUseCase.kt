package com.typebridge.mobile.domain.usecase

import com.typebridge.mobile.network.WebSocketClient
import javax.inject.Inject

class SendTextUseCase @Inject constructor(
    private val webSocketClient: WebSocketClient
) {
    suspend operator fun invoke(text: String): Result<Unit> {
        return try {
            webSocketClient.sendText(text)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
