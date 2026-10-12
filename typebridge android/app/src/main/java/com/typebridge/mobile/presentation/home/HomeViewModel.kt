package com.typebridge.mobile.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.typebridge.mobile.domain.model.ConnectionState
import com.typebridge.mobile.domain.repository.DeviceRepository
import com.typebridge.mobile.domain.usecase.GetConnectionStateUseCase
import com.typebridge.mobile.domain.usecase.SendControlUseCase
import com.typebridge.mobile.domain.usecase.SendTextUseCase
import com.typebridge.mobile.network.WebSocketClient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    getConnectionStateUseCase: GetConnectionStateUseCase,
    private val sendTextUseCase: SendTextUseCase,
    private val sendControlUseCase: SendControlUseCase,
    private val deviceRepository: DeviceRepository,
    private val webSocketClient: WebSocketClient
) : ViewModel() {
    val connectionState = getConnectionStateUseCase()

    private val _sendResult = MutableStateFlow<Result<Unit>?>(null)
    val sendResult: StateFlow<Result<Unit>?> = _sendResult.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _controlResult = MutableStateFlow<Result<Unit>?>(null)
    val controlResult: StateFlow<Result<Unit>?> = _controlResult.asStateFlow()

    init {
        // Automatically connect to the last paired device on app launch
        reconnectIfDisconnected()
    }

    fun reconnectIfDisconnected() {
        viewModelScope.launch {
            val currentState = webSocketClient.connectionState.value
            if (currentState is ConnectionState.Disconnected || currentState is ConnectionState.Error) {
                val devices = deviceRepository.getDevices().first()
                val pairedDevice = devices.firstOrNull()
                if (pairedDevice != null && pairedDevice.sessionKey.isNotEmpty()) {
                    webSocketClient.connect(
                        pairedDevice.ip,
                        pairedDevice.port,
                        pairedDevice.sessionId,
                        pairedDevice.sessionKey
                    )
                }
            }
        }
    }

    fun sendText(text: String) {
        if (_isSending.value) return
        _isSending.value = true
        viewModelScope.launch {
            try {
                _sendResult.value = sendTextUseCase(text)
            } catch (e: Exception) {
                _sendResult.value = Result.failure(e)
            } finally {
                _isSending.value = false
            }
        }
    }

    fun sendControl(command: String) {
        viewModelScope.launch {
            try {
                _controlResult.value = sendControlUseCase(command)
            } catch (e: Exception) {
                _controlResult.value = Result.failure(e)
            }
        }
    }

    fun clearResult() {
        _sendResult.value = null
        _controlResult.value = null
    }
}
