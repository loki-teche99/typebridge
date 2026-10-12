package com.typebridge.mobile.presentation.pair

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.typebridge.mobile.domain.usecase.PairDeviceUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PairViewModel @Inject constructor(
    private val pairDeviceUseCase: PairDeviceUseCase
) : ViewModel() {

    private val _pairResult = MutableStateFlow<Result<Unit>?>(null)
    val pairResult: StateFlow<Result<Unit>?> = _pairResult.asStateFlow()

    private val _isPairing = MutableStateFlow(false)
    val isPairing: StateFlow<Boolean> = _isPairing.asStateFlow()

    fun pairFromQr(qrData: String) {
        if (_isPairing.value) return
        _isPairing.value = true
        viewModelScope.launch {
            try {
                val result = pairDeviceUseCase(qrData)
                if (result.isSuccess) {
                    _pairResult.value = Result.success(Unit)
                } else {
                    _pairResult.value = Result.failure(result.exceptionOrNull() ?: Exception("Pairing failed"))
                }
            } catch (e: Exception) {
                _pairResult.value = Result.failure(e)
            } finally {
                _isPairing.value = false
            }
        }
    }

    fun pairManual(ip: String, port: Int, pin: String) {
        if (_isPairing.value) return
        _isPairing.value = true
        viewModelScope.launch {
            try {
                val result = pairDeviceUseCase.pairManual(ip, port, pin)
                if (result.isSuccess) {
                    _pairResult.value = Result.success(Unit)
                } else {
                    _pairResult.value = Result.failure(result.exceptionOrNull() ?: Exception("Pairing failed"))
                }
            } catch (e: Exception) {
                _pairResult.value = Result.failure(e)
            } finally {
                _isPairing.value = false
            }
        }
    }

    fun clearResult() {
        _pairResult.value = null
    }
}
