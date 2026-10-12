package com.typebridge.mobile.di

import com.google.gson.Gson
import com.typebridge.mobile.network.WebSocketClient
import com.typebridge.mobile.security.CryptoEngine
import com.typebridge.mobile.security.PairingManager
import com.typebridge.mobile.security.TrustManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object SecurityModule {
    @Provides
    @Singleton
    fun provideCryptoEngine(): CryptoEngine = CryptoEngine()

    @Provides
    @Singleton
    fun provideTrustManager(): TrustManager = TrustManager()

    @Provides
    @Singleton
    fun providePairingManager(
        client: OkHttpClient,
        cryptoEngine: CryptoEngine,
        webSocketClient: WebSocketClient,
        gson: Gson
    ): PairingManager = PairingManager(client, cryptoEngine, webSocketClient, gson)
}
