package com.typebridge.mobile.di

import com.typebridge.mobile.data.repository.DeviceRepositoryImpl
import com.typebridge.mobile.data.repository.MessageRepositoryImpl
import com.typebridge.mobile.domain.repository.DeviceRepository
import com.typebridge.mobile.domain.repository.MessageRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
abstract class AppModule {
    @Binds
    abstract fun bindDeviceRepository(
        deviceRepositoryImpl: DeviceRepositoryImpl
    ): DeviceRepository

    @Binds
    abstract fun bindMessageRepository(
        messageRepositoryImpl: MessageRepositoryImpl
    ): MessageRepository
}
