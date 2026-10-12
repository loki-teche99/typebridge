package com.typebridge.mobile.domain.usecase

import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.network.WebSocketClient
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

class GetConnectionStateUseCase @Inject constructor(
    private val webSocketClient: WebSocketClient
) {
    operator fun invoke(): StateFlow<ConnectionState> {
        return webSocketClient.connectionState
    }
}
