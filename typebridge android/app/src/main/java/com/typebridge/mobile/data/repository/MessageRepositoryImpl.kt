package com.typebridge.mobile.data.repository

import com.typebridge.mobile.data.local.dao.MessageDao
import com.typebridge.mobile.data.local.entity.toEntity
import com.typebridge.mobile.domain.model.Message
import com.typebridge.mobile.domain.repository.MessageRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class MessageRepositoryImpl @Inject constructor(
    private val messageDao: MessageDao
) : MessageRepository {
    override fun getMessages(): Flow<List<Message>> {
        return messageDao.getMessages().map { list -> list.map { it.toDomain() } }
    }

    override suspend fun addMessage(message: Message) {
        messageDao.insertMessage(message.toEntity())
    }

    override suspend fun clearMessages() {
        messageDao.clearMessages()
    }
}
