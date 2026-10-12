package com.typebridge.mobile.di

import android.content.Context
import androidx.room.Room
import com.typebridge.mobile.data.local.AppDatabase
import com.typebridge.mobile.data.local.dao.DeviceDao
import com.typebridge.mobile.data.local.dao.MessageDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "typebridge.db"
        )
        .fallbackToDestructiveMigration()
        .build()
    }

    @Provides
    fun provideDeviceDao(db: AppDatabase): DeviceDao = db.deviceDao()

    @Provides
    fun provideMessageDao(db: AppDatabase): MessageDao = db.messageDao()
}
