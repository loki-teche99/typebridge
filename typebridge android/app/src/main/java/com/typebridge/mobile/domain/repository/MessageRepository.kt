package com.typebridge.mobile.domain.repository

import com.typebridge.mobile.domain.model.Message
import kotlinx.coroutines.flow.Flow

interface MessageRepository {
    fun getMessages(): Flow<List<Message>>
    suspend fun addMessage(message: Message)
    suspend fun clearMessages()
}
