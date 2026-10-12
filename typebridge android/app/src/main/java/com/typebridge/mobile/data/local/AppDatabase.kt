package com.typebridge.mobile.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.typebridge.mobile.data.local.dao.DeviceDao
import com.typebridge.mobile.data.local.dao.MessageDao
import com.typebridge.mobile.data.local.entity.DeviceEntity
import com.typebridge.mobile.data.local.entity.MessageEntity

@Database(entities = [DeviceEntity::class, MessageEntity::class], version = 2, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun deviceDao(): DeviceDao
    abstract fun messageDao(): MessageDao
}
